# AGENTS.md

Terminal rhythm game (Guitar Hero style) built with Python 3.12, Rich for TUI rendering, and pygame for audio.

## Commands

```bash
uv sync                                        # Install dependencies
uv run main.py                                 # Run the game
uv run python src/analyze.py "assets/songs/x.mp3"  # Generate chart from MP3
uv run python -m unittest src.test_scoring -v  # Run scoring tests
```

## Tech stack

- **Runtime**: Python 3.12+
- **Package manager**: uv (pyproject.toml + uv.lock)
- **TUI**: Rich >=13.0 (gradients, animations, per-character color)
- **Audio**: pygame >=2.5 (playback + mixer for SFX)
- **Analysis**: librosa >=0.10 (beat detection, chart generation)
- **ASCII art**: pyfiglet >=0.8
- **Numerical**: numpy >=1.24
- **Testing**: unittest (stdlib)

## Project structure

```
main.py              — Game entry point: state machine, render, input, 60 FPS loop
src/
  analyze.py         — CLI tool: generates .chart.json from MP3 via librosa
  scoring.py         — Pure functions: accuracy, grades, combo, score
  scores.py          — Score persistence to scores.json
  config.py          — User config persistence to config.json
  theme.py           — All color constants and style data
  sfx.py             — SFX wrapper over pygame mixer
  test_scoring.py    — Unit tests for scoring.py
assets/
  songs/             — MP3 files + generated .chart.json files
  audio/             — SFX audio assets (.mp3)
  img/               — Image assets
docs/                — README, LICENSE, CREDITS
openspec/            — Spec-Driven Development artifacts
pyproject.toml       — Project metadata and dependencies
uv.lock              — Locked dependency versions
```

## Code style

- Named exports only (no `__all__`, no default-like patterns)
- Functions small and focused, files max 150 lines (except main.py — legacy)
- Pure functions preferred: scoring.py has zero imports, zero state
- Atomic writes for persistence (tempfile + os.replace)
- Platform-specific input: `msvcrt` (Windows), `curses` (Unix)

## Reference files

- `src/scoring.py` — Best example: pure functions, no state, well-tested
- `src/theme.py` — Color convention: all hex values here, nowhere else
- `src/config.py` — Persistence pattern: load with defaults, atomic save
- `src/sfx.py` — Graceful degradation pattern: no-op when unavailable

## Testing

- Framework: `unittest` (stdlib)
- Test files: `src/test_*.py`
- Run: `uv run python -m unittest src.test_scoring -v`
- Coverage: only `scoring.py` has tests currently

## Git workflow

- Commits: `feat:` / `fix:` / `refactor:` prefix format
- Atomic commits with descriptive messages
- No Co-Authored-By in commit messages

## Boundaries

### Always do
- Define new colors in `src/theme.py` with semantic names
- Use easing functions for animations (never linear interpolation)
- Auto-compute playfield math from constants (never hardcode row numbers)
- Validate playfield inequalities when changing timing constants

### Ask first
- Adding new Python dependencies
- Structural changes to game loop or state machine
- Changes to hit windows or scoring weights
- Modifications to main.py (high risk of regressions)

### Never do
- Hardcode hex color strings outside `src/theme.py`
- Use linear `t` for animations (use sin²/cos easing)
- Skip tests when modifying `src/scoring.py`
- Create files exceeding 150 lines
- Push to remote without explicit request
