## ADDED Requirements

### Requirement: Non-blocking Unix input without curses
The system MUST read keyboard input on Unix using `termios`, `tty`, and `select` from the Python stdlib. The `curses` module MUST NOT be imported or used anywhere in the codebase.

#### Scenario: Lane key press detected
- **GIVEN** the game is running on macOS or Linux
- **WHEN** the user presses a lane key (d, f, j, k by default)
- **THEN** `get_key()` MUST return the corresponding character without blocking the game loop

#### Scenario: Arrow key detected
- **GIVEN** the game is on a menu screen
- **WHEN** the user presses an arrow key
- **THEN** `get_key()` MUST return `"up"`, `"down"`, `"left"`, or `"right"` respectively

#### Scenario: No input available
- **GIVEN** the user is not pressing any key
- **WHEN** `get_key()` is called
- **THEN** it MUST return `None` immediately without blocking

### Requirement: Terminal state restoration
The system MUST restore the original terminal state on exit, including when the game exits due to an unhandled exception.

#### Scenario: Normal exit
- **GIVEN** the game is running
- **WHEN** the user exits normally (ESC → Exit)
- **THEN** the terminal MUST be restored to its pre-game state (echo on, canonical mode)

#### Scenario: Crash exit
- **GIVEN** the game is running
- **WHEN** an unhandled exception occurs
- **THEN** the terminal MUST still be restored (not left in raw mode)

### Requirement: ESC vs arrow key disambiguation
The system MUST correctly distinguish between an ESC keypress and the start of an ANSI arrow key escape sequence (`\x1b[A/B/C/D`).

#### Scenario: ESC key alone
- **GIVEN** the user presses only the ESC key
- **WHEN** `get_key()` processes the input
- **THEN** it MUST return `"esc"` and not `None` or an arrow key

#### Scenario: Arrow key sequence
- **GIVEN** the user presses the Up arrow key (sends `\x1b[A`)
- **WHEN** `get_key()` processes the input
- **THEN** it MUST return `"up"` and consume all 3 bytes of the sequence

### Requirement: Windows input unchanged
The system MUST continue to use `msvcrt` for keyboard input on Windows. The termios-based implementation MUST only activate on non-Windows platforms.

#### Scenario: Windows detection
- **GIVEN** the game is running on Windows
- **WHEN** `get_key()` is called
- **THEN** it MUST use the `msvcrt` code path, identical to current behavior
