# AGENTS.md

Terminal rhythm game (Guitar Hero style) built with Python 3.12, Rich for TUI rendering, and pygame for audio.

## Commands

```bash
pip install -r requirements.txt    # Install dependencies
python main.py                     # Run the game
python analyze.py "songs/x.mp3"   # Generate chart from MP3 (3 difficulties)
python -m unittest test_scoring -v # Run scoring tests
```

## Tech stack

- **Runtime**: Python 3.12+
- **TUI**: Rich >=13.0 (gradients, animations, per-character color)
- **Audio**: pygame >=2.5 (playback + mixer for SFX)
- **Analysis**: librosa >=0.10 (beat detection, chart generation)
- **ASCII art**: pyfiglet >=0.8
- **Numerical**: numpy >=1.24
- **Testing**: unittest (stdlib)

## Project structure

```
main.py          — Game engine: state machine, render, input, 60 FPS loop (1931 lines)
analyze.py       — CLI tool: generates .chart.json from MP3 via librosa (452 lines)
scoring.py       — Pure functions: accuracy, grades, combo, score (73 lines)
scores.py        — Score persistence to scores.json (89 lines)
config.py        — User config persistence to config.json (35 lines)
theme.py         — All color constants and style data (65 lines)
sfx.py           — SFX wrapper over pygame mixer (56 lines)
test_scoring.py  — Unit tests for scoring.py (143 lines)
songs/           — MP3 files + generated .chart.json files
audio/           — SFX audio assets (.mp3)
openspec/        — Spec-Driven Development artifacts
```

## Code style

- Named exports only (no `__all__`, no default-like patterns)
- Functions small and focused, files max 150 lines (except main.py — legacy)
- Pure functions preferred: scoring.py has zero imports, zero state
- Atomic writes for persistence (tempfile + os.replace)
- Platform-specific input: `msvcrt` (Windows), `curses` (Unix)

## Reference files

- `scoring.py` — Best example: pure functions, no state, well-tested
- `theme.py` — Color convention: all hex values here, nowhere else
- `config.py` — Persistence pattern: load with defaults, atomic save
- `sfx.py` — Graceful degradation pattern: no-op when unavailable

## Testing

- Framework: `unittest` (stdlib)
- Test files: `test_*.py` at project root
- Run: `python -m unittest test_scoring -v`
- Coverage: only `scoring.py` has tests currently

## Git workflow

- Commits: `feat:` / `fix:` / `refactor:` prefix format
- Atomic commits with descriptive messages
- No Co-Authored-By in commit messages

## Boundaries

### Always do
- Define new colors in `theme.py` with semantic names
- Use easing functions for animations (never linear interpolation)
- Auto-compute playfield math from constants (never hardcode row numbers)
- Validate playfield inequalities when changing timing constants

### Ask first
- Adding new Python dependencies
- Structural changes to game loop or state machine
- Changes to hit windows or scoring weights
- Modifications to main.py (1931 lines — high risk of regressions)

### Never do
- Hardcode hex color strings outside `theme.py`
- Use linear `t` for animations (use sin²/cos easing)
- Skip tests when modifying `scoring.py`
- Create files exceeding 150 lines
- Push to remote without explicit request
