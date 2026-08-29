"""Content-based highlight extraction via ffmpeg audio-activity analysis.

Approach: identify the "active" (non-silent) stretches of the source's
audio track using ffmpeg's `silencedetect` filter, treat the longest
continuous active stretches as the substantive content (talking, action,
music) worth keeping, and greedily select the longest ones -- reassembled
in original chronological order -- until they sum to roughly
`TARGET_DURATION_SECONDS`.

This is a signal-processing heuristic (sustained audio activity as a proxy
for "something is happening"), not semantic or visual scene understanding
-- there is no vision/LLM model wired into this service. It's a
well-established, practically buildable building block for automatic
highlight/trailer generation using ffmpeg alone.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.exceptions import ValidationError

logger = logging.getLogger(__name__)

TARGET_DURATION_SECONDS = 60.0
SILENCE_NOISE_THRESHOLD_DB = "-30dB"
SILENCE_MIN_DURATION_SECONDS = 0.75
MIN_ACTIVE_SEGMENT_SECONDS = 1.5
FFPROBE_TIMEOUT_SECONDS = 30
FFMPEG_ANALYZE_TIMEOUT_SECONDS = 10 * 60
FFMPEG_RENDER_TIMEOUT_SECONDS = 15 * 60

_SILENCE_START_RE = re.compile(r"silence_start:\s*([0-9.]+)")
_SILENCE_END_RE = re.compile(r"silence_end:\s*([0-9.]+)")


@dataclass(frozen=True)
class Segment:
    """A [start, end) time range in seconds within the source video."""

    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


def probe_duration_seconds(input_path: Path) -> float:
    """Return the media duration in seconds via `ffprobe`."""
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(input_path),
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=FFPROBE_TIMEOUT_SECONDS, check=False
        )
    except FileNotFoundError as exc:
        logger.error("ffprobe binary not found on PATH")
        raise ValidationError("ffprobe is not available on this server") from exc
    except subprocess.TimeoutExpired as exc:
        raise ValidationError("Timed out probing source video duration") from exc

    if result.returncode != 0 or not result.stdout.strip():
        logger.error("ffprobe failed (exit=%s): %s", result.returncode, result.stderr[-2000:])
        raise ValidationError("Could not determine source video duration")

    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise ValidationError("Could not parse source video duration") from exc


def detect_active_segments(input_path: Path, total_duration: float) -> list[Segment]:
    """Return the non-silent ("active") stretches of `input_path`'s audio track.

    Runs ffmpeg's `silencedetect` filter once over the whole file and takes
    the complement of the reported silence intervals over [0, total_duration].
    Very short active slivers (below `MIN_ACTIVE_SEGMENT_SECONDS`) are
    dropped as noise rather than treated as meaningful content.
    """
    command = [
        "ffmpeg",
        "-i",
        str(input_path),
        "-af",
        f"silencedetect=noise={SILENCE_NOISE_THRESHOLD_DB}:d={SILENCE_MIN_DURATION_SECONDS}",
        "-f",
        "null",
        "-",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=FFMPEG_ANALYZE_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as exc:
        logger.error("ffmpeg binary not found on PATH")
        raise ValidationError("ffmpeg is not available on this server") from exc
    except subprocess.TimeoutExpired as exc:
        raise ValidationError("Audio activity analysis timed out") from exc

    # ffmpeg with -f null exits 0 even on a successful analysis pass with no
    # encoding output; a non-zero exit means it couldn't read/decode the input.
    if result.returncode != 0:
        logger.error("ffmpeg silencedetect failed (exit=%s): %s", result.returncode, result.stderr[-2000:])
        raise ValidationError(f"ffmpeg failed to analyze audio (exit code {result.returncode})")

    silence_intervals: list[Segment] = []
    pending_start: float | None = None
    for line in result.stderr.splitlines():
        start_match = _SILENCE_START_RE.search(line)
        if start_match:
            pending_start = float(start_match.group(1))
            continue
        end_match = _SILENCE_END_RE.search(line)
        if end_match and pending_start is not None:
            silence_intervals.append(Segment(pending_start, float(end_match.group(1))))
            pending_start = None
    if pending_start is not None:
        # Silence runs to the end of the file with no matching "silence_end"
        # line ever printed (ffmpeg only logs silence_end when audio
        # actually resumes, not at end-of-stream).
        silence_intervals.append(Segment(pending_start, total_duration))

    active: list[Segment] = []
    cursor = 0.0
    for silence in sorted(silence_intervals, key=lambda seg: seg.start):
        if silence.start > cursor:
            active.append(Segment(cursor, silence.start))
        cursor = max(cursor, silence.end)
    if cursor < total_duration:
        active.append(Segment(cursor, total_duration))

    return [seg for seg in active if seg.duration >= MIN_ACTIVE_SEGMENT_SECONDS]


def select_highlight_segments(
    active_segments: list[Segment],
    total_duration: float,
    target_duration: float = TARGET_DURATION_SECONDS,
) -> list[Segment]:
    """Pick the longest active stretches, up to `target_duration` total,
    then return them in chronological order for a coherent playback order.

    Falls back to the first `target_duration` seconds of the whole source
    if no active segments were detected at all (e.g. a near-silent source
    that never crosses the noise threshold) -- always producing something
    playable rather than an empty result.
    """
    if not active_segments:
        return [Segment(0.0, min(target_duration, total_duration))]

    by_length_desc = sorted(active_segments, key=lambda seg: seg.duration, reverse=True)
    selected: list[Segment] = []
    remaining = target_duration
    for seg in by_length_desc:
        if remaining <= 0:
            break
        if seg.duration <= remaining:
            selected.append(seg)
            remaining -= seg.duration
        else:
            selected.append(Segment(seg.start, seg.start + remaining))
            remaining = 0.0

    return sorted(selected, key=lambda seg: seg.start)


def render_highlight_reel(input_path: Path, segments: list[Segment], output_path: Path) -> None:
    """Cut and concatenate `segments` from `input_path` into one continuous `output_path`.

    Builds an ffmpeg `filter_complex` graph that trims each segment's video
    and audio independently, resets their timestamps, and concatenates
    them in order. Re-encodes (concat via filter graph can't stream-copy).
    """
    if not segments:
        raise ValidationError("No segments selected for the highlight reel")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    filter_parts: list[str] = []
    concat_inputs: list[str] = []
    for i, seg in enumerate(segments):
        filter_parts.append(f"[0:v]trim=start={seg.start:.3f}:end={seg.end:.3f},setpts=PTS-STARTPTS[v{i}]")
        filter_parts.append(f"[0:a]atrim=start={seg.start:.3f}:end={seg.end:.3f},asetpts=PTS-STARTPTS[a{i}]")
        concat_inputs.append(f"[v{i}][a{i}]")

    filter_complex = ";".join(filter_parts)
    filter_complex += f";{''.join(concat_inputs)}concat=n={len(segments)}:v=1:a=1[outv][outa]"

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "[outv]",
        "-map",
        "[outa]",
        str(output_path),
    ]

    logger.info(
        "Rendering highlight reel from %d segment(s), total %.1fs",
        len(segments),
        sum(seg.duration for seg in segments),
    )

    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=FFMPEG_RENDER_TIMEOUT_SECONDS, check=False
        )
    except FileNotFoundError as exc:
        logger.error("ffmpeg binary not found on PATH")
        raise ValidationError("ffmpeg is not available on this server") from exc
    except subprocess.TimeoutExpired as exc:
        raise ValidationError("Highlight rendering timed out") from exc

    if result.returncode != 0:
        logger.error("ffmpeg render failed (exit=%s): %s", result.returncode, result.stderr[-2000:])
        raise ValidationError(f"ffmpeg failed to render highlight reel (exit code {result.returncode})")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ValidationError("ffmpeg reported success but produced no output file")

    logger.info("Highlight render complete: %s -> %s", input_path, output_path)
