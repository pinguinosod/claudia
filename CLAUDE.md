# Claudia — Project Guidelines

Keep this file up to date, if you change something that makes some information here obsolte or outdated, or you find something outdated here, then update this file with the new information.

Do not hesitate to apply the boyscout rule

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

All colors live in `theme.py`. Never hardcode hex color strings in `main.py` or any other file.

- **Adding a new color**: define it in `theme.py` with a semantic name, then reference it as `theme.MY_COLOR`.
- **Reusing an existing color for a new purpose**: reference the existing `theme.*` constant — do not copy the hex value.
- **Color dicts / lookups** (e.g. grade → color maps) also belong in `theme.py` since they are pure style data.

The one exception: inline lerp computations that produce a transient color value (e.g. `_lerp_single_color(theme.A, theme.B, t)`) stay in the rendering code — those are algorithmic, not named colors.

## Playfield Math

### Row-mapping formula

```
row_f = HIT_ZONE_ROW * (1.0 - ahead_ms / window_ms)
```
`window_ms = NOTE_FALL_WINDOW_S * 1000`. Notes enter at `row_f=0` (top) and cross the separator at `row_f=HIT_ZONE_ROW` (PERFECT line).

### Marker rows (auto-computed — never hardcode)

```python
_OK_MARKER_ROW   = int(HIT_ZONE_ROW * (1.0 - OK_MS   / (NOTE_FALL_WINDOW_S * 1000)))
_GOOD_MARKER_ROW = int(HIT_ZONE_ROW * (1.0 - GOOD_MS  / (NOTE_FALL_WINDOW_S * 1000)))
```

These rows mark where a falling note crosses into GOOD and OK hit windows respectively. A note at `row_f = _GOOD_MARKER_ROW` has exactly `GOOD_MS` milliseconds until it reaches the hit zone. Do not hardcode the resulting row numbers — they shift whenever timing constants are rebalanced.

### Ghost zone sizing rule

```
PLAYFIELD_ROWS = HIT_ZONE_ROW + 3
```

Verify ghost expiry fits: `HIT_ZONE_ROW * (1 + MISS_LINGER_MS / window_ms) < PLAYFIELD_ROWS`

Recheck this inequality whenever `HIT_ZONE_ROW`, `MISS_LINGER_MS`, or `NOTE_FALL_WINDOW_S` change — if it fails, missed notes render outside the playfield.

### Ripple speed

In-field and side-rail ripples both use **0.5s** so they travel at the same apparent speed.
Rule: `ripple_duration = HIT_ZONE_ROW / 44.0` seconds. Scale this whenever HIT_ZONE_ROW changes.

### Scaling checklist (when changing HIT_ZONE_ROW)

1. Update `HIT_ZONE_ROW`
2. Update `PLAYFIELD_ROWS = HIT_ZONE_ROW + 3`
3. Update `_PLAYFIELD_CONTENT_HEIGHT` (add the row delta to the old value)
4. Scale ripple duration: `HIT_ZONE_ROW / 44.0` (both in-field and side-rail)
5. Verify ghost expiry: `HIT_ZONE_ROW * (1 + MISS_LINGER_MS/2000) < PLAYFIELD_ROWS`
6. `SIGMA_CORE` — no change needed; note separation improves naturally with more rows
