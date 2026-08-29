"""Video flipping via the `ffmpeg` CLI.

We shell out to the `ffmpeg` binary directly with `subprocess` rather than
using the `ffmpeg-python` package. `ffmpeg-python` is a thin wrapper that
mostly builds the same argv and still requires the `ffmpeg` binary to be
on PATH; since the Docker image already ships that binary, invoking it
directly keeps one fewer dependency in `requirements.txt` and makes the
exact command being run (and its filter graph) explicit and easy to
reason about/test.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Literal

from app.exceptions import ValidationError

logger = logging.getLogger(__name__)

_FILTERS: dict[str, str] = {
    "horizontal": "hflip",
    "vertical": "vflip",
    "both": "hflip,vflip",
}

FFMPEG_TIMEOUT_SECONDS = 15 * 60  # generous ceiling for a <=10min / <=200MB input


def flip_video(
    input_path: Path,
    output_path: Path,
    direction: Literal["horizontal", "vertical", "both"],
) -> None:
    """Flip the video at `input_path` and write the result to `output_path`.

    Uses ffmpeg's `hflip` / `vflip` video filters (chained for "both").
    Audio is copied through untouched. Raises `ValidationError` if ffmpeg
    is missing or exits non-zero.
    """
    if direction not in _FILTERS:
        raise ValidationError(f"Unsupported flip direction: {direction!r}")

    if not input_path.exists():
        raise ValidationError(f"Input file does not exist: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    filter_graph = _FILTERS[direction]
    command = [
        "ffmpeg",
        "-y",  # overwrite output without prompting
        "-i",
        str(input_path),
        "-vf",
        filter_graph,
        "-c:a",
        "copy",
        str(output_path),
    ]

    logger.info("Running ffmpeg flip (direction=%s): %s", direction, " ".join(command))

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=FFMPEG_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as exc:
        logger.error("ffmpeg binary not found on PATH")
        raise ValidationError("ffmpeg is not available on this server") from exc
    except subprocess.TimeoutExpired as exc:
        logger.error("ffmpeg timed out after %ss for %s", FFMPEG_TIMEOUT_SECONDS, input_path)
        raise ValidationError("Video processing timed out") from exc

    if result.returncode != 0:
        logger.error("ffmpeg failed (exit=%s): %s", result.returncode, result.stderr[-2000:])
        raise ValidationError(f"ffmpeg failed to flip video (exit code {result.returncode})")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ValidationError("ffmpeg reported success but produced no output file")

    logger.info("Flip complete: %s -> %s", input_path, output_path)
