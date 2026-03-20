"""Sound effects — thin wrapper around pygame.mixer.Sound."""
import os

_sounds: dict = {}
_enabled = False
_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio")

_FILES = {
    "nav":       "beep_high_short.mp3",
    "settings":  "beep_nice.mp3",
    "select":    "beep_ascending_high_reverb.mp3",
    "beep":      "beep_counting.mp3",
    "victory01": "beep_victory01.mp3",
    "victory02": "beep_victory02.mp3",
    "victory03": "beep_victory03.mp3",
    "approval":  "beep_approval.mp3",
    "rejection": "beep_rejection.mp3",
    "badge":     "beep_fifths_hit.mp3",
    "countdown": "beep_mid_short.mp3",
}

GRADE_SFX = {
    "S+": "victory01",
    "S":  "victory02",
    "A":  "victory03",
    "B":  "approval",
    "C":  "approval",
    "D":  "approval",
    "F":  "rejection",
}


def init(pygame_available: bool) -> None:
    """Pre-load all SFX. Call once after pygame.mixer.init()."""
    global _enabled
    _enabled = pygame_available
    if not _enabled:
        return
    import pygame
    for name, filename in _FILES.items():
        path = os.path.join(_AUDIO_DIR, filename)
        if os.path.isfile(path):
            try:
                _sounds[name] = pygame.mixer.Sound(path)
            except Exception:
                pass


def play(name: str) -> None:
    """Play a named SFX. Silently no-ops if unavailable."""
    sound = _sounds.get(name)
    if sound:
        try:
            sound.play()
        except Exception:
            pass
