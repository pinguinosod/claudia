# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Keep this file up to date, if you change something that makes some information here obsolete or outdated, or you find something outdated here, then update this file with the new information.

Do not hesitate to apply the boyscout rule.

## Development Commands

```bash
# Install dependencies
uv sync

# Run the game
uv run main.py

# Generate charts for a new song
uv run python src/analyze.py "assets/songs/your song.mp3"

# Run tests
uv run python -m unittest src.test_scoring -v
```

## Tech Stack

- **Python 3.12+** — Core language
- **uv** — Package manager and virtual environment
- **Rich** — Terminal UI rendering (gradients, animations, colors)
- **pygame** — Audio playback and mixing
- **librosa** — Beat detection and audio analysis for chart generation
- **pyfiglet** — ASCII art title text
- **numpy** — Numerical computations for audio analysis
- **unittest** — Test framework (stdlib)

## Architecture

**Monolithic single-loop game** with clear module separation for non-UI concerns:

- `main.py` — Game entry point: state machine, rendering, input handling, main loop (60 FPS). Contains `GameState` class (gameplay logic), `State` enum (MENU → SONG_SELECT → PLAYING → PAUSED → COUNTDOWN → RESULTS → KEYBIND), and all Rich-based rendering functions.
- `src/analyze.py` — Offline CLI tool: generates `.chart.json` files from MP3s using librosa. Three difficulty tiers (easy/hard/crazy) based on note density and lane assignment.
- `src/scoring.py` — Pure functions for score calculation (no imports, no state). Accuracy, grades, combo bonus, final score (0–1M cap).
- `src/scores.py` — Score persistence to `scores.json`. Per-song, per-difficulty best tracking.
- `src/config.py` — User config persistence to `config.json`. Key bindings (default: D, F, J, K).
- `src/theme.py` — All color constants and style data. See "Color & Theme Rules" below.
- `src/sfx.py` — Sound effects wrapper around pygame mixer. Graceful degradation if unavailable.
- `src/layout.py` — Pure functions for terminal layout calculation. Returns `Layout` dataclass with dynamic playfield dimensions based on terminal size. Minimum terminal: 80×24.
- `assets/songs/` — MP3 files and generated `.chart.json` files.
- `assets/audio/` — SFX audio assets.
- `assets/img/` — Image assets.
- `docs/` — Documentation (README, LICENSE, CREDITS).

### Platform-specific input

- **Windows:** `msvcrt` for non-blocking keys + `winmm` for high-res timing
- **Unix:** `curses` for non-blocking keys

### Hit Windows

| Grade   | Window  | Score weight |
|---------|---------|--------------|
| PERFECT | ±35ms   | 1.0x         |
| GOOD    | ±85ms   | 0.5x         |
| OK      | ±135ms  | 0.1x         |
| MISS    | >±135ms | 0x           |

### Game Loop Flow

`MENU → SONG_SELECT → PLAYING → (PAUSED via ESC) → COUNTDOWN → RESULTS → MENU`

During PLAYING: 60 FPS polling loop → check input → update note timings → check misses → render playfield

## Visual Polish & Game Juice

This is a terminal game. Every implementation should treat the terminal as a creative canvas — not just a functional interface. When adding or modifying any visual element:

- **Animate everything that can be animated.** State transitions, item reveals, selections, confirmations — none of these should be instantaneous cuts if an animation would feel better.
- **Per-character effects over per-line effects.** Rich supports building `Text` objects character by character with individual colors. Use this. Diagonal waves, scatter resolves, color blooms — think at the glyph level.
- **Easing is mandatory.** Linear interpolation looks mechanical. Default to `sin²(t × π/2)` for ease-in, `1 - cos(t × π/2)` for ease-out, or `sin(t × π)` for bell curves. Raw `t` is a last resort.
- **Color tells a story.** Use the theme gradient as a palette. Brightness flares signal energy; dark near-background colors signal dormancy or anticipation. Lerp between them deliberately.
- **Idle states should breathe.** If the player is on a screen doing nothing, something should be subtly moving — a slow sweep, a pulse, a shimmer. Static screens feel dead.
- **Timing matters as much as the effect itself.** A good animation at the wrong speed is worse than no animation. Err toward slightly faster than feels natural — terminal rendering adds perceived lag.
- **Juice the interactions.** Selection changes, menu confirms, screen transitions — each should have a micro-animation or color pop that acknowledges the input. Make the UI feel responsive and alive.

## Color & Theme Rules

All colors live in `src/theme.py`. Never hardcode hex color strings in `main.py` or any other file.

- **Adding a new color**: define it in `theme.py` with a semantic name, then reference it as `theme.MY_COLOR`.
- **Reusing an existing color for a new purpose**: reference the existing `theme.*` constant — do not copy the hex value.
- **Color dicts / lookups** (e.g. grade → color maps) also belong in `theme.py` since they are pure style data.

The one exception: inline lerp computations that produce a transient color value (e.g. `_lerp_single_color(theme.A, theme.B, t)`) stay in the rendering code — those are algorithmic, not named colors.

## Playfield Math

**All playfield dimensions are now dynamic**, calculated by `src/layout.py` based on terminal size. The `_update_layout()` function in `main.py` recalculates every frame.

### Row-mapping formula

```
row_f = HIT_ZONE_ROW * (1.0 - ahead_ms / window_ms)
```
`window_ms = NOTE_FALL_WINDOW_S * 1000`. Notes enter at `row_f=0` (top) and cross the separator at `row_f=HIT_ZONE_ROW` (PERFECT line).

### Dynamic dimensions (from `layout.calc()`)

- `hit_zone_row = max(16, terminal_rows - 8)`
- `ghost_rows = ceil(hit_zone_row * MISS_LINGER_MS / NOTE_FALL_WINDOW_MS) + 1`
- `playfield_rows = hit_zone_row + ghost_rows`
- `ripple_duration = hit_zone_row / 44.0`
- Marker rows auto-computed from hit_zone_row and timing constants

### Ghost zone invariant (validated automatically)

`hit_zone_row * (1 + MISS_LINGER_MS / window_ms) < playfield_rows`

This is asserted inside `layout.calc()` — if it fails, the program crashes with a clear message.

### Minimum terminal size

80 columns × 24 rows. Below this, the game shows a warning instead of rendering.

### Scaling checklist (when changing timing constants)

1. Update constants in `src/layout.py`
2. Run tests: `cd src && uv run python -m unittest test_layout -v`
3. Ghost expiry invariant is validated automatically by `layout.calc()`
