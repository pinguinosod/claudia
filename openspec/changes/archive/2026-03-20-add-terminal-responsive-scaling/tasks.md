## 1. Layout module

- [x] 1.1 Create `src/layout.py` with a pure function that receives `(cols, rows)` and returns a dataclass with: `hit_zone_row`, `playfield_rows`, `screen_height`, `playfield_content_height`, `ok_marker_row`, `good_marker_row`, `ripple_duration`
- [x] 1.2 Implement clamping: `hit_zone_row = max(16, terminal_rows - 8)`
- [x] 1.3 Validate ghost expiry invariant inside the function
- [x] 1.4 Define constants `MIN_COLS = 80`, `MIN_ROWS = 24` and function `is_terminal_valid(cols, rows) -> bool`

## 2. Layout module tests

- [x] 2.1 Test: dimensions for 80x30 terminal (current equivalent case)
- [x] 2.2 Test: minimum clamping with 80x24 terminal (`hit_zone_row` = 16)
- [x] 2.3 Test: large terminal 120x50 scales correctly
- [x] 2.4 Test: determinism (same input = same output)
- [x] 2.5 Test: ghost expiry invariant holds for row range 24-60

## 3. Integration in main.py

- [x] 3.1 Replace fixed constants (`HIT_ZONE_ROW`, `PLAYFIELD_ROWS`, `SCREEN_HEIGHT`, `_PLAYFIELD_CONTENT_HEIGHT`) with a call to `layout.calc(cols, rows)` at the start of each frame
- [x] 3.2 Propagate dynamic dimensions to all playfield render functions
- [x] 3.3 Propagate dimensions to menu, song select, and results render functions
- [x] 3.4 Update marker rows and ripple duration calculations to use dynamic values

## 4. Small terminal screen

- [x] 4.1 Create render function for a centered "terminal too small" warning message
- [x] 4.2 Integrate minimum size check at the start of each frame: if smaller than 80x24, show warning instead of rendering
- [x] 4.3 During PLAYING, automatically pause the game if the terminal drops below the minimum
- [x] 4.4 Automatically resume when the terminal returns to a valid size

## 5. Verification

- [x] 5.1 Manually test by resizing the terminal during gameplay
- [x] 5.2 Verify that `src/layout.py` does not exceed 150 lines
- [x] 5.3 Update CLAUDE.md with the new dynamic constants and the reference to `src/layout.py`
