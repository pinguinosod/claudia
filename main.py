#!/usr/bin/env python3
import enum
import json
import math
import os
import random
import sys
import time
import glob as glob_module
import pyfiglet
from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.table import Table
from rich.text import Text
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
import theme
import scoring
import scores as scores_mod
import config as config_mod
import sfx
import layout as layout_mod

try:
    import msvcrt
    _WINDOWS = True
except ImportError:
    import curses
    _WINDOWS = False

try:
    import pygame
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.mixer.init()
    _PYGAME = True
except Exception:
    _PYGAME = False

sfx.init(_PYGAME)

console = Console(force_terminal=True, color_system="truecolor")

TITLE_ART = pyfiglet.figlet_format("CLAUDIA", font="colossal")
TITLE_LINES = TITLE_ART.split("\n")
NOISE_CHARS = "08Oo#@&BQdqpb"
_TITLE_MAX_WIDTH = max(len(l) for l in TITLE_LINES)
_TITLE_NON_EMPTY_COUNT = sum(1 for l in TITLE_LINES if l.strip())

REFRESH_RATE = 60
POLL_INTERVAL = 0.016   # ~60fps poll
ANIMATION_FPS = 60
MENU_SWEEP_INTERVAL = 25.0

# Rhythm game constants — lane keys loaded from config (mutable)
_cfg = config_mod.load()
LANE_KEYS = list(_cfg["lane_keys"])         # lane 0-3; mutated by keybind screen
LANE_CHARS = ["◆", "◆", "◆", "◆"]
MISS_LINGER_MS = 250                        # ms past hit time ghost note remains visible
NOTE_FALL_WINDOW_S = 2.0                    # seconds of notes visible

# Dynamic layout — recalculated each frame via _update_layout()
_layout = layout_mod.calc(*os.get_terminal_size())
HIT_ZONE_ROW = _layout.hit_zone_row
PLAYFIELD_ROWS = _layout.playfield_rows


def _update_layout():
    """Recalculate layout globals from current terminal size."""
    global _layout, HIT_ZONE_ROW, PLAYFIELD_ROWS
    _layout = layout_mod.calc(*os.get_terminal_size())
    HIT_ZONE_ROW = _layout.hit_zone_row
    PLAYFIELD_ROWS = _layout.playfield_rows
PERFECT_MS = 35
GOOD_MS = 85
OK_MS = 135

SPEED_OPTIONS = [2, 4, 6]   # internal multipliers: 2=1x(normal), 4=2x(fast), 6=3x(max)
SPEED_LABELS  = {2: "1x", 4: "2x", 6: "3x"}

# Lane separator / hit zone display
LANE_WIDTH = 11


def _lane_labels() -> list:
    """Return current lane labels derived from LANE_KEYS (reflects rebinds)."""
    return [f"  [{k.upper()}]  " for k in LANE_KEYS]


_MENU_MUSIC_PATH = os.path.join(os.path.dirname(__file__), "assets", "audio", "Digital Welcome Screen.mp3")

_PREVIEW_DURATION_S = 30.0   # seconds of preview to play
_PREVIEW_FADE_S     = 0.5    # fade-in AND fade-out duration
_PREVIEW_GAP_S      = 2.0    # silence between loops


class State(enum.Enum):
    MENU = "menu"
    SONG_SELECT = "song_select"
    PLAYING = "playing"
    PAUSED = "paused"
    COUNTDOWN = "countdown"
    RESULTS = "results"
    KEYBIND = "keybind"


# --- Gradient helpers (unchanged from original) ---

def _hex_to_rgb(color: str):
    c = color.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _lerp_colors(colors: list, t: float) -> str:
    if len(colors) == 1:
        return colors[0]
    scaled = t * (len(colors) - 1)
    lo = int(scaled)
    hi = min(lo + 1, len(colors) - 1)
    frac = scaled - lo
    r1, g1, b1 = _hex_to_rgb(colors[lo])
    r2, g2, b2 = _hex_to_rgb(colors[hi])
    r = round(r1 + (r2 - r1) * frac)
    g = round(g1 + (g2 - g1) * frac)
    b = round(b1 + (b2 - b1) * frac)
    return f"#{r:02x}{g:02x}{b:02x}"


def _brightened_gradient(colors: list, t: float) -> list:
    result = []
    for c in colors:
        r, g, b = _hex_to_rgb(c)
        r = round(r + (255 - r) * t)
        g = round(g + (255 - g) * t)
        b = round(b + (255 - b) * t)
        result.append(f"#{r:02x}{g:02x}{b:02x}")
    return result


def _lerp_color_to_white(color: str, t: float) -> str:
    r, g, b = _hex_to_rgb(color)
    return f"#{round(r+(255-r)*t):02x}{round(g+(255-g)*t):02x}{round(b+(255-b)*t):02x}"


def _lerp_single_color(c1: str, c2: str, t: float) -> str:
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    return f"#{round(r1+(r2-r1)*t):02x}{round(g1+(g2-g1)*t):02x}{round(b1+(b2-b1)*t):02x}"


def _selector_arrow(idle_t: float, sel_age: float = 9999.0) -> tuple:
    """Returns (arrow_char, arrow_color) for the animated menu selector."""
    # Character: one-shot reveal on selection change, stays at ► forever after
    if sel_age < 0.06:
        arrow_char = "· "
    elif sel_age < 0.14:
        arrow_char = "▸ "
    else:
        arrow_char = "► "

    # Glow: free-running 4s loop independent of character
    _tc = idle_t % 2.5
    if _tc < 0.25:
        pulse = math.sin(_tc / 0.25 * math.pi / 2) ** 2     # ease-in (0→1 over 0.25s)
    elif _tc < 2.0:
        pulse = 1.0                                           # hold at peak for 1.75s
    else:
        pulse = 1.0 - math.sin((_tc - 2.0) / 0.5 * math.pi / 2) ** 2  # ease-out (1→0 over 0.5s)
    _sel_hex = theme.SELECTED_COLOR.split()[-1]
    arrow_color = "bold " + _lerp_color_to_white(_sel_hex, pulse * 0.75)
    return arrow_char, arrow_color


def apply_gradient(text: str, colors: list) -> Text:
    lines = text.split("\n")
    non_empty_count = sum(1 for l in lines if l.strip())
    result = Text(justify="center")
    filled = 0
    for i, line in enumerate(lines):
        if line.strip():
            t = filled / max(non_empty_count - 1, 1)
            result.append(line, style=_lerp_colors(colors, t))
            filled += 1
        else:
            result.append(line)
        if i < len(lines) - 1:
            result.append("\n")
    return result


# --- Layout helpers ---

def _make_layout(renderable) -> Layout:
    layout = Layout()
    layout.split_column(Layout(name="content", ratio=1))
    layout["content"].update(renderable)
    return layout


# --- Title animation (unchanged) ---

def _row_gradient_colors() -> list:
    colors = []
    filled = 0
    for line in TITLE_LINES:
        if line.strip():
            t = filled / max(_TITLE_NON_EMPTY_COUNT - 1, 1)
            colors.append(_lerp_colors(theme.GRADIENT_COLORS, t))
            filled += 1
        else:
            colors.append(None)
    return colors


def _scramble_title(t: float) -> Text:
    max_diag = _TITLE_MAX_WIDTH * 0.65 + (len(TITLE_LINES) - 1) * 0.35
    row_colors = _row_gradient_colors()
    result = Text(justify="center")
    for row, line in enumerate(TITLE_LINES):
        grad_color = row_colors[row]
        for col, ch in enumerate(line):
            if ch == ' ':
                result.append(' ')
            else:
                diag_pos = (col * 0.65 + row * 0.35) / max(max_diag, 1)
                if diag_pos <= t:
                    result.append(ch, style=grad_color or "")
                else:
                    result.append(random.choice(NOISE_CHARS), style=theme.VOID_COLOR)
        if row < len(TITLE_LINES) - 1:
            result.append('\n')
    return result


def _sweep_title(sweep_t: float) -> Text:
    max_diag = _TITLE_MAX_WIDTH * 0.65 + (len(TITLE_LINES) - 1) * 0.35
    row_colors = _row_gradient_colors()
    result = Text(justify="center")
    for row, line in enumerate(TITLE_LINES):
        grad_color = row_colors[row]
        for col, ch in enumerate(line):
            if ch == ' ':
                result.append(' ')
            else:
                diag_pos = (col * 0.65 + row * 0.35) / max(max_diag, 1)
                brightness = max(0.0, 0.75 - abs(diag_pos - sweep_t) * 4)
                if brightness > 0 and grad_color:
                    color = _lerp_color_to_white(grad_color, brightness)
                else:
                    color = grad_color or ""
                result.append(ch, style=color)
        if row < len(TITLE_LINES) - 1:
            result.append('\n')
    return result


def _frame_scramble(t: float, items: list) -> Layout:
    content = Text(justify="center")
    content.append_text(_scramble_title(t))
    content.append("\n\n\n")
    for item in items:
        content.append(f"  {item}\n", style=theme.VOID_COLOR)
    content.append("\n\n\n\n\n")
    return _make_layout(Align(content, align="center", vertical="middle"))


def _frame_sweep(sweep_t: float, items: list) -> Layout:
    content = Text(justify="center")
    content.append_text(_sweep_title(sweep_t))
    content.append("\n\n\n")
    for item in items:
        content.append(f"  {item}\n", style=theme.VOID_COLOR)
    content.append("\n\n\n\n\n")
    return _make_layout(Align(content, align="center", vertical="middle"))


def _frame_menu_sweep(selected_index: int, sweep_t: float, items: list,
                      idle_t: float = 0.0, sel_age: float = 9999.0) -> Layout:
    content = Text(justify="center")
    content.append_text(_sweep_title(sweep_t))
    content.append("\n\n\n")
    arrow_char, arrow_color = _selector_arrow(idle_t, sel_age)
    for i, item in enumerate(items):
        if i == selected_index:
            content.append(arrow_char, style=arrow_color)
            content.append(f"{item}\n", style=theme.SELECTED_COLOR)
        else:
            content.append(f"  {item}\n", style=theme.UNSELECTED_COLOR)
    content.append("\n\n\n\n\n")
    content.append("Use Arrow Keys or W/S to navigate, Enter to select", style=theme.HELP_COLOR)
    return _make_layout(Align(content, align="center", vertical="middle"))


def _frame_menu(items_alpha: list, show_help_t: float, items: list) -> Layout:
    content = Text(justify="center")
    content.append_text(apply_gradient(TITLE_ART, theme.GRADIENT_COLORS))
    content.append("\n\n\n")
    for i, item in enumerate(items):
        a = items_alpha[i] if i < len(items_alpha) else 0.0
        ease = math.sin(a * math.pi / 2) ** 2
        color = _lerp_single_color(theme.VOID_COLOR, theme.UNSELECTED_COLOR, ease)
        content.append(f"  {item}\n", style=color)
    content.append("\n\n\n\n\n")
    if show_help_t > 0:
        ease = math.sin(show_help_t * math.pi / 2) ** 2
        help_color = _lerp_single_color(theme.VOID_COLOR, theme.HELP_COLOR, ease)
        content.append("Use Arrow Keys or W/S to navigate, Enter to select", style=help_color)
    return _make_layout(Align(content, align="center", vertical="middle"))


def make_menu_layout(selected_index: int, items: list, idle_t: float = 0.0, sel_age: float = 9999.0) -> Layout:
    content = Text(justify="center")
    content.append_text(apply_gradient(TITLE_ART, theme.GRADIENT_COLORS))
    content.append("\n\n\n")
    arrow_char, arrow_color = _selector_arrow(idle_t, sel_age)
    for i, item in enumerate(items):
        if i == selected_index:
            content.append(arrow_char, style=arrow_color)
            content.append(f"{item}\n", style=theme.SELECTED_COLOR)
        else:
            content.append(f"  {item}\n", style=theme.UNSELECTED_COLOR)
    content.append("\n\n\n\n\n")
    content.append("Use Arrow Keys or W/S to navigate, Enter to select", style=theme.HELP_COLOR)
    return _make_layout(Align(content, align="center", vertical="middle"))


def make_pause_layout(selected: int, idle_t: float, sel_age: float,
                      song_name: str, difficulty: str) -> Layout:
    content = Text(justify="center")
    content.append("\n\n")
    header = "P A U S E D"
    content.append(header + "\n\n", style=f"bold {theme.GRADIENT_COLORS[1]}")
    label = song_name if len(song_name) <= 40 else song_name[:39] + "…"
    content.append(f"{label}  ·  {difficulty.upper()}\n\n\n", style=theme.HELP_COLOR)
    options = ["Resume", "Quit to Song Select"]
    arrow_char, arrow_color = _selector_arrow(idle_t, sel_age)
    for i, opt in enumerate(options):
        if i == selected:
            content.append(arrow_char, style=arrow_color)
            content.append(f"{opt}\n", style=theme.SELECTED_COLOR)
        else:
            content.append(f"  {opt}\n", style=theme.UNSELECTED_COLOR)
    content.append("\n\n")
    content.append("ESC resume   Enter confirm", style=theme.HELP_COLOR)
    return _make_layout(Align(content, align="center", vertical="middle"))


def _make_countdown_panel(count: int, age: float) -> Align:
    """Side panel replacement during countdown — pulsing figlet digit + subtitle."""
    _BAR_WIDTH = 18
    if age < 0.15:
        flash = math.sin(age / 0.15 * math.pi / 2) ** 2
    elif age < 0.75:
        flash = 1.0
    else:
        flash = 1.0 - math.sin((age - 0.75) / 0.25 * math.pi / 2) ** 2 * 0.4
    flash = max(0.0, min(1.0, flash))
    bright_colors = _brightened_gradient(theme.GRADIENT_COLORS, flash * 0.8)
    digit_art = pyfiglet.figlet_format(str(count), font="colossal")
    panel = Text(justify="center")
    panel.append_text(apply_gradient(digit_art, bright_colors))
    panel.append("\n")
    panel.append("Get ready…".center(_BAR_WIDTH), style=theme.HELP_COLOR)
    return Align(panel, align="center", vertical="middle")


def make_keybind_layout(lane_keys: list, selected: int, awaiting: bool,
                        error: str, idle_t: float) -> Layout:
    """Full-screen key rebinding UI."""
    pulse = 0.55 + 0.45 * math.sin(idle_t * math.pi * 2.0)
    bright = _brightened_gradient(theme.GRADIENT_COLORS, pulse * 0.7)
    dim    = _brightened_gradient(theme.GRADIENT_COLORS, 0.1)

    content = Text(justify="center")
    content.append("\n\n")
    content.append("KEY  BINDINGS\n\n\n", style=f"bold {theme.GRADIENT_COLORS[1]}")

    # Build one line with 4 boxes
    TOP  = "┌─────┐"
    MID  = "│  {}  │"
    BOT  = "└─────┘"
    GAP  = "    "

    top_line = Text(justify="center")
    mid_line = Text(justify="center")
    bot_line = Text(justify="center")

    for i, key in enumerate(lane_keys):
        colors = bright if i == selected else dim
        col = _lerp_colors(colors, i / max(len(lane_keys) - 1, 1))
        letter = "?" if (i == selected and awaiting) else key.upper()
        top_line.append(TOP, style=col)
        mid_line.append(MID.format(letter), style=f"bold {col}")
        bot_line.append(BOT, style=col)
        if i < len(lane_keys) - 1:
            top_line.append(GAP)
            mid_line.append(GAP)
            bot_line.append(GAP)

    content.append_text(top_line)
    content.append("\n")
    content.append_text(mid_line)
    content.append("\n")
    content.append_text(bot_line)
    content.append("\n\n")

    # Lane numbers below boxes
    labels_line = Text(justify="center")
    for i in range(len(lane_keys)):
        labels_line.append(f" Lane {i+1} ", style=theme.HELP_COLOR)
        if i < len(lane_keys) - 1:
            labels_line.append("  ")
    content.append_text(labels_line)
    content.append("\n\n")

    if awaiting:
        content.append("Press any key (letter, number, symbol)  ·  ESC cancel\n", style=theme.SELECTED_COLOR)
    else:
        content.append("← → select   Enter rebind   ESC back\n", style=theme.HELP_COLOR)

    if error:
        content.append(f"\n{error}", style=f"bold {theme.RESULT_MISS_COLOR}")

    return _make_layout(Align(content, align="center", vertical="middle"))


def run_intro(live: Live, items: list) -> None:
    frame_time = 1 / ANIMATION_FPS

    def _finish():
        live.update(_frame_menu([1.0] * len(items), 1.0, items))

    for f in range(42):
        live.update(_frame_scramble(f / 41, items))
        time.sleep(frame_time)
        if get_key() is not None:
            _finish(); return

    for f in range(24):
        live.update(_frame_sweep(f / 23, items))
        time.sleep(frame_time)
        if get_key() is not None:
            _finish(); return

    for f in range(24):
        if f < 12:
            alphas = [f / 11] + [0.0] * (len(items) - 1)
        else:
            alphas = [1.0] + [(f - 12) / 11 if i == 1 else (1.0 if i == 0 else 0.0)
                               for i in range(1, len(items))]
        live.update(_frame_menu(alphas, 0.0, items))
        time.sleep(frame_time)
        if get_key() is not None:
            _finish(); return

    time.sleep(0.2)
    for f in range(12):
        live.update(_frame_menu([1.0] * len(items), (f + 1) / 12, items))
        time.sleep(frame_time)
        if get_key() is not None:
            _finish(); return


# --- Song discovery ---

def find_songs() -> list:
    """Return list of dicts with 'name', 'mp3', 'difficulties' for songs that have an MP3."""
    songs_dir = os.path.join(os.path.dirname(__file__), "assets", "songs")
    if not os.path.isdir(songs_dir):
        return []
    mp3_paths = sorted(glob_module.glob(os.path.join(songs_dir, "*.mp3")))
    songs = []
    for mp3_path in mp3_paths:
        base = mp3_path[:-4]  # strip .mp3
        name = os.path.basename(base)
        difficulties = {}
        for diff in ("easy", "hard", "crazy"):
            chart_path = base + f".{diff}.chart.json"
            if os.path.isfile(chart_path):
                difficulties[diff] = chart_path
        # Backwards compat: old .chart.json treated as "crazy"
        if not difficulties:
            old_chart = base + ".chart.json"
            if os.path.isfile(old_chart):
                difficulties["crazy"] = old_chart
        if difficulties:
            # Read BPM + duration from whichever chart is available
            meta_path = (difficulties.get("crazy") or difficulties.get("hard")
                         or difficulties.get("easy"))
            bpm = None
            duration = None
            preview_start = 0.0
            if meta_path:
                try:
                    with open(meta_path) as _f:
                        _meta = json.load(_f)
                    bpm           = _meta.get("bpm")
                    duration      = _meta.get("duration")
                    preview_start = _meta.get("preview_start", 0.0)
                except Exception:
                    pass
            songs.append({
                "name": name, "mp3": mp3_path,
                "difficulties": difficulties,
                "bpm": bpm, "duration": duration,
                "preview_start": preview_start,
            })
    return songs


def load_chart(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


# --- Song select screen ---

_ALL_DIFFS = ["easy", "hard", "crazy"]


def make_song_select_layout(songs: list, selected: int, difficulty: str = "hard", scroll_speed: int = 2, idle_t: float = 0.0, sel_age: float = 9999.0, score_data: dict = None) -> Layout:
    ARROW_W  = 4
    BPM_W    = 6
    DUR_W    = 5
    GRADE_W  = 5
    COL_GAP  = "  "
    VIEWPORT = 7
    HALF_VP  = VIEWPORT // 2

    content = Text(justify="left")
    small = pyfiglet.figlet_format("SELECT SONG", font="small")
    content.append_text(apply_gradient(small, theme.GRADIENT_COLORS))
    content.append("\n\n")

    # Speed selector — all options visible, selected bracketed
    content.append("SPEED:  ", style=theme.UNSELECTED_COLOR)
    for j, opt in enumerate(SPEED_OPTIONS):
        if j > 0:
            content.append("  ")
        label = SPEED_LABELS.get(opt, f"{opt}x")
        if opt == scroll_speed:
            content.append(f"[{label}]", style=theme.SELECTED_COLOR)
        else:
            content.append(label, style=theme.UNSELECTED_COLOR)
    content.append("   TAB", style=theme.HELP_COLOR)
    content.append("\n\n")

    if not songs:
        content.append("No songs found in songs/ directory\n", style=theme.HELP_COLOR)
        content.append("Add .mp3 + .chart.json pairs and restart\n", style=theme.HELP_COLOR)
    else:
        n          = len(songs)
        name_col_w = max(len(s["name"]) for s in songs)

        # Column header + separator
        header = "NAME".ljust(name_col_w) + COL_GAP + "BPM".rjust(BPM_W) + COL_GAP + "TIME".rjust(DUR_W) + COL_GAP + "GRADE".rjust(GRADE_W)
        sep    = "─" * (ARROW_W + name_col_w + len(COL_GAP) + BPM_W + len(COL_GAP) + DUR_W + len(COL_GAP) + GRADE_W)
        content.append(" " * ARROW_W + header + "\n", style=theme.HELP_COLOR)
        content.append(sep + "\n", style=theme.HELP_COLOR)

        # Viewport window centred on selection
        win_start = max(0, min(selected - HALF_VP, n - VIEWPORT))
        win_end   = min(n, win_start + VIEWPORT)
        win_start = max(0, win_end - VIEWPORT)

        # Distance → style
        def _dist_style(dist: int) -> str:
            if dist == 1: return theme.UNSELECTED_COLOR
            if dist == 2: return theme.HELP_COLOR
            return f"dim {theme.HELP_COLOR}"

        # ▲ overflow indicator (always 2 lines to prevent layout shift)
        if win_start > 0:
            content.append(f"  ▲ {win_start} more\n\n", style=theme.HELP_COLOR)
        else:
            content.append("\n\n")

        arrow_char, arrow_color = _selector_arrow(idle_t, sel_age)
        for i in range(win_start, win_end):
            s           = songs[i]
            dist        = abs(i - selected)
            bpm_str     = f"♩{s['bpm']:.0f}".rjust(BPM_W) if s.get("bpm") is not None else " " * BPM_W
            dur_str     = (f"{int(s['duration']) // 60}:{int(s['duration']) % 60:02d}").rjust(DUR_W) \
                          if s.get("duration") is not None else " " * DUR_W
            name_padded = s["name"].ljust(name_col_w)
            # Grade column
            best = scores_mod.get_best(score_data, s["name"], difficulty) if score_data else None
            grade_str = best["best_grade"] if best else "—"
            grade_color = theme.RESULT_GRADE_COLORS.get(grade_str, theme.HELP_COLOR)

            if i == selected:
                meta = COL_GAP + bpm_str + COL_GAP + dur_str + "\n"
                content.append("\n")
                content.append("  " + arrow_char, style=arrow_color)
                content.append(name_padded, style=theme.SELECTED_COLOR)
                content.append(COL_GAP + bpm_str + COL_GAP + dur_str + COL_GAP, style=theme.UNSELECTED_COLOR)
                content.append(grade_str.rjust(GRADE_W) + "\n", style=grade_color)
                # Difficulty rack
                content.append(" " * ARROW_W)
                for j, diff in enumerate(_ALL_DIFFS):
                    if j > 0:
                        content.append("  ")
                    diff_avail = diff in s["difficulties"]
                    if diff == difficulty and diff_avail:
                        content.append(f"[{diff}]", style=f"bold {theme.SELECTED_COLOR}")
                    elif diff_avail:
                        content.append(diff, style=theme.UNSELECTED_COLOR)
                    else:
                        content.append(diff, style=theme.HELP_COLOR)
                content.append("\n\n")
            else:
                row_style = _dist_style(dist)
                meta = COL_GAP + bpm_str + COL_GAP + dur_str + COL_GAP
                content.append(" " * ARROW_W + name_padded + meta, style=row_style)
                content.append(grade_str.rjust(GRADE_W) + "\n", style=grade_color)

        # ▼ overflow indicator (always 2 lines to prevent layout shift)
        remaining = n - win_end
        if remaining > 0:
            content.append(f"\n  ▼ {remaining} more\n", style=theme.HELP_COLOR)
        else:
            content.append("\n\n")

    content.append("\n\n")
    content.append("Enter play  ←/→ difficulty  ESC back", style=theme.HELP_COLOR)
    return _make_layout(Align(content, align="center", vertical="middle"))


# --- Rhythm game state ---

class HitEffect:
    """Short-lived particle effect at a lane position."""
    def __init__(self, lane: int, grade: str, t_start: float):
        self.lane = lane
        self.grade = grade          # "PERFECT", "GOOD", "OK", "MISS"
        self.t_start = t_start
        self.duration = 0.35        # seconds


class GameState:
    def __init__(self, chart: dict, mp3_path: str):
        self.notes = [dict(n) for n in chart["notes"]]   # {t, lane, hit}
        for n in self.notes:
            n["t_ms"] = int(n["t"] * 1000)
            n["hit"] = False
            n["missed"] = False
        self.mp3_path = mp3_path
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.perfect = 0
        self.good = 0
        self.ok = 0
        self.miss = 0
        self.hit_effects: list[HitEffect] = []
        self.lane_flash: list[float] = [0.0] * 4   # keypress flash timer (seconds remaining)
        self.hit_ripple: list[float] = [9999.0] * 4  # seconds since last PERFECT per lane
        self.hit_consume: list[float] = [9999.0] * 4 # seconds since last consumed note per lane
        self.miss_flash: list[float] = [0.0] * 4   # seconds remaining for MISS pulse
        self.total_notes = len(self.notes)
        self.duration_s: float = chart.get("duration", 0.0)
        self.finished = False
        self.song_ended_at: float = 0.0
        # Pre-roll: delay music so the earliest note always enters from row 0
        window_ms = int(NOTE_FALL_WINDOW_S * 1000)
        if self.notes:
            first_note_ms = min(n["t_ms"] for n in self.notes)
            self._delay_ms = max(0, window_ms - first_note_ms)
        else:
            self._delay_ms = 0
        self._music_started = False
        self._paused_at: float = 0.0

    def get_current_ms(self) -> int:
        return int((time.time() - self._start_time) * 1000) - self._delay_ms

    def start(self, live_start_time: float):
        self._start_time = live_start_time
        self._music_started = False
        if self._delay_ms == 0:
            self._start_music()

    def _start_music(self):
        self._music_started = True
        if _PYGAME:
            try:
                pygame.mixer.music.load(self.mp3_path)
                pygame.mixer.music.play()
            except Exception:
                pass

    def tick_preroll(self):
        """Call each frame during PLAYING; starts music when pre-roll expires."""
        if not self._music_started:
            elapsed_ms = int((time.time() - self._start_time) * 1000)
            if elapsed_ms >= self._delay_ms:
                self._start_music()

    def pause(self):
        self._paused_at = time.time()
        if _PYGAME:
            try:
                pygame.mixer.music.pause()
            except Exception:
                pass

    def resume(self):
        if self._paused_at > 0:
            self._start_time += time.time() - self._paused_at
            self._paused_at = 0.0
        if _PYGAME:
            try:
                pygame.mixer.music.unpause()
            except Exception:
                pass

    def stop(self):
        if _PYGAME:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def register_keypress(self, lane: int, current_ms: int) -> str:
        """Returns grade string or None if no note hit."""
        self.lane_flash[lane] = 0.15   # flash for 150ms

        # Find closest unhit note in this lane
        best = None
        best_delta = 9999
        for n in self.notes:
            if n["hit"] or n["missed"] or n["lane"] != lane:
                continue
            delta = abs(n["t_ms"] - current_ms)
            if delta < best_delta:
                best_delta = delta
                best = n

        if best is None or best_delta >= OK_MS:
            return None

        best["hit"] = True
        self.hit_consume[lane] = 0.0
        if best_delta < PERFECT_MS:
            grade = "PERFECT"
            weight = scoring.SCORE_WEIGHT_PERFECT
            self.perfect += 1
        elif best_delta < GOOD_MS:
            grade = "GOOD"
            weight = scoring.SCORE_WEIGHT_GOOD
            self.good += 1
        else:
            grade = "OK"
            weight = scoring.SCORE_WEIGHT_OK
            self.ok += 1

        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        notes_hit_so_far = self.perfect + self.good + self.ok
        self.score = scoring.note_score(
            self.score, weight, self.total_notes, notes_hit_so_far, self.miss, self.perfect
        )

        if grade == "PERFECT":
            self.hit_ripple[lane] = 0.0   # start ripple timer at 0 (counts up)

        now = time.time()
        self.hit_effects.append(HitEffect(lane, grade, now))
        return grade

    def check_misses(self, current_ms: int):
        for n in self.notes:
            if n["hit"] or n["missed"]:
                continue
            if current_ms > n["t_ms"] + OK_MS:
                n["missed"] = True
                self.miss_flash[n["lane"]] = 0.35
                self.miss += 1
                self.combo = 0
                now = time.time()
                self.hit_effects.append(HitEffect(n["lane"], "MISS", now))

    def is_song_complete(self, current_ms: int) -> bool:
        all_done = all(n["hit"] or n["missed"] for n in self.notes)
        if all_done and not self.finished:
            self.finished = True
            self.song_ended_at = time.time()
            if _PYGAME:
                try:
                    pygame.mixer.music.fadeout(2000)
                except Exception:
                    pass
        return self.finished and (time.time() - self.song_ended_at > 2.0)

    def accuracy_pct(self) -> float:
        return scoring.accuracy_pct(self.perfect, self.good, self.ok, self.total_notes)

    def grade_letter(self) -> str:
        return scoring.grade_letter(self.perfect, self.good, self.ok, self.miss, self.total_notes)

    def prune_effects(self):
        now = time.time()
        self.hit_effects = [e for e in self.hit_effects
                            if now - e.t_start < e.duration]


# --- Playfield renderer ---


NOTE_CHAR = "◆"
LANE_SEP = "│"


def _note_color_at_row(row: int, lane: int) -> str:
    """Notes fade from pink (far) to purple (near hit zone), brightening as they approach."""
    proximity = row / max(PLAYFIELD_ROWS - 1, 1)   # 0=top far, 1=bottom near
    ease = 1 - math.cos(proximity * math.pi / 2)
    return _lerp_single_color(theme.GRADIENT_COLORS[0], theme.GRADIENT_COLORS[2], ease)


# Dynamic — recalculated from layout each frame access
def _ripple_duration():
    return _layout.ripple_duration

SIGMA_CORE  = 0.55   # tight Gaussian core — tuned for 15-row approach zone
RING_DECAY  = 2.5    # how quickly the outer ring fades with distance
RING_PERIOD = 1.5    # spacing between rings (rows)
RING_AMP    = 0.35   # amplitude of outer ring relative to core


def _compute_voltages(gs: GameState, current_ms: int, scroll_speed: int = 2):
    effective_window_ms = int(4000 / scroll_speed)
    ghost_window_ms     = int(NOTE_FALL_WINDOW_S * 1000)  # fixed — ghost zone always 2x
    voltages      = [[0.0] * 4 for _ in range(PLAYFIELD_ROWS)]
    miss_voltages = [[0.0] * 4 for _ in range(PLAYFIELD_ROWS)]

    for n in gs.notes:
        ahead_ms = n["t_ms"] - current_ms

        if not n["hit"] and not n["missed"] and -OK_MS < ahead_ms <= effective_window_ms:
            row_f = HIT_ZONE_ROW * (1.0 - ahead_ms / effective_window_ms)
            for r in range(PLAYFIELD_ROWS):          # all rows — formula places peak correctly
                dist = abs(r - row_f)
                core = math.exp(-(dist ** 2) / (2 * SIGMA_CORE ** 2))
                ring = (math.exp(-dist / RING_DECAY)
                        * max(0.0, math.cos(dist * math.pi / RING_PERIOD))
                        * RING_AMP)
                voltages[r][n["lane"]] += core + ring

        elif n["missed"] and -MISS_LINGER_MS < ahead_ms < 0:
            row_f = HIT_ZONE_ROW * (1.0 - ahead_ms / ghost_window_ms)  # > HIT_ZONE_ROW
            for r in range(HIT_ZONE_ROW, PLAYFIELD_ROWS):         # ghost rows only
                dist = abs(r - row_f)
                core = math.exp(-(dist ** 2) / (2 * SIGMA_CORE ** 2))
                ring = (math.exp(-dist / RING_DECAY)
                        * max(0.0, math.cos(dist * math.pi / RING_PERIOD))
                        * RING_AMP)
                miss_voltages[r][n["lane"]] += core + ring

    for r in range(PLAYFIELD_ROWS):
        for l in range(4):
            voltages[r][l]      = min(1.0, voltages[r][l])
            miss_voltages[r][l] = min(1.0, miss_voltages[r][l])

    return voltages, miss_voltages


def _voltage_char(v: float) -> str:
    if v < 0.08: return "·"
    if v < 0.25: return "░"
    if v < 0.55: return "▒"
    if v < 0.80: return "▓"
    return "█"


def _voltage_color(v: float, lane: int, row: int, gs: GameState, idle_t: float) -> str:
    breath = math.sin(idle_t * math.pi * 0.4) ** 2 * 0.03
    base_v = max(v, breath)

    depth  = min(1.0, row / HIT_ZONE_ROW)
    target = _lerp_colors(theme.DEPTH_COLORS, depth)
    color  = _lerp_single_color(theme.NOTE_DARK, target, base_v)

    ripple_age = gs.hit_ripple[lane]
    if ripple_age < _ripple_duration():
        t = ripple_age / _ripple_duration()
        pos_t = 0.5 * t + 0.5 * (1.0 - math.cos(t * math.pi / 2))
        ripple_row = HIT_ZONE_ROW * (1.0 - pos_t)
        ripple_dist = abs(row - ripple_row)
        if ripple_dist < 2.0:
            fade = 0.5 * (1.0 - t) + 0.5 * math.cos(t * math.pi / 2)
            burst = math.exp(-(ripple_dist ** 2) / 0.8) * fade
            color = _lerp_color_to_white(color, burst * 0.9)

    miss_t = gs.miss_flash[lane]
    if miss_t > 0:
        fade = miss_t / 0.35
        ease = math.sin(fade * math.pi / 2) ** 2
        color = _lerp_single_color(color, theme.MISS_FLASH_COLOR, ease * 0.85)

    return color


def _miss_voltage_color(v: float, lane: int) -> str:
    """Crimson burn-out color for notes in the ghost zone."""
    if v < 0.05:
        return theme.NOTE_DARK
    fade = min(1.0, v * 1.4)
    return _lerp_single_color(theme.MISS_FLASH_DARK, theme.MISS_FLASH_COLOR, fade)


def _side_col(r: int, gs: GameState, now: float, idle_t: float,
              base_char: str, base_color: str, lanes: list) -> tuple:
    """Animated left/right rail char+color for approach row r.
    lanes: which lanes feed this rail — [0,1] for left, [2,3] for right."""
    ch = base_char
    color = base_color

    # Idle breath — very subtle glow oscillating slowly
    breath = math.sin(idle_t * math.pi * 0.25) ** 2 * 0.05
    color = _lerp_color_to_white(color, breath)

    # PERFECT: upward ripple — only lanes belonging to this side
    max_burst = 0.0
    for lane in lanes:
        age = gs.hit_ripple[lane]
        if age < _ripple_duration():
            t = age / _ripple_duration()
            pos_t = 0.5 * t + 0.5 * (1.0 - math.cos(t * math.pi / 2))
            ripple_r = HIT_ZONE_ROW * (1.0 - pos_t)
            dist = abs(r - ripple_r)
            fade = 0.5 * (1.0 - t) + 0.5 * math.cos(t * math.pi / 2)
            burst = math.exp(-(dist ** 2) / 1.5) * fade
            max_burst = max(max_burst, burst)

    if max_burst > 0.03:
        if base_char == LANE_SEP and max_burst > 0.65:
            ch = "┃"          # bold rail char at ripple peak
        color = _lerp_color_to_white(color, max_burst * 0.92)

    # GOOD / OK: brief grade-colored bloom near separator — only this side's lanes
    for eff in gs.hit_effects:
        if eff.grade in ("GOOD", "OK") and eff.lane in lanes:
            age = now - eff.t_start
            if age < 0.22:
                dist = abs(r - (HIT_ZONE_ROW - 2))
                tint = math.exp(-(dist ** 2) / 5.0) * math.sin((1.0 - age / 0.22) * math.pi)
                color = _lerp_single_color(color, theme.GRADE_COLORS[eff.grade], tint * 0.45)

    return ch, color


_GRADE_PRIORITY = {"PERFECT": 3, "GOOD": 2, "OK": 1, "MISS": 0}


def _make_side_panel(gs: GameState, now: float, idle_t: float,
                     difficulty: str = "", scroll_speed: int = 2,
                     song_name: str = "", current_ms: int = 0) -> Align:
    """Build the right-side HUD panel: diff/speed, song name, progress, grade, score, combo."""
    panel = Text(justify="left")
    _BAR_WIDTH = 18

    # --- Difficulty + speed ---
    speed_label = SPEED_LABELS.get(scroll_speed, f"{scroll_speed}")
    diff_speed = f"{difficulty.upper()}  {speed_label}"
    panel.append(diff_speed.center(_BAR_WIDTH) + "\n", style=theme.HELP_COLOR)

    # --- Song name ---
    label = song_name if len(song_name) <= _BAR_WIDTH else song_name[:_BAR_WIDTH - 1] + "…"
    panel.append(label.center(_BAR_WIDTH) + "\n", style=theme.HELP_COLOR)

    # --- Progress bar ---
    duration_ms = gs.duration_s * 1000
    progress = max(0.0, min(1.0, current_ms / duration_ms)) if duration_ms > 0 else 0.0
    filled = round(progress * _BAR_WIDTH)
    bar_str = "█" * filled + "░" * (_BAR_WIDTH - filled)
    for i, ch in enumerate(bar_str):
        pos = i / max(_BAR_WIDTH - 1, 1)
        color = _lerp_colors(theme.GRADIENT_COLORS, pos)
        panel.append(ch, style=color)
    panel.append("\n\n")

    # --- Grade popup: best active grade across all lanes ---
    best_eff = None
    best_prio = -1
    for eff in gs.hit_effects:
        p = _GRADE_PRIORITY.get(eff.grade, -1)
        if p > best_prio:
            best_prio = p
            best_eff = eff

    if best_eff is not None:
        age = now - best_eff.t_start
        fade = max(0.0, 1.0 - age / best_eff.duration)
        ease_fade = math.sin(fade * math.pi / 2) ** 2
        grade_color_base = theme.GRADE_COLORS.get(best_eff.grade, theme.HELP_COLOR)
        color = _lerp_single_color(theme.VOID_COLOR, grade_color_base, ease_fade)
        panel.append(best_eff.grade.center(_BAR_WIDTH), style=f"bold {color}")
    else:
        panel.append(" " * _BAR_WIDTH)  # placeholder — column width held by progress bar
    panel.append("\n\n")

    # --- Combo ---
    combo_pulse = 0.5 + 0.5 * math.sin(idle_t * 2.0 * math.pi / 3.0)
    combo_color = _lerp_single_color(theme.GRADIENT_COLORS[1],
                                     _lerp_color_to_white(theme.GRADIENT_COLORS[1], 0.6),
                                     combo_pulse)
    panel.append("COMBO".center(_BAR_WIDTH) + "\n", style=theme.HELP_COLOR)
    combo_str = f"×{gs.combo}"
    panel.append(" " * ((_BAR_WIDTH - len(combo_str)) // 2))
    panel.append(combo_str + "\n", style=f"bold {combo_color}")

    # Stars — live accuracy tier
    notes_judged = gs.perfect + gs.good + gs.ok + gs.miss
    if notes_judged == 0:
        star_filled = 0
    else:
        acc = gs.accuracy_pct()
        star_filled = (1 if acc >= 20 else 0) + (1 if acc >= 40 else 0) \
                    + (1 if acc >= 60 else 0) + (1 if acc >= 80 else 0) \
                    + (1 if acc >= 95 else 0)
    stars_str = "★" * star_filled + "☆" * (5 - star_filled)
    star_color = _lerp_colors(theme.GRADIENT_COLORS, star_filled / 5.0)
    panel.append(stars_str.center(_BAR_WIDTH), style=star_color)

    return Align(panel, align="center", vertical="middle")


def make_playfield(gs: GameState, current_ms: int, idle_t: float, scroll_speed: int = 2, difficulty: str = "", song_name: str = "", countdown=None) -> Layout:
    """Build the complete rhythm game layout."""
    gs.prune_effects()
    now = time.time()

    # Active hit effects per lane
    lane_effects = {e.lane: e for e in gs.hit_effects}

    content = Text(justify="center")

    # --- Mini title with idle sweep ---
    small_title = " C L A U D I A "
    sweep_pos = (idle_t % 3.0) / 3.0
    title_line = Text(justify="center")
    for i, ch in enumerate(small_title):
        pos = i / max(len(small_title) - 1, 1)
        brightness = max(0.0, 0.6 - abs(pos - sweep_pos) * 3)
        base_color = _lerp_colors(theme.GRADIENT_COLORS, pos)
        if brightness > 0:
            color = _lerp_color_to_white(base_color, brightness)
        else:
            color = base_color
        title_line.append(ch, style=color)
    content.append_text(title_line)
    content.append("\n")

    # --- Separator ---
    sep_color = theme.GRADIENT_COLORS[1]
    content.append("─" * (LANE_WIDTH * 4 + 5) + "\n", style=sep_color)

    # --- Note rows (voltage field) ---
    voltages, miss_voltages = _compute_voltages(gs, current_ms, scroll_speed)

    # --- Approach rows (0 .. HIT_ZONE_ROW-1) ---
    for r in range(HIT_ZONE_ROW):
        seps = [
            _side_col(r, gs, now, idle_t, LANE_SEP, sep_color, [0]),       # outer-left  — lane 0
            _side_col(r, gs, now, idle_t, LANE_SEP, sep_color, [0, 1]),    # sep 0|1
            _side_col(r, gs, now, idle_t, LANE_SEP, sep_color, [1, 2]),    # sep 1|2
            _side_col(r, gs, now, idle_t, LANE_SEP, sep_color, [2, 3]),    # sep 2|3
            _side_col(r, gs, now, idle_t, LANE_SEP, sep_color, [3]),       # outer-right — lane 3
        ]

        content.append(seps[0][0], style=seps[0][1])
        for lane in range(4):
            v = voltages[r][lane]
            ch = _voltage_char(v)
            color = _voltage_color(v, lane, r, gs, idle_t)
            cell = (ch * LANE_WIDTH).center(LANE_WIDTH)
            content.append(cell, style=color)
            sep_ch, sep_col = seps[lane + 1]
            content.append(sep_ch, style=sep_col)
        content.append("\n")

    # --- Separator (PERFECT / hit line) ---
    sep_dim = _lerp_single_color("#000000", theme.PERFECT_COLOR, 0.25)
    _GRADE_FLASH = {"PERFECT": 1.0, "GOOD": 0.6, "OK": 0.3}
    content.append("◄", style=sep_dim)
    for lane in range(4):
        best = None
        for eff in gs.hit_effects:
            if eff.lane == lane and (best is None or eff.t_start > best.t_start):
                best = eff
        if best is not None:
            age = now - best.t_start
            t = max(0.0, 1.0 - age / best.duration)
            ease = math.sin(t * math.pi / 2) ** 2
            intensity = ease * _GRADE_FLASH.get(best.grade, 0.0)
            lane_sep_color = _lerp_color_to_white(sep_dim, intensity)
        else:
            lane_sep_color = sep_dim
        content.append("─" * LANE_WIDTH, style=lane_sep_color)
        if lane < 3:
            content.append("─", style=sep_dim)
    content.append("►\n", style=sep_dim)

    # --- Ghost rows (HIT_ZONE_ROW .. PLAYFIELD_ROWS-1) ---
    for r in range(HIT_ZONE_ROW, PLAYFIELD_ROWS):
        ghost_left_col = sep_color
        ghost_right_col = sep_color
        for eff in gs.hit_effects:
            if eff.grade == "MISS":
                age = now - eff.t_start
                if age < 0.3:
                    tint = math.sin((1.0 - age / 0.3) * math.pi) * 0.55
                    if eff.lane in (0, 1):
                        ghost_left_col  = _lerp_single_color(ghost_left_col,  theme.MISS_FLASH_COLOR, tint)
                    else:
                        ghost_right_col = _lerp_single_color(ghost_right_col, theme.MISS_FLASH_COLOR, tint)

        content.append(LANE_SEP, style=ghost_left_col)   # LEFT
        for lane in range(4):
            lv = voltages[r][lane]        # still-hittable late note
            mv = miss_voltages[r][lane]   # missed note

            # Consumed burst: brief flash at first ghost row when a note was just hit
            consume_burst = 0.0
            if r == HIT_ZONE_ROW:
                age = gs.hit_consume[lane]
                if age < 0.18:
                    consume_burst = math.sin((1.0 - age / 0.18) * math.pi)

            if mv > 0.05:
                ch = _voltage_char(mv)
                color = _miss_voltage_color(mv, lane)
            elif consume_burst > lv:
                ch = _voltage_char(consume_burst)
                color = _lerp_color_to_white(theme.LANE_COLORS[lane], consume_burst * 0.85)
            elif lv > 0.05:
                ch = _voltage_char(lv)
                color = _voltage_color(lv, lane, r, gs, idle_t)
            else:
                ch = _voltage_char(0.0)
                color = theme.NOTE_DARK

            cell = (ch * LANE_WIDTH).center(LANE_WIDTH)
            content.append(cell, style=color)
            if lane < 3:
                content.append(LANE_SEP, style=sep_color)      # inner sep — unchanged
            else:
                content.append(LANE_SEP, style=ghost_right_col) # RIGHT
        content.append("\n")

    # --- Hit zone with key labels and flash ---
    content.append(LANE_SEP, style=sep_color)
    for lane in range(4):
        flash_t = gs.lane_flash[lane]
        eff = lane_effects.get(lane)

        if flash_t > 0:
            # Bright flash fading out
            flash_progress = flash_t / 0.15
            ease = math.sin(flash_progress * math.pi)
            base = theme.LANE_COLORS[lane]
            color = _lerp_color_to_white(base, ease * 0.8)
        elif eff and eff.grade == "PERFECT":
            age = now - eff.t_start
            burst = 1.0 - age / eff.duration
            color = _lerp_color_to_white(theme.PERFECT_COLOR, burst * 0.9)
        else:
            color = theme.HIT_ZONE_COLOR

        label = _lane_labels()[lane]
        content.append(label.center(LANE_WIDTH), style=f"bold {color}")
        content.append(LANE_SEP, style=sep_color)

    content.append("\n")

    if countdown is not None:
        side = _make_countdown_panel(*countdown)
    else:
        side = _make_side_panel(gs, now, idle_t, difficulty, scroll_speed, song_name, current_ms)
    grid = Table.grid(padding=(0, 2))
    grid.add_column(no_wrap=True)
    grid.add_column(no_wrap=True)
    grid.add_row(content, side)
    return _make_layout(Align(grid, align="center", vertical="middle"))


# --- Results screen ---

_RT_BREAKDOWN = 0.25
_RT_SCORE     = 0.50
_RT_SCORE_END = 1.45   # count-up duration = 0.95 s
_RT_STATS     = 1.15
_RT_GRADE     = 1.60
_RT_GRADE_END = 2.50   # scramble duration = 0.90 s
_RT_BADGE     = 2.80
_RT_ESC       = 3.2
_RT_IDLE      = 3.2


def _results_scramble_resolve(rows: list, t: float) -> Text:
    """Scramble chars resolve into results text. rows = list of (text, color) tuples."""
    result = Text(justify="left")
    row_count = len(rows)
    for row, (line, color) in enumerate(rows):
        for col, ch in enumerate(line):
            if ch == ' ':
                result.append(' ')
            else:
                diag_pos = (col * 0.6 + row * 0.4) / max(len(line) * 0.6 + row_count * 0.4, 1)
                if diag_pos <= t:
                    result.append(ch, style=color)
                else:
                    result.append(random.choice(NOISE_CHARS), style=theme.VOID_COLOR)
        if row < row_count - 1:
            result.append('\n')
    return result


def make_results_layout(gs: GameState, result_t: float,
                        song_name: str = "", difficulty: str = "",
                        scroll_speed: int = 2) -> Layout:
    grade = gs.grade_letter()
    accuracy_str = f"{gs.accuracy_pct():.2f}%"
    grade_base = theme.RESULT_GRADE_COLORS.get(grade, theme.GRADIENT_COLORS[0])
    grade_art_lines = pyfiglet.figlet_format(grade, font="colossal").rstrip("\n").split("\n")
    while grade_art_lines and not grade_art_lines[-1].strip():
        grade_art_lines.pop()
    block_width = max(len(l) for l in grade_art_lines) if grade_art_lines else 20
    speed_label = SPEED_LABELS.get(scroll_speed, f"{scroll_speed}")
    displayed_score = scoring.final_score(gs.score, gs.max_combo, gs.total_notes)
    col_w     = block_width // 2
    _bd_left1 = f"PERFECT {gs.perfect:>4}".ljust(col_w)
    _bd_left2 = f"OK      {gs.ok:>4}".ljust(col_w)
    bd_row1   = _bd_left1 + f"   GOOD {gs.good:>4}"
    bd_row2   = _bd_left2 + f"   MISS {gs.miss:>4}"
    left_w    = len(_bd_left1)
    score_str   = f"{displayed_score:,}"
    combo_str   = f"\u00d7{gs.max_combo}"
    stats_w     = max(len("SCORE      " + score_str),
                      len("ACCURACY   " + accuracy_str),
                      len("COMBO      " + combo_str))
    badge = scoring.clear_badge(gs.perfect, gs.good, gs.ok, gs.miss, gs.total_notes)
    badge_color = theme.PERFECT_BADGE_COLOR if badge == "PERFECT" else theme.FC_BADGE_COLOR

    # Derived timing values
    idle_t_internal = max(0.0, result_t - _RT_IDLE)

    _raw_gs = max(0.0, min(1.0, (result_t - _RT_GRADE) / (_RT_GRADE_END - _RT_GRADE)))
    grade_scramble_t = math.sin(_raw_gs * math.pi / 2) ** 2

    _raw_st = max(0.0, min(1.0, (result_t - _RT_SCORE) / (_RT_SCORE_END - _RT_SCORE)))
    count_ease = 1.0 - (1.0 - _raw_st) ** 3
    score_display = int(displayed_score * count_ease)
    score_display_str = f"{score_display:,}".rjust(len(score_str))

    stats_pad = " " * max(0, (block_width - stats_w) // 2)

    content = Text(justify="left")
    content.append("\n")

    # ── Song context (always visible) ───────────────────────────────────────
    content.append(
        f"{song_name[:block_width]}  ·  {difficulty.upper()}  {speed_label}".center(block_width) + "\n\n\n\n\n",
        style=theme.HELP_COLOR,
    )

    # ── Grade art area ───────────────────────────────────────────────────────
    if result_t < _RT_GRADE:
        content.append("\n" * len(grade_art_lines))
    elif grade_scramble_t < 1.0:
        grade_rows = [(line, grade_base) for line in grade_art_lines]
        content.append_text(_results_scramble_resolve(grade_rows, grade_scramble_t))
        content.append("\n")
    else:
        pulse = 0.5 + 0.5 * math.sin(idle_t_internal * 2 * math.pi / 3)
        grade_color = _lerp_single_color(grade_base, _lerp_color_to_white(grade_base, 0.5), pulse)
        for line in grade_art_lines:
            content.append(line + "\n", style=f"bold {grade_color}")

    # ── Badge area ───────────────────────────────────────────────────────────
    if badge:
        if result_t >= _RT_BADGE:
            content.append("\n")
            content.append(badge.center(block_width) + "\n", style=f"bold {badge_color}")
        else:
            content.append("\n\n")

    content.append("\n\n\n")

    # ── Stats area ───────────────────────────────────────────────────────────
    if result_t >= _RT_SCORE:
        content.append(stats_pad)
        content.append("SCORE      ", style=theme.HELP_COLOR)
        for i, ch in enumerate(score_display_str):
            pos = i / max(len(score_display_str) - 1, 1)
            content.append(ch, style=f"bold {_lerp_colors(theme.GRADIENT_COLORS, pos)}")
        content.append("\n")
    else:
        content.append("\n")

    if result_t >= _RT_STATS:
        content.append(stats_pad)
        content.append("ACCURACY   ", style=theme.HELP_COLOR)
        for i, ch in enumerate(accuracy_str):
            pos = i / max(len(accuracy_str) - 1, 1)
            content.append(ch, style=f"bold {_lerp_colors(theme.GRADIENT_COLORS, pos)}")
        content.append("\n")
        content.append(stats_pad)
        content.append("COMBO      ", style=theme.HELP_COLOR)
        content.append(combo_str + "\n\n", style=theme.GRADIENT_COLORS[1])
    else:
        content.append("\n\n\n")

    # ── Breakdown area ───────────────────────────────────────────────────────
    if result_t >= _RT_BREAKDOWN:
        content.append("\n")
        bd1_c = bd_row1.center(block_width)
        bd2_c = bd_row2.center(block_width)
        lead  = len(bd1_c) - len(bd1_c.lstrip())
        content.append(bd1_c[:lead + left_w],        style=theme.PERFECT_COLOR)
        content.append(bd1_c[lead + left_w:] + "\n", style=theme.GOOD_COLOR)
        content.append(bd2_c[:lead + left_w],        style=theme.OK_COLOR)
        content.append(bd2_c[lead + left_w:] + "\n", style=theme.RESULT_MISS_COLOR)
    else:
        content.append("\n" * 3)

    # ── ESC prompt ───────────────────────────────────────────────────────────
    if result_t >= _RT_ESC:
        content.append("\n\n")
        content.append("ESC back to song select".center(block_width), style=theme.HELP_COLOR)

    return _make_layout(Align(content, align="center", vertical="top"))


def _start_menu_music():
    if not _PYGAME or not os.path.isfile(_MENU_MUSIC_PATH):
        return
    try:
        pygame.mixer.music.load(_MENU_MUSIC_PATH)
        pygame.mixer.music.play()
    except Exception:
        pass


class SongPreview:
    """Debounced song preview: seeks to stored interesting point, fades in/out, loops."""

    DELAY_S = 0.4

    def __init__(self):
        self._current: str | None = None
        self._current_start_s: float = 0.0
        self._pending: str | None = None
        self._pending_start_s: float = 0.0
        self._play_at: float = 0.0
        self._play_started_at: float = 0.0
        self._restart_at: float = 0.0    # 0 = not scheduled

    def select(self, mp3_path: str, start_s: float = 0.0) -> None:
        """Queue a preview. No-op if this exact track is already mid-play."""
        if (mp3_path == self._current
                and self._restart_at == 0.0
                and _PYGAME
                and pygame.mixer.music.get_busy()):
            return
        self._pending = mp3_path
        self._pending_start_s = start_s
        self._play_at = time.time() + self.DELAY_S
        self._restart_at = 0.0

    def tick(self) -> None:
        """Call once per frame while in SONG_SELECT."""
        now = time.time()

        if self._pending and now >= self._play_at:
            self._do_start(self._pending, self._pending_start_s)
            self._pending = None
            return

        if self._play_started_at > 0.0 and self._restart_at == 0.0:
            elapsed = now - self._play_started_at
            if elapsed >= _PREVIEW_DURATION_S - _PREVIEW_FADE_S:
                if _PYGAME:
                    try:
                        pygame.mixer.music.fadeout(int(_PREVIEW_FADE_S * 1000))
                    except Exception:
                        pass
                self._restart_at = now + _PREVIEW_FADE_S + _PREVIEW_GAP_S
            elif _PYGAME and not pygame.mixer.music.get_busy():
                self._restart_at = now + _PREVIEW_GAP_S   # ended early

        if self._restart_at > 0.0 and now >= self._restart_at:
            self._restart_at = 0.0
            self._do_start(self._current, self._current_start_s)

    def stop(self) -> None:
        """Immediately stop and clear all state."""
        self._current = None
        self._current_start_s = 0.0
        self._pending = None
        self._pending_start_s = 0.0
        self._play_at = 0.0
        self._play_started_at = 0.0
        self._restart_at = 0.0
        if _PYGAME:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def _do_start(self, mp3_path: str, start_s: float) -> None:
        if not _PYGAME or not mp3_path:
            return
        try:
            pygame.mixer.music.load(mp3_path)
            pygame.mixer.music.play(0, start=start_s, fade_ms=int(_PREVIEW_FADE_S * 1000))
            self._current = mp3_path
            self._current_start_s = start_s
            self._play_started_at = time.time()
            self._restart_at = 0.0
        except Exception:
            pass


# --- Input ---

def _get_key_windows():
    if not msvcrt.kbhit():
        return None
    key = msvcrt.getch()
    if key == b'\xe0':
        key = msvcrt.getch()
        if key == b'H':
            return "up"
        elif key == b'P':
            return "down"
        elif key == b'K':
            return "left"
        elif key == b'M':
            return "right"
        return None
    elif key == b'\r':
        return "enter"
    elif key == b'\x1b':
        return "esc"
    ch = key.decode('utf-8', errors='ignore').lower()
    if ch == '\t':
        return 'tab'
    if ch in ('w',):
        return "w"
    if ch in ('s',):
        return "s"
    if ch in ('a',):
        return "left"
    if ch in LANE_KEYS:
        return ch
    return None


def _get_key_unix():
    try:
        ch = _curses_win.getch()
        if ch == curses.KEY_UP:
            return "up"
        elif ch == curses.KEY_DOWN:
            return "down"
        elif ch == curses.KEY_LEFT:
            return "left"
        elif ch == curses.KEY_RIGHT:
            return "right"
        elif ch in (curses.KEY_ENTER, 10, 13):
            return "enter"
        elif ch == 27:
            return "esc"
        elif ch == 9:
            return "tab"
        elif ch != -1:
            c = chr(ch).lower()
            if c == 'w':
                return 'w'
            if c == 's':
                return 's'
            if c == 'a':
                return 'left'
            if c in LANE_KEYS:
                return c
    except Exception:
        pass
    return None


def get_key():
    if _WINDOWS:
        return _get_key_windows()
    return _get_key_unix()


def _get_raw_key_windows():
    """Like _get_key_windows but returns any printable ASCII character."""
    if not msvcrt.kbhit():
        return None
    key = msvcrt.getch()
    if key in (b'\xe0', b'\x00'):   # arrow / function key prefix — consume second byte
        msvcrt.getch()
        return None
    if key == b'\r':
        return "enter"
    if key == b'\x1b':
        return "esc"
    ch = key.decode('utf-8', errors='ignore')
    if ch == '\t':
        return "tab"
    if ch.isprintable() and not ch.isspace():
        return ch.lower()
    return None


def _get_raw_key_unix():
    """Like _get_key_unix but returns any printable ASCII character."""
    try:
        ch = _curses_win.getch()
        if ch == curses.KEY_UP:              return "up"
        if ch == curses.KEY_DOWN:            return "down"
        if ch == curses.KEY_LEFT:            return "left"
        if ch == curses.KEY_RIGHT:           return "right"
        if ch in (curses.KEY_ENTER, 10, 13): return "enter"
        if ch == 27:                         return "esc"
        if ch == 9:                          return "tab"
        if 33 <= ch <= 126:                  # printable non-space ASCII
            return chr(ch).lower()
    except Exception:
        pass
    return None


def get_raw_key():
    """Returns any printable ASCII char or a navigation sentinel (esc/enter/tab/arrows).
    Used by the keybind screen to capture arbitrary keypresses."""
    if _WINDOWS:
        return _get_raw_key_windows()
    return _get_raw_key_unix()


def _flush_input():
    """Drain all pending OS keyboard events."""
    while get_key() is not None:
        pass


# --- Song select helpers ---

def _available_difficulties(songs: list) -> list:
    """Return difficulty names that have at least one song with a chart."""
    result = []
    for diff in ("easy", "hard", "crazy"):
        if any(diff in s["difficulties"] for s in songs):
            result.append(diff)
    return result


def _next_available_song(songs: list, current_idx: int, difficulty: str, direction: int) -> int:
    """Return next index (wrapping) that has a chart for difficulty, or current if none."""
    n = len(songs)
    for step in range(1, n + 1):
        idx = (current_idx + direction * step) % n
        if difficulty in songs[idx]["difficulties"]:
            return idx
    return current_idx


# --- Game loop ---

def run_game():
    MAIN_ITEMS = ["Play", "Key Bindings", "Exit"]
    selected_index = 0
    state = State.MENU
    songs: list = []
    song_selected = 0
    difficulty = "easy"
    scroll_speed = 2
    gs: GameState = None
    idle_t = 0.0
    sel_age = 0.0
    result_start_time = 0.0
    _sfx_beep_played  = False
    _sfx_grade_played = False
    _sfx_badge_played = False
    last_frame_time = time.time()
    last_sweep = time.time()
    _menu_music_restart_at: float = 0.0
    _pause_sel      = 0
    _pause_idle_t   = 0.0
    _pause_sel_age  = 0.0
    _paused_ms      = 0
    _countdown_start     = 0.0
    _last_countdown_beep = -1
    _keybind_sel      = 0
    _keybind_awaiting = False
    _keybind_error    = ""
    _preview = SongPreview()
    _scores = scores_mod.load()

    try:
        with Live(console=console, screen=True,
                  auto_refresh=True, refresh_per_second=30, transient=True) as live:
            run_intro(live, MAIN_ITEMS)
            _flush_input()
            live.update(make_menu_layout(selected_index, MAIN_ITEMS))
            _start_menu_music()

            while True:
                now = time.time()
                dt = now - last_frame_time
                last_frame_time = now

                # --- Terminal size check ---
                _term_cols, _term_rows = os.get_terminal_size()
                if not layout_mod.is_terminal_valid(_term_cols, _term_rows):
                    if state == State.PLAYING:
                        _paused_ms = gs.current_ms(now)
                        state = State.PAUSED
                    _warn = Text("Terminal too small!", style="bold red")
                    _warn.append(f"\nMinimum: {layout_mod.MIN_COLS}×{layout_mod.MIN_ROWS}")
                    _warn.append(f"\nCurrent: {_term_cols}×{_term_rows}")
                    live.update(Align.center(_warn, vertical="middle"))
                    time.sleep(POLL_INTERVAL)
                    continue
                _update_layout()

                # --- MENU ---
                if state == State.MENU:
                    idle_t += dt
                    sel_age += dt
                    if _PYGAME and not pygame.mixer.music.get_busy():
                        if _menu_music_restart_at == 0.0:
                            _menu_music_restart_at = time.time() + 2.0
                        elif time.time() >= _menu_music_restart_at:
                            _start_menu_music()
                            _menu_music_restart_at = 0.0
                    if now - last_sweep >= MENU_SWEEP_INTERVAL:
                        last_sweep = now
                        for f in range(24):
                            live.update(_frame_menu_sweep(selected_index, f / 23, MAIN_ITEMS, idle_t, sel_age))
                            time.sleep(1 / ANIMATION_FPS)

                    key = get_key()
                    if key in ("up", "w"):
                        selected_index = (selected_index - 1) % len(MAIN_ITEMS)
                        sfx.play("nav")
                        idle_t = 0.0
                        sel_age = 0.0
                    elif key in ("down", "s"):
                        selected_index = (selected_index + 1) % len(MAIN_ITEMS)
                        sfx.play("nav")
                        idle_t = 0.0
                        sel_age = 0.0
                    elif key == "enter":
                        if MAIN_ITEMS[selected_index] == "Play":
                            sfx.play("select")
                            if _PYGAME:
                                pygame.mixer.music.stop()
                            _menu_music_restart_at = 0.0
                            songs = find_songs()
                            song_selected = 0
                            # Snap to first available song for current difficulty
                            if songs and difficulty not in songs[0]["difficulties"]:
                                song_selected = _next_available_song(songs, 0, difficulty, 1)
                            state = State.SONG_SELECT
                            _preview.select(songs[song_selected]["mp3"], songs[song_selected].get("preview_start", 0.0))
                            idle_t = 0.0
                            sel_age = 0.0
                            live.update(make_song_select_layout(songs, song_selected, difficulty, scroll_speed, idle_t, sel_age, _scores))
                            continue
                        elif MAIN_ITEMS[selected_index] == "Key Bindings":
                            sfx.play("select")
                            _keybind_sel      = 0
                            _keybind_awaiting = False
                            _keybind_error    = ""
                            state = State.KEYBIND
                            idle_t = 0.0
                            continue
                        elif MAIN_ITEMS[selected_index] == "Exit":
                            if _PYGAME:
                                pygame.mixer.music.stop()
                            break
                    live.update(make_menu_layout(selected_index, MAIN_ITEMS, idle_t, sel_age))
                    time.sleep(POLL_INTERVAL)

                # --- KEY BINDINGS ---
                elif state == State.KEYBIND:
                    idle_t += dt
                    if _keybind_awaiting:
                        key = get_raw_key()          # broad capture: any printable char
                        if key == "esc":
                            _keybind_awaiting = False
                        elif key is not None and key not in ("enter", "tab"):
                            if key in LANE_KEYS and LANE_KEYS.index(key) != _keybind_sel:
                                _keybind_error = f"'{key.upper()}' is already bound to Lane {LANE_KEYS.index(key) + 1}!"
                            else:
                                LANE_KEYS[_keybind_sel] = key
                                _cfg["lane_keys"] = list(LANE_KEYS)
                                config_mod.save(_cfg)
                                _keybind_error = ""
                                sfx.play("approval")
                            _keybind_awaiting = False
                    else:
                        key = get_key()              # normal navigation
                        if key in ("left", "a"):
                            _keybind_sel = (_keybind_sel - 1) % 4
                            sfx.play("nav")
                        elif key in ("right", "d"):
                            _keybind_sel = (_keybind_sel + 1) % 4
                            sfx.play("nav")
                        elif key == "enter":
                            _keybind_awaiting = True
                            sfx.play("select")
                        elif key == "esc":
                            state = State.MENU
                            idle_t = 0.0
                            sel_age = 0.0
                            continue
                    live.update(make_keybind_layout(LANE_KEYS, _keybind_sel,
                                                    _keybind_awaiting, _keybind_error, idle_t))
                    time.sleep(POLL_INTERVAL)

                # --- SONG SELECT ---
                elif state == State.SONG_SELECT:
                    idle_t += dt
                    sel_age += dt
                    _preview.tick()
                    key = get_key()
                    if key in ("up", "w") and songs:
                        song_selected = _next_available_song(songs, song_selected, difficulty, -1)
                        _preview.select(songs[song_selected]["mp3"], songs[song_selected].get("preview_start", 0.0))
                        sfx.play("nav")
                        idle_t = 0.0
                        sel_age = 0.0
                    elif key in ("down", "s") and songs:
                        song_selected = _next_available_song(songs, song_selected, difficulty, 1)
                        _preview.select(songs[song_selected]["mp3"], songs[song_selected].get("preview_start", 0.0))
                        sfx.play("nav")
                        idle_t = 0.0
                        sel_age = 0.0
                    elif key in ("left", "right", "d") and songs:
                        avail_diffs = _available_difficulties(songs)
                        if avail_diffs:
                            cur = avail_diffs.index(difficulty) if difficulty in avail_diffs else 0
                            step = 1 if key in ("right", "d") else -1
                            difficulty = avail_diffs[(cur + step) % len(avail_diffs)]
                            if difficulty not in songs[song_selected]["difficulties"]:
                                song_selected = _next_available_song(songs, song_selected, difficulty, 1)
                        _preview.select(songs[song_selected]["mp3"], songs[song_selected].get("preview_start", 0.0))
                        sfx.play("settings")
                        sel_age = 0.0
                    elif key == "tab":
                        idx = SPEED_OPTIONS.index(scroll_speed) if scroll_speed in SPEED_OPTIONS else 0
                        scroll_speed = SPEED_OPTIONS[(idx + 1) % len(SPEED_OPTIONS)]
                        sfx.play("settings")
                        idle_t = 0.0
                    elif key == "enter" and songs:
                        sfx.play("select")
                        play_diff = difficulty
                        if play_diff not in songs[song_selected]["difficulties"]:
                            play_diff = min(
                                songs[song_selected]["difficulties"].keys(),
                                key=lambda d: abs(_ALL_DIFFS.index(d) - _ALL_DIFFS.index(difficulty))
                                              if d in _ALL_DIFFS else 999
                            )
                        chart_path = songs[song_selected]["difficulties"].get(play_diff)
                        if chart_path:
                            _preview.stop()
                            chart = load_chart(chart_path)
                            gs = GameState(chart, songs[song_selected]["mp3"])
                            state = State.PLAYING
                            idle_t = 0.0
                            gs.start(time.time())
                            live.update(make_playfield(gs, 0, idle_t, scroll_speed, difficulty, songs[song_selected]["name"]))
                            continue
                    elif key == "esc":
                        _preview.stop()
                        state = State.MENU
                        _start_menu_music()
                        _menu_music_restart_at = 0.0
                        idle_t = 0.0
                        sel_age = 0.0
                        live.update(make_menu_layout(selected_index, MAIN_ITEMS, idle_t, sel_age))
                        continue
                    live.update(make_song_select_layout(songs, song_selected, difficulty, scroll_speed, idle_t, sel_age, _scores))
                    time.sleep(POLL_INTERVAL)

                # --- PLAYING ---
                elif state == State.PLAYING:
                    idle_t += dt
                    gs.tick_preroll()
                    current_ms = gs.get_current_ms()

                    # Tick flash timers
                    for i in range(4):
                        gs.lane_flash[i] = max(0.0, gs.lane_flash[i] - dt)
                        gs.miss_flash[i]  = max(0.0, gs.miss_flash[i]  - dt)
                        gs.hit_ripple[i]  += dt
                        gs.hit_consume[i] += dt

                    # Check misses
                    gs.check_misses(current_ms)

                    # Check song complete
                    if gs.is_song_complete(current_ms):
                        gs.stop()
                        state = State.RESULTS
                        _song_name = songs[song_selected]["name"]
                        result_start_time = time.time()
                        _sfx_beep_played  = False
                        _sfx_grade_played = False
                        _sfx_badge_played = False
                        continue

                    # Input
                    key = get_key()
                    if key == "esc":
                        _paused_ms = gs.get_current_ms()
                        gs.pause()
                        state = State.PAUSED
                        _pause_sel = 0
                        _pause_idle_t = 0.0
                        _pause_sel_age = 0.0
                        sfx.play("nav")
                        continue

                    if key in LANE_KEYS:
                        lane = LANE_KEYS.index(key)
                        gs.register_keypress(lane, current_ms)

                    frame_start = time.time()
                    live.update(make_playfield(gs, current_ms, idle_t, scroll_speed, difficulty, songs[song_selected]["name"]))
                    elapsed = time.time() - frame_start
                    time.sleep(max(0.0, POLL_INTERVAL - elapsed))

                # --- PAUSED ---
                elif state == State.PAUSED:
                    _pause_idle_t += dt
                    _pause_sel_age += dt
                    key = get_key()
                    if key in ("up", "w"):
                        _pause_sel = (_pause_sel - 1) % 2
                        sfx.play("nav")
                        _pause_sel_age = 0.0
                    elif key in ("down", "s"):
                        _pause_sel = (_pause_sel + 1) % 2
                        sfx.play("nav")
                        _pause_sel_age = 0.0
                    elif key == "esc" or (key == "enter" and _pause_sel == 0):
                        sfx.play("select")
                        _countdown_start = time.time()
                        _last_countdown_beep = -1
                        state = State.COUNTDOWN
                        continue
                    elif key == "enter" and _pause_sel == 1:
                        sfx.play("rejection")
                        gs.stop()
                        state = State.SONG_SELECT
                        _preview.select(songs[song_selected]["mp3"],
                                        songs[song_selected].get("preview_start", 0.0))
                        idle_t = 0.0
                        sel_age = 0.0
                        live.update(make_song_select_layout(songs, song_selected, difficulty, scroll_speed, idle_t, sel_age, _scores))
                        continue
                    live.update(make_pause_layout(_pause_sel, _pause_idle_t, _pause_sel_age,
                                                  songs[song_selected]["name"], difficulty))
                    time.sleep(POLL_INTERVAL)

                # --- COUNTDOWN ---
                elif state == State.COUNTDOWN:
                    idle_t += dt
                    _flush_input()                        # drain OS buffer every frame
                    elapsed  = time.time() - _countdown_start
                    beat_s   = 60.0 / songs[song_selected]["bpm"]
                    count    = 3 - int(elapsed / beat_s)
                    beep_idx = int(elapsed / beat_s)
                    if beep_idx != _last_countdown_beep:
                        sfx.play("countdown")
                        _last_countdown_beep = beep_idx
                    if count <= 0:
                        gs.resume()
                        _flush_input()                    # eat anything pressed in final frame
                        state = State.PLAYING
                        idle_t = 0.0
                        continue
                    age = (elapsed % beat_s) / beat_s     # 0–1 within current beat
                    live.update(make_playfield(gs, _paused_ms, idle_t, scroll_speed,
                                              difficulty, songs[song_selected]["name"],
                                              countdown=(count, age)))
                    time.sleep(POLL_INTERVAL)

                # --- RESULTS ---
                elif state == State.RESULTS:
                    result_t = time.time() - result_start_time
                    if not _sfx_beep_played and result_t >= _RT_SCORE:
                        sfx.play("beep")
                        _sfx_beep_played = True
                    if not _sfx_grade_played and result_t >= _RT_GRADE:
                        sfx.play(sfx.GRADE_SFX.get(gs.grade_letter(), "approval"))
                        _sfx_grade_played = True
                    if not _sfx_badge_played and result_t >= _RT_BADGE:
                        if scoring.clear_badge(gs.perfect, gs.good, gs.ok, gs.miss, gs.total_notes):
                            sfx.play("badge")
                        _sfx_badge_played = True
                    key = get_key()
                    if key == "esc" and result_t >= _RT_ESC:
                        final = scoring.final_score(gs.score, gs.max_combo, gs.total_notes)
                        scores_mod.update_best(_scores, songs[song_selected]["name"], difficulty, gs, final)
                        scores_mod.save(_scores)
                        state = State.SONG_SELECT
                        _preview.select(songs[song_selected]["mp3"], songs[song_selected].get("preview_start", 0.0))
                        idle_t = 0.0
                        sel_age = 0.0
                        live.update(make_song_select_layout(songs, song_selected, difficulty, scroll_speed, idle_t, sel_age, _scores))
                        continue
                    live.update(make_results_layout(gs, result_t,
                                songs[song_selected]["name"], difficulty, scroll_speed))
                    time.sleep(POLL_INTERVAL)

    except Exception as e:
        import traceback
        print(f"\nError: {e}")
        traceback.print_exc()
        input("Press Enter to exit...")


def main():
    if not _WINDOWS:
        global _curses_win
        _curses_win = curses.initscr()
        curses.noecho()
        curses.cbreak()
        _curses_win.keypad(True)
        _curses_win.nodelay(True)
        try:
            run_game()
        finally:
            curses.nocbreak()
            _curses_win.keypad(False)
            curses.echo()
            curses.endwin()
    else:
        import ctypes
        _winmm = ctypes.windll.winmm
        _winmm.timeBeginPeriod(1)
        try:
            os.system('cls')
            run_game()
        finally:
            _winmm.timeEndPeriod(1)


if __name__ == "__main__":
    main()
