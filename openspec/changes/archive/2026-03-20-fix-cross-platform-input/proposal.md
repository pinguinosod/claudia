## Why

On macOS, `curses.initscr()` and Rich's `Live(screen=True)` both compete for terminal control, producing visual artifacts, broken display, and unresponsive input. Replacing `curses` with `termios`+`tty`+`select` (all Python stdlib) eliminates this conflict without adding dependencies.

## What Changes

- Replace `import curses` + `curses.initscr()` with `termios`/`tty`/`select` on Unix (macOS + Linux)
- Remove `_curses_win` global and all `curses.*` calls
- Implement ANSI escape sequence parsing for arrow keys (`\x1b[A/B/C/D`)
- Replace `curses.endwin()` cleanup with `termios.tcsetattr()` restore
- Windows path (`msvcrt`) remains unchanged
- No new dependencies

## Capabilities

### New Capabilities
- `unix-input`: Non-blocking keyboard input on Unix using termios+tty+select, replacing curses

### Modified Capabilities
- `terminal-scaling`: No requirement changes — input layer is independent of layout calculation

## Impact

- **main.py**: `main()` function (init/cleanup), `_get_key_unix()`, `_get_raw_key_unix()`, `_flush_input()`, import block
- **No other modules affected**: scoring, layout, theme, sfx, config, scores are all input-independent
- **No new dependencies**: `termios`, `tty`, `select` are Python stdlib (Unix only, same as `curses`)
- **Windows unchanged**: `msvcrt` path untouched
