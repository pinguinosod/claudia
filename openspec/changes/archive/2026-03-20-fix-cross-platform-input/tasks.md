## 1. Replace Unix input imports

- [x] 1.1 Remove `import curses` from the Unix branch of the try/except import block; add `import termios`, `import tty`, `import select`, `import sys`
- [x] 1.2 Remove `_curses_win` global variable
- [x] 1.3 Add `_original_terminal_attrs` global to store terminal state for restore

## 2. Implement raw terminal context manager

- [x] 2.1 Implement `_raw_terminal()` context manager using `termios.tcgetattr()` + `tty.setraw()` in `__enter__` and `termios.tcsetattr()` in `__exit__`
- [x] 2.2 Guard `tty.setraw()` with try/except for the case stdin is not a tty (redirected input)

## 3. Rewrite Unix input functions

- [x] 3.1 Rewrite `_get_key_unix()` using `select.select([sys.stdin], [], [], 0)` for non-blocking check, then `sys.stdin.read(1)` to read one byte
- [x] 3.2 Implement ANSI escape sequence parsing: after `\x1b`, use `select` with timeout=0 to check for `[` + direction byte (`A/B/C/D`)
- [x] 3.3 Rewrite `_get_raw_key_unix()` with same termios approach, returning any printable ASCII char or nav sentinel
- [x] 3.4 Rewrite `_flush_input()` on Unix to drain stdin with `select` loop instead of `get_key()` loop

## 4. Update main() entry point

- [x] 4.1 Replace `curses.initscr()` / `curses.noecho()` / `curses.cbreak()` / `_curses_win.keypad()` / `_curses_win.nodelay()` with `_raw_terminal()` context manager
- [x] 4.2 Remove `curses.nocbreak()` / `curses.echo()` / `curses.endwin()` from the finally block

## 5. Update documentation

- [x] 5.1 Update AGENTS.md: change "Platform-specific input: msvcrt (Windows), curses (Unix)" to "msvcrt (Windows), termios+tty+select (Unix)"
- [x] 5.2 Update openspec/config.yaml context section with same change

## 6. Verification

- [x] 6.1 Test manually on macOS: launch game, navigate menus, play a song, exit cleanly
- [x] 6.2 Test manually on macOS: crash the game (Ctrl+C), verify terminal is not left in raw mode
- [x] 6.3 Verify all existing tests still pass: `uv run python -m unittest src.test_scoring src.test_layout -v`
