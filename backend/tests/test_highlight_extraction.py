"""Unit tests for the pure segment-selection logic in `highlight_extraction`.

`detect_active_segments`, `probe_duration_seconds`, and
`render_highlight_reel` all shell out to real ffmpeg/ffprobe binaries and
are exercised (mocked) at the pipeline level in `test_highlights.py`
instead of here, per the project's rule against hitting real
network/subprocess dependencies in the test suite.
"""

from __future__ import annotations

from app.services.highlight_extraction import Segment, select_highlight_segments


def test_segment_duration_property() -> None:
    assert Segment(10.0, 25.5).duration == 15.5


def test_select_highlight_segments_keeps_all_when_under_target() -> None:
    segments = [Segment(0, 5), Segment(10, 50), Segment(60, 65)]  # durations: 5, 40, 5 = 50 total

    selected = select_highlight_segments(segments, total_duration=65, target_duration=60)

    assert selected == [Segment(0, 5), Segment(10, 50), Segment(60, 65)]


def test_select_highlight_segments_trims_a_single_long_segment_to_target() -> None:
    segments = [Segment(0, 100)]

    selected = select_highlight_segments(segments, total_duration=100, target_duration=60)

    assert selected == [Segment(0, 60)]


def test_select_highlight_segments_picks_longest_first_then_reorders_chronologically() -> None:
    # Durations: 10, 5, 50. Greedy-by-length takes the 50s and 10s segments
    # (60s total) and skips the 5s one, then returns them in original
    # (chronological) order -- not selection order.
    segments = [Segment(0, 10), Segment(20, 25), Segment(30, 80)]

    selected = select_highlight_segments(segments, total_duration=80, target_duration=60)

    assert [s.start for s in selected] == [0, 30]
    assert selected[-1].duration == 50


def test_select_highlight_segments_falls_back_to_start_when_none_detected() -> None:
    selected = select_highlight_segments([], total_duration=120, target_duration=60)

    assert selected == [Segment(0.0, 60.0)]


def test_select_highlight_segments_fallback_caps_at_total_duration() -> None:
    """A source shorter than the target duration can't be padded out -- the
    fallback must not return a segment longer than the source itself."""
    selected = select_highlight_segments([], total_duration=30, target_duration=60)

    assert selected == [Segment(0.0, 30.0)]
