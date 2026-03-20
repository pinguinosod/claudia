## Context

The game uses `curses.initscr()` on Unix for non-blocking keyboard input. Rich's `Live(screen=True)` also takes control of the terminal via alternate screen buffer. These two systems conflict on macOS: curses sets the terminal to raw mode and intercepts stdout, while Rich writes directly to stdout. The result is visual artifacts, garbled display, and input dropping.

Current Unix input flow:
```
main() → curses.initscr() → [game loop] → _curses_win.getch() → curses.endwin()
                                ↕ conflict
                          Live(screen=True) → Rich renders
```

## Goals / Non-Goals

**Goals:**
- Eliminate `curses` dependency from the input path entirely
- Restore terminal state on exit (even on crash)
- Preserve exact same input API: `get_key()` and `get_raw_key()` return identical values
- Work on macOS and Linux without new dependencies

**Non-Goals:**
- Fixing Windows input (msvcrt works correctly, unchanged)
- Supporting non-ANSI terminals (VT100+ assumed, same as Rich)
- Handling keyboard events outside ASCII + standard arrow/nav keys

## Decisions

### 1. termios + tty + select as curses replacement

`termios.tcgetattr()` saves terminal state. `tty.setraw()` puts stdin into raw mode (no echo, character-by-character). `select.select([sys.stdin], [], [], 0)` checks for available input without blocking. `sys.stdin.read(1)` reads one byte.

**Why over curses**: `tty.setraw()` does not initialize an alternate screen or set up a window abstraction — it only changes terminal mode. Rich's Live keeps full control of rendering. No conflict.

**Why over pynput/readchar**: Zero new dependencies. `termios`+`tty`+`select` are stdlib on all Unix platforms including macOS.

### 2. ANSI escape sequence parsing for arrow keys

Arrow keys send multi-byte sequences: `\x1b` `[` `A/B/C/D`. After reading `\x1b`, a second `select` with timeout=0 checks if more bytes follow. If yes → arrow key. If no → Escape key press.

```
Read \x1b
  ├─ select timeout=0 → more bytes? → read '[' then 'A/B/C/D' → arrow
  └─ no more bytes → ESC
```

**Why this matters**: On curses, `KEY_UP` etc. were handled by the library. With raw termios we parse sequences manually — simple but explicit.

### 3. Context manager for terminal state

Wrap raw mode in a context manager (`_raw_terminal()`) that guarantees `tcsetattr` restore in the `finally` block, even if the game crashes. This replaces the `curses.endwin()` cleanup in `main()`.

### 4. _flush_input drains with select loop

`_flush_input()` now calls `select.select` in a loop until stdin is empty, instead of calling `get_key()` repeatedly. Avoids any latency from byte-by-byte reads during flush.

## Risks / Trade-offs

- **[SSH sessions]** → ANSI sequences are standard over SSH. No regression expected.
- **[Terminal emulators with non-standard arrow sequences]** → Extremely rare. All modern terminals (Terminal.app, iTerm2, GNOME Terminal, Alacritty, kitty) use standard ANSI. Mitigation: fail silently (return None), same as current curses behavior.
- **[tty.setraw() on non-tty stdin]** → If stdin is redirected (e.g. `python main.py < file`), `tty.setraw()` raises. Mitigation: catch and run without raw mode (game becomes unplayable but doesn't crash).
