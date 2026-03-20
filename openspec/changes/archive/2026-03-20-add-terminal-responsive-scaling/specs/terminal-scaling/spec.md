## ADDED Requirements

### Requirement: Dynamic terminal size detection
The system MUST query the terminal dimensions at the start of each render frame and recalculate all playfield dimensions accordingly.

#### Scenario: Terminal resized during gameplay
- **GIVEN** the game is in PLAYING state
- **WHEN** the user resizes the terminal window
- **THEN** the playfield MUST adapt to the new dimensions within the next frame (≤16ms)

#### Scenario: Terminal resized on menu screen
- **GIVEN** the game is in MENU, SONG_SELECT, or RESULTS state
- **WHEN** the user resizes the terminal window
- **THEN** all UI elements MUST re-render adapted to the new size

### Requirement: Minimum terminal size enforcement
The system MUST define a minimum terminal size of 80 columns × 24 rows. If the terminal is smaller, the game MUST display a centered warning message instead of rendering broken UI.

#### Scenario: Terminal below minimum size during gameplay
- **GIVEN** the game is in PLAYING state
- **WHEN** the terminal is resized below 80×24
- **THEN** the game MUST pause and display a message requesting the user to enlarge the terminal

#### Scenario: Terminal restored to valid size
- **GIVEN** the game is paused due to small terminal
- **WHEN** the terminal is resized back to ≥80×24
- **THEN** the game MUST resume normal rendering automatically

#### Scenario: Game launched in small terminal
- **GIVEN** the terminal size is below 80×24 at launch
- **WHEN** the user starts the game
- **THEN** the system MUST show the size warning on the initial screen

### Requirement: Proportional playfield scaling
The system MUST calculate `hit_zone_row` proportionally to the terminal height, reserving fixed rows for UI chrome (title, separators, ghost zone, labels). All derived dimensions (`playfield_rows`, marker rows, ripple duration) MUST be recalculated from `hit_zone_row`.

#### Scenario: Large terminal (40+ rows)
- **GIVEN** the terminal has 40 or more rows
- **WHEN** the playfield renders
- **THEN** `hit_zone_row` MUST be `terminal_rows - 8` and `playfield_rows` MUST be `hit_zone_row + 3`

#### Scenario: Minimum clamping
- **GIVEN** the terminal has exactly 24 rows
- **WHEN** the playfield dimensions are calculated
- **THEN** `hit_zone_row` MUST NOT be less than 16

### Requirement: Layout calculation module
The system MUST provide a pure function in `src/layout.py` that receives terminal dimensions `(cols, rows)` and returns all calculated playfield dimensions. This function MUST have no side effects and no dependencies on game state.

#### Scenario: Layout calculation is deterministic
- **GIVEN** a terminal size of 80×30
- **WHEN** the layout function is called multiple times with the same input
- **THEN** it MUST return identical dimensions every time

#### Scenario: Layout preserves playfield math invariants
- **GIVEN** any valid terminal size (≥80×24)
- **WHEN** layout dimensions are calculated
- **THEN** the ghost expiry inequality MUST hold: `hit_zone_row * (1 + MISS_LINGER_MS / window_ms) < playfield_rows`
