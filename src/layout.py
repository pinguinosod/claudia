"""Terminal layout calculation — pure functions, no game state."""

import math
from dataclasses import dataclass

MIN_COLS = 80
MIN_ROWS = 24

# Timing constants (duplicated from main to keep this module dependency-free)
_MISS_LINGER_MS = 250
_NOTE_FALL_WINDOW_MS = 2000.0
_OK_MS = 135
_GOOD_MS = 85

# Fixed rows reserved for UI chrome (title, separators, labels, padding)
_RESERVED_ROWS = 8
_MIN_HIT_ZONE_ROW = 16


@dataclass(frozen=True)
class Layout:
    hit_zone_row: int
    ghost_rows: int
    playfield_rows: int
    screen_height: int
    playfield_content_height: int
    ok_marker_row: int
    good_marker_row: int
    ripple_duration: float


def is_terminal_valid(cols: int, rows: int) -> bool:
    return cols >= MIN_COLS and rows >= MIN_ROWS


def calc(cols: int, rows: int) -> Layout:
    """Calculate all playfield dimensions from terminal size.

    Pure function: same input always produces same output.
    """
    hit_zone_row = max(_MIN_HIT_ZONE_ROW, rows - _RESERVED_ROWS)
    # Ghost rows scale with hit_zone_row to satisfy expiry invariant
    ghost_rows = math.ceil(hit_zone_row * _MISS_LINGER_MS / _NOTE_FALL_WINDOW_MS) + 1
    playfield_rows = hit_zone_row + ghost_rows
    screen_height = playfield_rows + (_RESERVED_ROWS - ghost_rows)
    playfield_content_height = 2 + hit_zone_row + 1 + ghost_rows + 1

    window_ms = _NOTE_FALL_WINDOW_MS
    ok_marker_row = int(hit_zone_row * (1.0 - _OK_MS / window_ms))
    good_marker_row = int(hit_zone_row * (1.0 - _GOOD_MS / window_ms))
    ripple_duration = hit_zone_row / 44.0

    # Validate ghost expiry invariant
    assert hit_zone_row * (1.0 + _MISS_LINGER_MS / window_ms) < playfield_rows, (
        f"Ghost expiry violated: hit_zone_row={hit_zone_row}, "
        f"playfield_rows={playfield_rows}"
    )

    return Layout(
        hit_zone_row=hit_zone_row,
        ghost_rows=ghost_rows,
        playfield_rows=playfield_rows,
        screen_height=screen_height,
        playfield_content_height=playfield_content_height,
        ok_marker_row=ok_marker_row,
        good_marker_row=good_marker_row,
        ripple_duration=ripple_duration,
    )
