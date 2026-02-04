#!/usr/bin/env python3
"""Génère un pack audio 8-bit pour AstroPaws.

Sorties (WAV mono 22.05 kHz) dans le dossier `sounds/` :
- sfx_shoot.wav
- sfx_explosion.wav
- sfx_pickup.wav
- sfx_dash.wav
- sfx_warp.wav
- music_menu_loop.wav
- music_gameplay_loop.wav
"""

from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path

SR = 22050
RNG = random.Random(42)


def make_buffer(duration_s: float) -> list[float]:
    return [0.0] * max(1, int(duration_s * SR))


def clamp(x: float) -> float:
    return max(-1.0, min(1.0, x))


def env(i: int, total: int, attack: float = 0.05, release: float = 0.2) -> float:
    a = max(1, int(total * attack))
    r = max(1, int(total * release))
    if i < a:
        return i / a
    if i > total - r:
        return max(0.0, (total - i) / r)
    return 1.0


def wf(kind: str, phase: float) -> float:
    if kind == "square":
        return 1.0 if math.sin(2.0 * math.pi * phase) >= 0 else -1.0
    if kind == "triangle":
        return 2.0 * abs(2.0 * (phase - math.floor(phase + 0.5))) - 1.0
    if kind == "saw":
        return 2.0 * (phase - math.floor(phase + 0.5))
    if kind == "noise":
        return RNG.uniform(-1.0, 1.0)
    return math.sin(2.0 * math.pi * phase)


def add_tone(
    buf: list[float],
    start_s: float,
    dur_s: float,
    freq_hz: float,
    volume: float = 0.3,
    kind: str = "square",
    slide_to_hz: float | None = None,
    attack: float = 0.03,
    release: float = 0.25,
) -> None:
    start = int(start_s * SR)
    count = max(1, int(dur_s * SR))
    phase = 0.0
    for i in range(count):
        idx = start + i
        if idx >= len(buf):
            break
        t = i / max(1, count - 1)
        freq = freq_hz if slide_to_hz is None else freq_hz + (slide_to_hz - freq_hz) * t
        phase += freq / SR
        buf[idx] += wf(kind, phase) * volume * env(i, count, attack=attack, release=release)


def add_noise_burst(
    buf: list[float],
    start_s: float,
    dur_s: float,
    volume: float = 0.4,
    attack: float = 0.01,
    release: float = 0.9,
) -> None:
    start = int(start_s * SR)
    count = max(1, int(dur_s * SR))
    for i in range(count):
        idx = start + i
        if idx >= len(buf):
            break
        buf[idx] += wf("noise", 0.0) * volume * env(i, count, attack=attack, release=release)


def normalize(buf: list[float], headroom: float = 0.95) -> list[float]:
    peak = max(0.001, max(abs(x) for x in buf))
    gain = min(1.0, headroom / peak)
    return [clamp(x * gain) for x in buf]


def write_wav(path: Path, buf: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = bytearray()
    for sample in normalize(buf):
        pcm.extend(struct.pack("<h", int(sample * 32767)))
    with wave.open(str(path), "wb") as wavf:
        wavf.setnchannels(1)
        wavf.setsampwidth(2)
        wavf.setframerate(SR)
        wavf.writeframes(bytes(pcm))


def note_freq(semitones_from_a4: int) -> float:
    return 440.0 * (2.0 ** (semitones_from_a4 / 12.0))


def build_sfx_shoot() -> list[float]:
    b = make_buffer(0.10)
    add_tone(b, 0.0, 0.10, 1600, volume=0.28, kind="square", slide_to_hz=800, attack=0.02, release=0.55)
    return b


def build_sfx_explosion() -> list[float]:
    b = make_buffer(0.45)
    add_noise_burst(b, 0.0, 0.35, volume=0.55)
    add_tone(b, 0.0, 0.30, 130, volume=0.35, kind="triangle", slide_to_hz=55, attack=0.01, release=0.85)
    return b


def build_sfx_pickup() -> list[float]:
    b = make_buffer(0.22)
    add_tone(b, 0.00, 0.07, 880, volume=0.24, kind="square")
    add_tone(b, 0.06, 0.07, 1108, volume=0.24, kind="square")
    add_tone(b, 0.12, 0.08, 1318, volume=0.24, kind="square")
    return b


def build_sfx_dash() -> list[float]:
    b = make_buffer(0.22)
    add_tone(b, 0.0, 0.20, 340, volume=0.35, kind="saw", slide_to_hz=120, attack=0.01, release=0.8)
    add_noise_burst(b, 0.02, 0.15, volume=0.13, attack=0.0, release=0.8)
    return b


def build_sfx_warp() -> list[float]:
    b = make_buffer(0.70)
    add_tone(b, 0.0, 0.62, 220, volume=0.22, kind="square", slide_to_hz=1320, attack=0.03, release=0.3)
    add_tone(b, 0.56, 0.12, 1760, volume=0.20, kind="triangle")
    return b


def add_bass_pattern(buf: list[float], bpm: int, bars: int, root_steps: list[int], vol: float = 0.13) -> None:
    beat = 60.0 / bpm
    for bar in range(bars):
        root = root_steps[bar % len(root_steps)]
        base_time = bar * 4 * beat
        for beat_idx in range(4):
            t = base_time + beat_idx * beat
            add_tone(buf, t, beat * 0.7, note_freq(root - 24), volume=vol, kind="triangle", release=0.5)


def add_arp_pattern(
    buf: list[float], bpm: int, bars: int, chord_roots: list[int], chord_type: str = "minor", vol: float = 0.10
) -> None:
    beat = 60.0 / bpm
    step = beat / 2
    quality = [0, 3, 7, 10] if chord_type == "minor" else [0, 4, 7, 11]
    for bar in range(bars):
        root = chord_roots[bar % len(chord_roots)]
        base_time = bar * 4 * beat
        for i in range(8):
            t = base_time + i * step
            n = root + quality[i % len(quality)]
            add_tone(buf, t, step * 0.9, note_freq(n), volume=vol, kind="square", release=0.35)


def build_music_menu() -> list[float]:
    bpm = 112
    bars = 8
    duration = bars * 4 * (60.0 / bpm)
    b = make_buffer(duration)
    roots = [-5, -8, -10, -3]  # Dm Bb Gm C (autour de A4)
    add_bass_pattern(b, bpm=bpm, bars=bars, root_steps=roots, vol=0.14)
    add_arp_pattern(b, bpm=bpm, bars=bars, chord_roots=[r + 12 for r in roots], chord_type="minor", vol=0.09)
    # petit lead discret
    beat = 60.0 / bpm
    motif = [2, 5, 7, 9, 7, 5, 2, 0]
    for i, sem in enumerate(motif * 4):
        add_tone(b, i * beat * 0.5, beat * 0.35, note_freq(sem + 12), volume=0.05, kind="triangle", release=0.35)
    return b


def build_music_gameplay() -> list[float]:
    bpm = 148
    bars = 8
    duration = bars * 4 * (60.0 / bpm)
    b = make_buffer(duration)
    roots = [0, 3, -2, 5]  # A C G B
    add_bass_pattern(b, bpm=bpm, bars=bars, root_steps=roots, vol=0.16)
    add_arp_pattern(b, bpm=bpm, bars=bars, chord_roots=[r + 12 for r in roots], chord_type="minor", vol=0.11)
    beat = 60.0 / bpm
    lead = [12, 14, 15, 19, 17, 15, 14, 12]
    for i, sem in enumerate(lead * 4):
        add_tone(b, i * beat * 0.5, beat * 0.28, note_freq(sem), volume=0.06, kind="saw", release=0.25)
    return b


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    sounds_dir = repo_root / "sounds"

    targets = {
        "sfx_shoot.wav": build_sfx_shoot(),
        "sfx_explosion.wav": build_sfx_explosion(),
        "sfx_pickup.wav": build_sfx_pickup(),
        "sfx_dash.wav": build_sfx_dash(),
        "sfx_warp.wav": build_sfx_warp(),
        "music_menu_loop.wav": build_music_menu(),
        "music_gameplay_loop.wav": build_music_gameplay(),
    }

    for name, data in targets.items():
        out = sounds_dir / name
        write_wav(out, data)
        print(f"Generated: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
