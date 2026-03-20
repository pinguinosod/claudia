## Why

The game uses fixed dimensions (`SCREEN_HEIGHT = 30`, `HIT_ZONE_ROW = 22`, `PLAYFIELD_ROWS = 25`) that assume a fullscreen terminal. When the user reduces the terminal size, the content gets clipped or overflows without adaptation, making the game unplayable in small terminals.

## What Changes

- Detect the terminal size in real time using `os.get_terminal_size()` or Rich's `console.size`
- Dynamically recalculate the playfield constants (`HIT_ZONE_ROW`, `PLAYFIELD_ROWS`, `SCREEN_HEIGHT`) based on the available size
- Adapt all UI elements (menus, song select, results, playfield) to the available width and height
- Define minimum sizes: if the terminal is too small, show a warning message instead of rendering broken UI
- Re-detect the size on each game loop frame to respond to live resizing

## Capabilities

### New Capabilities
- `terminal-scaling`: Terminal size detection and dynamic calculation of playfield and UI dimensions

### Modified Capabilities
(none — no prior specs exist)

## Impact

- **main.py**: All render functions and playfield dimension constants. This is the most affected file since it concentrates all rendering logic.
- **Visual impact**: The playfield will have fewer approach rows in small terminals (notes fall visually faster). Menus and results screen will be compacted. Easing animations are preserved but operate over dynamic ranges.
- **Unaffected modules**: `src/scoring.py`, `src/scores.py`, `src/config.py`, `src/analyze.py` — they do not depend on terminal dimensions.
- **No new dependencies**: `os.get_terminal_size()` is stdlib, Rich already exposes `console.size`.
