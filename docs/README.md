# Claudia

A rhythm game that runs entirely in your terminal. Notes fall, you hit them. Built with Python.

> Early development — expect rough edges.

---

## Bring your own music

Claudia works with any MP3 you own. Drop it in the `assets/songs/` folder and run the analyzer to generate a chart:

```bash
uv run python src/analyze.py "assets/songs/your song.mp3"
```

The game will pick it up automatically next time you launch.

A few tracks are bundled to get you started (see [CREDITS](CREDITS.md)).

---

## Install

```bash
git clone https://github.com/pinguinosod/claudia
cd claudia
uv sync
uv run main.py
```

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

---

## Controls

| Key | Action |
|-----|--------|
| D F J K | Hit lanes (rebindable in-game) |
| ESC | Pause |
| W / S | Navigate menus |
| Enter | Confirm |

Lane keys can be rebound from the main menu → **Key Bindings**.

---

## Dependencies

- [Rich](https://github.com/Textualize/rich) — terminal rendering
- [pygame](https://www.pygame.org/) — audio playback
- [librosa](https://librosa.org/) — beat detection & chart generation
- [pyfiglet](https://github.com/pwaller/pyfiglet) — ASCII art

---

## License

MIT — see [LICENSE](LICENSE).

Music and audio assets have separate licenses — see [CREDITS](CREDITS.md).
