"""Pure scoring functions — no game state, no imports from main."""

# Accuracy weights — used for accuracy_pct() and grade_letter() (unchanged)
NOTE_WEIGHT_PERFECT = 1.00
NOTE_WEIGHT_GOOD    = 0.70
NOTE_WEIGHT_OK      = 0.30

# Score weights — more aggressive; used by note_score() only
SCORE_WEIGHT_PERFECT = 1.00
SCORE_WEIGHT_GOOD    = 0.50
SCORE_WEIGHT_OK      = 0.10

ACCURACY_SCORE_MAX = 900_000
COMBO_BONUS_MAX    = 100_000


def accuracy_pct(perfect: int, good: int, ok: int, total_notes: int) -> float:
    """Weighted accuracy: PERFECT=100%, GOOD=70%, OK=30%, MISS=0%."""
    if total_notes == 0:
        return 100.0
    weighted = perfect * 1.0 + good * 0.7 + ok * 0.3
    return weighted / total_notes * 100.0


def grade_letter(perfect: int, good: int, ok: int, miss: int, total_notes: int) -> str:
    if total_notes == 0:
        return "S+"
    acc = accuracy_pct(perfect, good, ok, total_notes)
    if miss == 0 and ok == 0 and good == 0:
        return "S+"   # all-PERFECT
    if acc >= 95.0 and miss == 0:
        return "S"
    if acc >= 90.0:
        return "A"
    if acc >= 80.0:
        return "B"
    if acc >= 70.0:
        return "C"
    if acc >= 50.0:
        return "D"
    return "F"


def clear_badge(perfect: int, good: int, ok: int, miss: int, total_notes: int) -> str:
    """Returns a clear status badge string, or '' if any notes were missed."""
    if total_notes == 0:
        return ""
    if miss > 0:
        return ""
    if good == 0 and ok == 0:
        return "PERFECT"
    return "FULL COMBO"


def note_score(current_score: int, weight: float, total_notes: int,
               notes_hit_so_far: int, miss_count: int, perfect_count: int) -> int:
    """Accuracy component only (0–900K). Combo bonus revealed on results screen."""
    if notes_hit_so_far == total_notes and miss_count == 0 and perfect_count == total_notes:
        return ACCURACY_SCORE_MAX  # all-PERFECT: absorb rounding remainder
    note_value = ACCURACY_SCORE_MAX / max(1, total_notes)
    return min(ACCURACY_SCORE_MAX, round(current_score + note_value * weight))


def combo_bonus(max_combo: int, total_notes: int) -> int:
    """Combo consistency bonus (0–100K). Added to accuracy score at end of song."""
    if total_notes == 0:
        return 0
    return round(min(max_combo, total_notes) / total_notes * COMBO_BONUS_MAX)


def final_score(accuracy_score: int, max_combo: int, total_notes: int) -> int:
    """Total score shown on results screen (0–1,000,000)."""
    return min(1_000_000, accuracy_score + combo_bonus(max_combo, total_notes))
