# Audit Criteria — Clitar Hero

## Structure and organization
- [ ] No file exceeds 150 lines of code
- [ ] Functions under 30 lines
- [ ] Clear separation: engine (main.py), pure logic (scoring.py), data (theme.py), persistence (scores.py, config.py)
- [ ] No duplicated code between modules

## Security
- [ ] No hardcoded secrets
- [ ] User inputs validated (keybindings, song files)
- [ ] JSON files parsed with error handling

## Testing
- [ ] scoring.py with complete unit tests
- [ ] analyze.py with tests for chart generation
- [ ] Pure functions covered by tests

## Performance
- [ ] Game loop maintains 60 FPS without drops
- [ ] No heavy computations inside the render loop
- [ ] Lazy loading of audio assets

## Visual and UX
- [ ] All colors defined in theme.py (no hardcoded hex values)
- [ ] Animations with easing (not linear)
- [ ] Idle screens with breathing animation
- [ ] Visual feedback on every user interaction

## Maintainability
- [ ] Game constants centralized (hit windows, scoring weights)
- [ ] Playfield math auto-calculated (no hardcoded values)
- [ ] Dead code removed
