# Girly color palette — Y2K / vaporwave / cyber-girl aesthetic

# Title art gradient (applied top → bottom)
GRADIENT_COLORS = ["#FF6EC7", "#E040FB", "#7C4DFF"]  # neon pink → electric magenta → electric violet

# Menu item colors
SELECTED_COLOR   = "bold #FF1493"  # deep pink, bold
UNSELECTED_COLOR = "#CE93D8"       # light lavender

# Other text
HELP_COLOR  = "#9575CD"  # medium lavender — good contrast on dark backgrounds
GAME_COLOR  = "#FF6EC7"  # neon pink

# Hit-grade colors
PERFECT_COLOR = "#FFFFFF"   # white flash
GOOD_COLOR    = "#FFCA28"   # warm amber-gold
OK_COLOR      = "#40C4FF"   # neon cyan
MISS_COLOR    = "#2a0a2e"   # near-black purple

# Lane colors (4 lanes)
LANE_COLORS = ["#FF6EC7", "#E040FB", "#7C4DFF", "#FF1493"]

# Hit zone
HIT_ZONE_COLOR  = "#CE93D8"   # light lavender base
HIT_FLASH_COLOR = "#FFFFFF"   # white on keypress

# Background / void (noise chars, animation fade-from)
VOID_COLOR = "#2a0a2e"   # near-black purple

# Playfield voltage field
NOTE_DARK    = "#150018"                          # deep anchor for approaching notes
DEPTH_COLORS = ["#2E003C", "#E91E8C", "#FFB0FF"]  # voltage depth gradient: dark → vivid hot pink → near-white

# Miss flash (crimson burn-out on missed note)
MISS_FLASH_COLOR = "#FF1744"   # vivid red burst on miss
MISS_FLASH_DARK  = "#120005"   # near-black anchor for the red fade

# Results screen miss label (MISS_COLOR is too dark to read as a stat)
RESULT_MISS_COLOR = "#EF9A9A"  # soft coral-pink

SPLUS_COLOR   = "#E0FFFF"   # icy cyan-white — all-PERFECT run
D_GRADE_COLOR = "#FFA040"   # orange-amber — below average but above fail

# Clear status badge colors (results screen)
PERFECT_BADGE_COLOR = "#E0FFFF"   # icy white — all-PERFECT run
FC_BADGE_COLOR      = "#B9F6CA"   # mint-cyan green — full combo, no miss

# Hit-grade color lookup (for in-game effects)
GRADE_COLORS = {
    "PERFECT": PERFECT_COLOR,
    "GOOD":    GOOD_COLOR,
    "OK":      OK_COLOR,
    "MISS":    MISS_COLOR,
}

# Results screen grade letter colors
RESULT_GRADE_COLORS = {
    "S+": SPLUS_COLOR,
    "S":  PERFECT_COLOR,
    "A":  GOOD_COLOR,
    "B":  OK_COLOR,
    "C":  HIT_ZONE_COLOR,
    "D":  D_GRADE_COLOR,
    "F":  RESULT_MISS_COLOR,
}
