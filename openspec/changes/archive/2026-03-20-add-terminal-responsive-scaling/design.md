## Context

The game uses fixed constants to size the playfield: `HIT_ZONE_ROW = 22`, `PLAYFIELD_ROWS = 25`, `SCREEN_HEIGHT = 30`. All render functions in `main.py` depend on these values. Rich handles width automatically with `Align.center()` and `Table`, but the height is hardcoded.

## Goals / Non-Goals

**Goals:**
- Calculate playfield dimensions dynamically based on `os.get_terminal_size()`
- Maintain proportions and playability across terminals of different sizes
- Define a minimum size and show a warning if it is not met
- Preserve the existing playfield math formula (only parameterized)

**Non-Goals:**
- Adapt lane width (Rich already centers content)
- Change scoring logic or hit windows based on terminal size
- Support terminals with fewer than 80 columns wide

## Decisions

### 1. `src/layout.py` module for dimension calculation

Extract all dimension logic into a new `src/layout.py` module with a pure function that receives `(cols, rows)` from the terminal and returns a dataclass/dict with all calculated dimensions: `hit_zone_row`, `playfield_rows`, `screen_height`, `playfield_content_height`, marker rows, ripple duration.

**Why**: Keeps `main.py` focused on rendering and game loop. Allows testing scaling formulas independently. Follows the pure module pattern like `scoring.py`.

**Discarded alternative**: Calculate inline in `main.py` — adds complexity to an already large file (1931 lines).

### 2. Recalculate per frame, not per resize event

Call the calculation function at the start of each game loop frame (already runs at 60 FPS). The cost of `os.get_terminal_size()` is negligible (~1us).

**Why**: There is no reliable cross-platform resize signal. Per-frame polling is simple and universally compatible. It does not require signal handlers (`SIGWINCH` only works on Unix).

### 3. Minimum size: 80x24

If the terminal is smaller than 80 columns or 24 rows, show a centered message asking the user to enlarge the window instead of rendering broken game UI. Pause the game loop while in "too small" mode.

**Why**: 80x24 is the standard minimum terminal size. Below this, the playfield does not have enough approach rows to be playable.

### 4. HIT_ZONE_ROW proportional to available height

`hit_zone_row = terminal_rows - 8` (reserve 8 rows for: title, separators, ghost zone, labels, padding). Clamp minimum to 16 approach rows to maintain playability.

**Why**: Scales linearly with the terminal. The 8 reserved rows cover the fixed UI elements. The minimum of 16 guarantees that notes have enough visual time for the player to react.

### 5. Derived formulas remain unchanged

- `playfield_rows = hit_zone_row + 3`
- `ripple_duration = hit_zone_row / 44.0`
- Marker rows auto-calculated from hit_zone_row
- Ghost expiry verified automatically

**Why**: The proportionality of the playfield math is preserved. Only the base value `hit_zone_row` changes.

## Risks / Trade-offs

- **[Faster notes in small terminals]** → With fewer approach rows, notes visually "fall" faster. Mitigation: the actual timing does not change (hit windows are temporal, not spatial). The player has the same time to react.
- **[Flicker during resize]** → A frame may render with stale dimensions during transition. Mitigation: Rich uses an alternate screen buffer that minimizes artifacts. Per-frame recalculation corrects within <=16ms.
- **[main.py already has 1931 lines]** → Adding resize logic inline would make it worse. Mitigation: the `src/layout.py` module absorbs all calculation complexity.
