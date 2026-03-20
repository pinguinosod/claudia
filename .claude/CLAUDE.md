# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Keep this file up to date, if you change something that makes some information here obsolete or outdated, or you find something outdated here, then update this file with the new information.

Do not hesitate to apply the boyscout rule.

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
