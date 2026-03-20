"""Score persistence — best results per song × difficulty."""

import json
import os
import tempfile
from datetime import datetime

SCORES_PATH = os.path.join(os.path.dirname(__file__), "scores.json")

_EMPTY = {
    "version": 1,
    "songs": {},
    "totals": {
        "play_count": 0,
        "first_play_at": None,
        "last_play_at": None,
    },
}


def load() -> dict:
    """Return full scores dict, creating file if missing."""
    if not os.path.isfile(SCORES_PATH):
        return dict(_EMPTY)
    try:
        with open(SCORES_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return dict(_EMPTY)


def save(data: dict) -> None:
    """Write atomically via temp file + rename."""
    dir_ = os.path.dirname(SCORES_PATH)
    try:
        fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, SCORES_PATH)
    except Exception:
        pass


def get_best(data: dict, song_name: str, difficulty: str) -> dict | None:
    """Return stored best entry or None."""
    return data.get("songs", {}).get(song_name, {}).get(difficulty)


def update_best(data: dict, song_name: str, difficulty: str, gs, final_score: int) -> bool:
    """Compare new result to stored best; overwrite only if higher score.

    gs must have: grade_letter(), accuracy_pct(), max_combo, perfect, good,
    ok, miss, total_notes attributes.

    Returns True if this is a new best.
    """
    import scoring as _scoring
    grade   = gs.grade_letter()
    acc     = gs.accuracy_pct()
    combo   = gs.max_combo
    badge   = _scoring.clear_badge(gs.perfect, gs.good, gs.ok, gs.miss, gs.total_notes)
    now_str = datetime.now().replace(microsecond=0).isoformat()

    songs = data.setdefault("songs", {})
    song  = songs.setdefault(song_name, {})
    prev  = song.get(difficulty)

    is_new_best = prev is None or final_score > prev.get("best_score", -1)

    if is_new_best:
        song[difficulty] = {
            "best_score":    final_score,
            "best_grade":    grade,
            "best_accuracy": round(acc, 2),
            "best_combo":    combo,
            "clear_badge":   badge,
            "play_count":    (prev["play_count"] + 1) if prev else 1,
            "best_at":       now_str,
        }
    else:
        song[difficulty]["play_count"] = prev.get("play_count", 0) + 1

    totals = data.setdefault("totals", {})
    totals["play_count"] = totals.get("play_count", 0) + 1
    totals["last_play_at"] = now_str
    if not totals.get("first_play_at"):
        totals["first_play_at"] = now_str

    return is_new_best
