#!/usr/bin/env python3
"""
analyze.py — offline MP3 → chart JSON pipeline

Usage: python analyze.py [song.mp3]
       If no path is given, lists songs/ and prompts for a choice.
Output: <song>.easy.chart.json, <song>.hard.chart.json, <song>.crazy.chart.json
"""
import json
import sys
import os
import numpy as np

_SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ASSETS_DIR = os.path.join(_SCRIPT_DIR, "assets")

# Sentinel meaning "no previous note exists yet"
_BEFORE_SONG = -float("inf")


def _apply_min_gap(items: list, min_gap_s: float, key=lambda x: x["t"]) -> list:
    result = []
    last_t = _BEFORE_SONG
    for item in items:
        if key(item) - last_t >= min_gap_s:
            result.append(item)
            last_t = key(item)
    return result


def _break_lane_streaks(notes: list, max_run: int = 2) -> list:
    """Reassign lanes when same lane repeats more than max_run times consecutively.

    Operates in-place on the notes list (mutates lane assignments directly).
    """
    for i in range(max_run, len(notes)):
        if all(notes[j]["lane"] == notes[i]["lane"] for j in range(i - max_run, i)):
            ranked = notes[i]["_lane_ranks"]
            for alt in ranked:
                if alt != notes[i]["lane"]:
                    notes[i]["lane"] = alt
                    break
    return notes


def _spread_close_notes(notes: list, min_sep_s: float = 0.250) -> list:
    """Reassign notes that are too close in time on the same lane to avoid visual clustering.

    At 1x speed (2s window), notes within min_sep_s on the same lane appear bunched.
    Uses each note's _lane_ranks to find the best-fit alternative lane that won't collide.

    Operates in-place on the notes list (mutates lane assignments directly).
    """
    last_t = [_BEFORE_SONG] * 4
    for n in notes:
        if n["t"] - last_t[n["lane"]] < min_sep_s:
            for alt in n["_lane_ranks"]:
                if alt != n["lane"] and n["t"] - last_t[alt] >= min_sep_s:
                    n["lane"] = alt
                    break
        last_t[n["lane"]] = n["t"]
    return notes


def _simplify_to_inner_lanes(notes: list) -> list:
    """Remap lanes to inner lanes (1 and 2). Uses outer lanes only when both top
    two spectral ranks are outer — i.e., the note is thoroughly extreme in frequency.

    Returns a new list of dicts — does not mutate the input notes.
    """
    result = []
    for n in notes:
        top = n["_lane_ranks"][0]
        second = n["_lane_ranks"][1]
        # Keep outer only when spectral signature strongly prefers it (both top ranks outer)
        if top in (0, 3) and second in (0, 3):
            lane = top
        else:
            # Map to inner: 0→1, 3→2; inner lanes stay as-is
            lane = top if top in (1, 2) else (1 if top == 0 else 2)
        result.append({**n, "lane": lane})
    return result


def _make_difficulty_chart(notes: list, strength_pct: float,
                            min_gap_s: float, simplify_lanes: bool) -> list:
    threshold = np.percentile([n["_strength"] for n in notes], 100 - strength_pct * 100)
    filtered = [n for n in notes if n["_strength"] >= threshold]
    gapped = _apply_min_gap(filtered, min_gap_s)
    if simplify_lanes:
        gapped = _simplify_to_inner_lanes(gapped)
    return [{"t": n["t"], "lane": n["lane"]} for n in gapped]


def _snap_and_dedup(notes: list, grid: np.ndarray) -> list:
    """Snap notes to nearest grid point; keep strongest note per slot."""
    snapped = []
    for n in notes:
        idx = int(np.argmin(np.abs(grid - n["t"])))
        snapped.append({**n, "t": round(float(grid[idx]), 4)})
    by_slot: dict = {}
    for n in snapped:
        key = n["t"]
        if key not in by_slot or n["_strength"] > by_slot[key]["_strength"]:
            by_slot[key] = n
    return sorted(by_slot.values(), key=lambda n: n["t"])


def _quantize_to_grid(notes: list, bpm: float, beat_frames: np.ndarray,
                      sr: int, hop_length: int, min_gap_s: float) -> list:
    """Snap note timings to nearest BPM subdivision. Deduplicates collisions by strength.

    Uses 16th notes for BPM<200, 8th notes otherwise.
    Spectral fields (_lane_ranks, _strength) are preserved from the original onset transient;
    only t is updated to the snapped grid position.
    """
    import librosa as _lib
    beat_times = _lib.frames_to_time(beat_frames, sr=sr, hop_length=hop_length)
    subdiv = 4 if bpm < 200.0 else 2

    # Build grid by interpolating between consecutive beats — handles BPM drift
    grid = []
    for i in range(len(beat_times) - 1):
        interval = beat_times[i + 1] - beat_times[i]
        for s in range(subdiv):
            grid.append(beat_times[i] + s * interval / subdiv)
    grid.append(float(beat_times[-1]))
    grid = np.array(grid)

    return _apply_min_gap(_snap_and_dedup(notes, grid), min_gap_s)


def _compute_preview_start(notes: list) -> float:
    """Return preview start time: 1 s before the densest 1-second note window."""
    if not notes:
        return 0.0
    bins: dict[int, int] = {}
    for n in notes:
        b = int(n["t"])
        bins[b] = bins.get(b, 0) + 1
    peak_bin = max(bins, key=bins.__getitem__)
    return max(0.0, round(peak_bin - 1.0, 2))


def _make_progress():
    from rich.progress import (Progress, SpinnerColumn, BarColumn, TextColumn,
                                TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn)
    return Progress(
        SpinnerColumn("line"),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
    )


def _run_analysis(path: str, progress, t_song) -> None:
    """Core analysis pipeline. Writes chart files. Updates progress tasks."""
    import librosa

    base = os.path.splitext(path)[0]
    name = os.path.splitext(os.path.basename(path))[0]

    progress.update(t_song, description=f"Song: {name} — Loading…")
    t_load = progress.add_task("Loading audio...", total=None)
    y, sr = librosa.load(path, sr=22050)
    progress.update(t_load, description=f"Audio loaded  ({len(y)/sr:.1f}s)", completed=1, total=1)

    progress.update(t_song, description=f"Song: {name} — BPM…")
    t_bpm = progress.add_task("Detecting BPM...", total=None)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(tempo) if not hasattr(tempo, '__len__') else float(tempo[0])
    progress.update(t_bpm, description=f"BPM: {bpm:.1f}", completed=1, total=1)

    progress.update(t_song, description=f"Song: {name} — Onsets…")
    t_onset = progress.add_task("Onset strength...", total=None)
    hop_length = 512  # audio frames per analysis step (~11.6ms at 44.1kHz)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    onset_env_times = librosa.frames_to_time(
        np.arange(len(onset_env)), sr=sr, hop_length=hop_length
    )
    progress.update(t_onset, description="Onset strength done", completed=1, total=1)

    t_detect = progress.add_task("Detecting onsets...", total=None)
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units='frames', hop_length=hop_length, delta=0.05)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=hop_length)
    # Filter: remove onsets too close together (< 100ms)
    MIN_ONSET_DELTA = 0.100
    filtered = _apply_min_gap(list(onset_times), MIN_ONSET_DELTA, key=lambda t: t)
    progress.update(t_detect, description=f"Onsets: {len(filtered)} (filtered from {len(onset_times)})", completed=1, total=1)

    progress.update(t_song, description=f"Song: {name} — STFT…")
    t_stft = progress.add_task("Computing STFT...", total=None)
    S = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)
    progress.update(t_stft, description="STFT done", completed=1, total=1)

    # Define 4 frequency bands for 4 lanes
    # Band edges (Hz): sub-bass | bass | mid | high
    band_edges = [0, 200, 800, 3000, sr // 2]

    # Precompute band bin boundaries (constant — avoids repeat searchsorted in loop)
    band_bins = [
        (int(np.searchsorted(freqs, band_edges[i])),
         int(np.searchsorted(freqs, band_edges[i + 1])))
        for i in range(4)
    ]

    # Squared spectrogram once (avoids squaring inside double loop)
    S_sq = S ** 2

    # Per-band mean energy over ALL frames — normalization reference for lane bias fix
    band_mean_energy = np.array([
        float(np.mean(np.sum(S_sq[lo:hi, :], axis=0)))
        for lo, hi in band_bins
    ])

    # HPSS: reuses existing S — no second STFT
    # h_ratio ≈ 1 → melodic/harmonic; h_ratio ≈ 0 → percussive/beat
    H_spec, P_spec = librosa.decompose.hpss(S)
    H_col = np.sum(H_spec, axis=0)
    P_col = np.sum(P_spec, axis=0)
    harmonic_ratio = H_col / (H_col + P_col + 1e-8)  # (n_frames,) in [0, 1]

    # Spectral centroid per frame: reuses S — no second STFT
    centroid_hz = librosa.feature.spectral_centroid(S=S, sr=sr, hop_length=hop_length)[0]

    # Quartile centroid boundaries over onset frames — ensures even lane distribution
    # regardless of how the song's centroid clusters in absolute frequency
    _onset_centroid_frames = [
        min(int(librosa.time_to_frames(t, sr=sr, hop_length=hop_length)), S.shape[1] - 1)
        for t in filtered
    ]
    _onset_centroids = centroid_hz[_onset_centroid_frames]
    centroid_q25, centroid_q50, centroid_q75 = np.percentile(_onset_centroids, [25, 50, 75])
    centroid_boundaries = np.array([centroid_q25, centroid_q50, centroid_q75])
    # Lane 0 = lowest centroid quartile (dark/bass) … Lane 3 = highest (bright/treble)
    # Rising melody → increasing centroid → notes sweep right (L→R pattern)

    notes = []
    progress.update(t_song, description=f"Song: {name} — Lanes…")
    t_lanes = progress.add_task("Assigning lanes...", total=len(filtered))
    for t in filtered:
        frame = librosa.time_to_frames(t, sr=sr, hop_length=hop_length)
        frame = min(frame, S.shape[1] - 1)

        # Normalized band energies — removes low-frequency dominance
        band_energies = [float(np.sum(S_sq[lo:hi, frame])) for lo, hi in band_bins]
        norm_energies = [e / (band_mean_energy[i] + 1e-8) for i, e in enumerate(band_energies)]

        # Band rank → score (1st=3, 2nd=2, 3rd=1, 4th=0)
        band_rank_order = list(np.argsort(norm_energies)[::-1])
        band_scores = np.zeros(4)
        for rank_pos, lane_idx in enumerate(band_rank_order):
            band_scores[lane_idx] = 3 - rank_pos

        # Centroid-based lane: which quartile bucket does this onset fall in?
        c_hz = float(centroid_hz[frame])
        centroid_lane = int(np.searchsorted(centroid_boundaries, c_hz))  # 0-3
        centroid_scores = np.zeros(4)
        centroid_scores[centroid_lane] = 3.0

        # Composite: percussive notes → band energy; melodic notes → centroid proximity
        h_ratio = float(harmonic_ratio[frame])
        composite = (1.0 - h_ratio) * band_scores + h_ratio * centroid_scores

        lane_ranks = [int(x) for x in np.argsort(composite)[::-1]]
        lane = lane_ranks[0]

        # Sample onset strength at this time
        strength_idx = int(np.argmin(np.abs(onset_env_times - t)))
        strength = float(onset_env[strength_idx])

        notes.append({
            "t": round(float(t), 4),
            "lane": lane,
            "_lane_ranks": lane_ranks,
            "_strength": strength,
        })
        progress.advance(t_lanes)
    progress.update(t_lanes, description=f"Lanes assigned ({len(notes)} notes)")
    progress.update(t_song, description=f"Song: {name} — Writing…")

    # Snap note times to BPM grid; deduplicate collisions by strength
    notes = _quantize_to_grid(notes, bpm, beat_frames, sr, hop_length, MIN_ONSET_DELTA)

    # Break consecutive same-lane streaks
    notes = _break_lane_streaks(notes)
    notes = _spread_close_notes(notes)

    # Build difficulty charts
    import librosa as _lib
    _beat_times = _lib.frames_to_time(beat_frames, sr=sr, hop_length=hop_length)
    _coarse_grid = np.array(list(_beat_times))  # quarter notes — one point per beat
    easy_source = _apply_min_gap(_snap_and_dedup(notes, _coarse_grid), MIN_ONSET_DELTA)

    crazy_notes = [{"t": n["t"], "lane": n["lane"]} for n in notes]
    hard_notes  = _make_difficulty_chart(notes,       strength_pct=0.70, min_gap_s=0.150, simplify_lanes=False)
    easy_notes  = _make_difficulty_chart(easy_source, strength_pct=0.40, min_gap_s=0.250, simplify_lanes=True)

    duration = round(len(y) / sr, 2)

    chart_base = {
        "bpm": round(bpm, 2),
        "duration": duration,
        "preview_start": _compute_preview_start(notes),
        "sr": sr,
        "source": os.path.basename(path),
    }

    # Serialize all charts before writing any — ensures all-or-nothing on disk
    outputs = {
        diff: json.dumps(dict(chart_base, notes=diff_notes), indent=2)
        for diff, diff_notes in [("crazy", crazy_notes), ("hard", hard_notes), ("easy", easy_notes)]
    }
    note_counts = {"crazy": len(crazy_notes), "hard": len(hard_notes), "easy": len(easy_notes)}
    for diff, content in outputs.items():
        out_path = base + f".{diff}.chart.json"
        with open(out_path, "w") as f:
            f.write(content)
        print(f"Written: {out_path}  ({note_counts[diff]} notes)")

    progress.update(t_song, description=f"Song: {name} — Done")


def analyze(path: str) -> None:
    try:
        import librosa
    except ImportError as e:
        print(f"Import error: {e}")
        print("Run: pip install librosa numpy rich")
        sys.exit(1)

    import threading, time

    duration_s = librosa.get_duration(path=path)
    est_s = max(4, int(duration_s * 0.025))

    with _make_progress() as progress:
        t_overall = progress.add_task(f"[bold]Overall  (~{est_s}s est.)", total=100)
        t_song = progress.add_task("", total=None)

        t_start = time.time()
        _stop = threading.Event()
        def _tick():
            while not _stop.wait(0.1):
                elapsed = time.time() - t_start
                progress.update(t_overall, completed=min(95, elapsed / est_s * 100))
        threading.Thread(target=_tick, daemon=True).start()

        try:
            _run_analysis(path, progress, t_song)
        finally:
            _stop.set()
            progress.update(t_overall, completed=100)


def analyze_all(paths: list) -> None:
    try:
        import librosa
    except ImportError as e:
        print(f"Import error: {e}")
        print("Run: pip install librosa numpy rich")
        sys.exit(1)

    import threading, time

    estimates = [max(4, int(librosa.get_duration(path=p) * 0.025)) for p in paths]
    total_est_s = sum(estimates)
    n = len(paths)

    with _make_progress() as progress:
        t_overall = progress.add_task(
            f"[bold]All {n} songs  (~{total_est_s}s est.)", total=100
        )
        t_song = progress.add_task("Starting…", total=None)

        t_start = time.time()
        _stop = threading.Event()
        def _tick():
            while not _stop.wait(0.1):
                elapsed = time.time() - t_start
                progress.update(t_overall, completed=min(95, elapsed / total_est_s * 100))
        threading.Thread(target=_tick, daemon=True).start()

        try:
            for i, path in enumerate(paths):
                name = os.path.splitext(os.path.basename(path))[0]
                progress.update(t_song, description=f"[{i+1}/{n}] {name}", total=None, completed=0)
                _run_analysis(path, progress, t_song)
        finally:
            _stop.set()
            progress.update(t_overall, completed=100)


def pick_song():
    """Interactively list MP3s in songs/ and return the chosen path, or None for all."""
    songs_dir = os.path.join(_ASSETS_DIR, "songs")
    if not os.path.isdir(songs_dir):
        print(f"songs/ directory not found at {songs_dir}")
        sys.exit(1)

    mp3s = sorted(f for f in os.listdir(songs_dir) if f.lower().endswith(".mp3"))
    if not mp3s:
        print("No MP3 files found in songs/")
        sys.exit(1)

    print("\nAvailable songs:")
    print("  0. [Run ALL songs]")
    for i, name in enumerate(mp3s):
        tags = []
        stem = os.path.splitext(name)[0]
        for diff in ("easy", "hard", "crazy"):
            chart = os.path.join(songs_dir, f"{stem}.{diff}.chart.json")
            if os.path.isfile(chart):
                tags.append(diff)
        if not tags:
            old = os.path.join(songs_dir, f"{stem}.chart.json")
            if os.path.isfile(old):
                tags.append("legacy")
        tag = f" [{', '.join(tags)}]" if tags else ""
        print(f"  {i + 1}. {name}{tag}")

    print()
    while True:
        try:
            raw = input(f"Choose (0 = all, 1-{len(mp3s)} = single): ").strip()
            idx = int(raw)
            if idx == 0:
                return None
            if 1 <= idx <= len(mp3s):
                return os.path.join(songs_dir, mp3s[idx - 1])
        except (ValueError, EOFError):
            pass
        print(f"  Please enter 0 for all, or a number between 1 and {len(mp3s)}")


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        analyze(sys.argv[1])
    else:
        choice = pick_song()
        if choice is None:
            songs_dir = os.path.join(_ASSETS_DIR, "songs")
            paths = sorted(
                os.path.join(songs_dir, f)
                for f in os.listdir(songs_dir)
                if f.lower().endswith(".mp3")
            )
            analyze_all(paths)
        else:
            analyze(choice)
