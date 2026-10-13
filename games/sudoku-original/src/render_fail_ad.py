#!/usr/bin/env python3
"""Render a 20 s "fail" ad for Sudoku - Original.

A player misses an obvious answer three times and runs out of lives, then the
video asks the viewer to spot it and reveals it. Viewers think "I could do
better" and install. Reuses the game screen, palettes, art and sounds from
render_short_v2.py.

Timeline
  0.0 -  3.0  nearly finished board, one row missing only a 9
  3.0 -  9.4  three wrong taps (3, 7, 1), each breaking a heart
  9.4 - 11.4  "Out of lives!"
 11.4 - 14.4  "CAN YOU SEE IT?" with a 3-2-1 countdown
 14.4 - 16.4  the answer, 9, pops in
 16.4 - 20.0  end card: "THINK YOU'RE SMARTER?"

Usage: python3 render_fail_ad.py [output.mp4]
       PREVIEW=2,4,7,10,13,15,18 python3 render_fail_ad.py
"""
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw

_argv, sys.argv = sys.argv, sys.argv[:1]
import render_short_v2 as base  # noqa: E402
sys.argv = _argv

from render_short_v2 import (DARK, GOLD, WHITE, art, back, cell_rect, clamp,  # noqa: E402
                             draw_game, ease, font, overlay, paste, star)

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base.GAME, "exports", "ad-20s-fail.mp4")
W, H, FPS, DUR = base.W, base.H, 30, 20.0
NFRAMES = int(FPS * DUR)
P = DARK

# ------------------------------------------------------------------ puzzle state
SOL = base.SOLUTION
TR, TC = 1, 8                      # target cell: row 2 is 5 1 4 2 7 6 3 8 _
ANSWER = SOL[TR][TC]
assert ANSWER == 9 and sorted(SOL[TR][:TC]) == [1, 2, 3, 4, 5, 6, 7, 8]
# One extra blank per digit 1-8 (outside the target row and column), so every key
# stays on the number pad - the game hides a key once all nine copies are placed.
_PICK = sorted(((r, c) for r in range(9) for c in range(9) if r != TR and c != TC),
               key=lambda rc: (rc[0] * 4 + rc[1] * 7) % 81)  # scattered, deterministic
BLANKS = {(TR, TC)}
for _d in range(1, 9):
    BLANKS.add(next(rc for rc in _PICK if SOL[rc[0]][rc[1]] == _d))
# original clues stay "given" (minus the blanks); the rest look player-entered
GIVENS = [[0 if (r, c) in BLANKS else base.GRID0[r][c] for c in range(9)] for r in range(9)]
GRID = [[0 if (r, c) in BLANKS else SOL[r][c] for c in range(9)] for r in range(9)]

T_TAPS = [(3.0, 3), (5.6, 7), (8.4, 1)]
T_OVER, T_ASK, T_REVEAL, T_END = 9.4, 11.4, 14.4, 16.4
ROW_HIT = {v: SOL[TR].index(v) for _, v in T_TAPS}  # where each wrong number already is in the row

events = []
for r in range(9):
    for c in range(9):
        if GRID[r][c] and not GIVENS[r][c]:
            events.append((-5.0, "fill", r, c, GRID[r][c]))
events.append((-1.0, "erase", TR, TC, 0))   # puts the selection on the target cell
for t, v in T_TAPS:
    events.append((t, "wrong", TR, TC, v))
    events.append((t + 1.7, "erase", TR, TC, 0))
events.append((T_REVEAL, "fill", TR, TC, ANSWER))
events.sort(key=lambda e: e[0])
base.EVENTS = events
base.GRID0 = GIVENS
base.GAME_START = -60.0  # timer reads as a few minutes into the game


# ------------------------------------------------------------------ helpers
def caption(img, text, alpha, color, y=150, size=72):
    if alpha <= 0:
        return
    lines = text.split("\n")

    def draw(d):
        f = font("Bold", size)
        while max(d.textlength(l, font=f) for l in lines) > 940:
            f = font("Bold", f.size - 4)
        lh = f.size * 1.18
        top = y - lh * (len(lines) - 1) / 2
        w = max(d.textlength(l, font=f) for l in lines)
        d.rounded_rectangle([W / 2 - w / 2 - 42, top - lh / 2 - 22, W / 2 + w / 2 + 42, top + lh * (len(lines) - 0.5) + 22],
                            38, fill=color + (int(240 * alpha),))
        for i, l in enumerate(lines):
            d.text((W / 2, top + i * lh), l, font=f, fill=(255, 255, 255, int(255 * alpha)), anchor="mm")
    overlay(img, draw)


def cell_center(r, c):
    x0, y0, x1, y1 = cell_rect(r, c)
    return (x0 + x1) / 2, (y0 + y1) / 2


def key_center(v):
    return 36 + (v - 1) * 112 + 54, 1770 + 64


def finger(img, now):
    """A translucent fingertip that drifts to each number key and taps it."""
    for t, v in T_TAPS:
        if t - 0.7 <= now <= t + 0.25:
            sx, sy = cell_center(TR, TC)
            kx, ky = key_center(v)
            k = ease((now - (t - 0.7)) / 0.55)
            x, y = sx + (kx - sx) * k, sy + 60 + (ky - sy - 60) * k
            press = 1 - 0.25 * math.sin(clamp((now - t + 0.1) / 0.2) * math.pi)
            r = 46 * press

            def draw(d):
                d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 90), outline=(255, 255, 255, 200), width=5)
            overlay(img, draw)


def ring(img, r, c, color, alpha, pulse=0.0):
    x, y = cell_center(r, c)
    rad = 62 + 8 * pulse

    def draw(d):
        d.ellipse([x - rad, y - rad, x + rad, y + rad], outline=color + (int(255 * alpha),), width=9)
    overlay(img, draw)


# ------------------------------------------------------------------ sections
CAPTIONS = [
    (0.0, 3.0, "THIS PLAYER NEEDS\nJUST ONE NUMBER…", P["accent"]),
    (3.0, 5.6, "3?! SERIOUSLY?", P["error"]),
    (5.6, 8.4, "THERE'S ALREADY\nA 7 IN THIS ROW!", P["error"]),
    (8.4, T_OVER, "NOT 1 EITHER…", P["error"]),
]


def sec_play(now):
    img = draw_game(now, P)
    # pulse the empty target cell before the first tap
    if now < T_TAPS[0][0]:
        ring(img, TR, TC, GOLD, 0.6 + 0.4 * math.sin(now * 6), math.sin(now * 6))
    # circle the copy of the wrong number that is already in the row
    for t, v in T_TAPS:
        if t + 0.15 <= now < t + 1.7:
            a = ease((now - t - 0.15) / 0.2) * (1 - ease((now - t - 1.5) / 0.2))
            ring(img, TR, ROW_HIT[v], P["error"], a, math.sin((now - t) * 10))
    finger(img, now)
    for t0, t1, s, col in CAPTIONS:
        if t0 <= now < t1:
            caption(img, s, ease((now - t0) / 0.15) * (1 - ease((now - t1 + 0.15) / 0.15)), col)
    return img


def sec_over(now):
    local = now - T_OVER
    img = draw_game(T_TAPS[-1][0] + 0.5, P, freeze=T_TAPS[-1][0] + 0.5)
    overlay(img, lambda d: d.rectangle([0, 0, W, H], fill=(0, 0, 0, int(175 * ease(local / 0.25)))))
    s = back(local / 0.35)
    if s > 0:
        cw, ch = int(820 * s), int(640 * s)
        cx, cy = W // 2, 980

        def card(d):
            d.rounded_rectangle([cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2], int(48 * s), fill=P["surface"] + (255,))
        overlay(img, card)
        if s > 0.6:
            hb = art("heart_broken", int(190 * s))
            paste(img, hb, cx - hb.width // 2, cy - ch / 2 + 40 * s)

            def text(d):
                d.text((cx, cy + 70 * s), "Out of lives!", font=font("Bold", 76 * s), fill=P["text"], anchor="mm")
                d.text((cx, cy + 160 * s), "3 mistakes on ONE empty cell", font=font("Medium", 40 * s), fill=P["text2"], anchor="mm")
            overlay(img, text)
    caption(img, "GAME OVER…", ease(local / 0.2), P["error"])
    return img


def sec_ask(now):
    local = now - T_ASK
    img = draw_game(T_ASK, P, freeze=T_TAPS[-1][0] + 1.8)
    pulse = math.sin(local * 7)
    ring(img, TR, TC, GOLD, 0.8, pulse)
    x, y = cell_center(TR, TC)
    n = 3 - int(local)

    def draw(d):
        d.text((x, y + 2), "?", font=font("Bold", 80 + 8 * pulse), fill=GOLD, anchor="mm")
        if 1 <= n <= 3:
            k = local % 1
            sz = 300 * (1.15 - 0.25 * ease(k / 0.3))
            a = int(255 * (1 - ease((k - 0.7) / 0.3)))
            d.text((W // 2, 1100), str(n), font=font("Bold", sz), fill=(255, 255, 255, a), anchor="mm",
                   stroke_width=10, stroke_fill=(0, 0, 0, a))
    overlay(img, draw)
    caption(img, "CAN YOU SEE IT?", ease(local / 0.2), P["accent"])
    return img


def sec_reveal(now):
    local = now - T_REVEAL
    img = draw_game(now, P)
    x, y = cell_center(TR, TC)
    g = math.sin(clamp(local / 0.6) * math.pi)

    def draw(d):
        for k in range(6):
            a = k * math.pi / 3 + local * 2
            rr = 90 + 140 * ease(local / 0.5)
            star(d, x - 60 + rr * math.cos(a) * 0.9, y + rr * math.sin(a), 26 * (1 - ease((local - 0.6) / 0.6)), GOLD, rot=local * 3)
        d.ellipse([x - 70, y - 70, x + 70, y + 70], outline=P["success"] + (int(255 * max(g, 0.5)),), width=10)
    overlay(img, draw)
    caption(img, "IT'S 9! EASY, RIGHT?", ease(local / 0.2), P["success"])
    return img


def sec_end(now):
    local = now - T_END
    img = base.end_bg().copy()
    cx = W // 2
    a = ease(local / 0.35)

    def head(d):
        f = font("Bold", 96)
        for i, line in enumerate(["THINK YOU'RE", "SMARTER?"]):
            sz = 96 * (0.8 + 0.2 * back((local - i * 0.12) / 0.4))
            d.text((cx, 330 + i * 120), line, font=font("Bold", sz), fill=(255, 255, 255, int(255 * a)), anchor="mm")
        d.text((cx, 560), "Prove it.", font=font("Medium", 56), fill=(205, 218, 255, int(255 * a)), anchor="mm")
    overlay(img, head)
    s = back((local - 0.25) / 0.5)
    size = max(2, int(440 * s))
    icon = Image.open(os.path.join(base.ASSETS, "icon.png")).convert("RGBA").resize((size, size), Image.LANCZOS)
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], int(size * 0.22), fill=255)
    icon.putalpha(m)
    paste(img, icon, cx - size // 2, 880 - size // 2)
    b = ease((local - 0.8) / 0.35)
    pulse = 1 + 0.04 * math.sin(max(0.0, local - 1.2) * 6)
    bw, bh = int(780 * pulse), int(150 * pulse)

    def cta(d):
        d.text((cx, 1180), "Sudoku – Original", font=font("Bold", 72), fill=(255, 255, 255, int(255 * b)), anchor="mm")
        y0 = 1400
        d.rounded_rectangle([cx - bw // 2, y0 - bh // 2, cx + bw // 2, y0 + bh // 2], bh // 2, fill=(46, 108, 243, int(255 * b)))
        d.text((cx, y0), "PLAY FREE", font=font("Bold", 66), fill=(255, 255, 255, int(255 * b)), anchor="mm")
        d.text((cx, 1560), "on Google Play", font=font("Medium", 44), fill=(190, 200, 230, int(255 * b)), anchor="mm")
    overlay(img, cta)
    return img


SECTIONS = [(0.0, sec_play), (T_OVER, sec_over), (T_ASK, sec_ask), (T_REVEAL, sec_reveal), (T_END, sec_end)]


def frame(n):
    now = n / FPS
    idx = max(i for i, (t0, _) in enumerate(SECTIONS) if now >= t0)
    img = SECTIONS[idx][1](now)
    t0 = SECTIONS[idx][0]
    if idx in (2, 4) and now - t0 < 0.25:
        img = Image.blend(SECTIONS[idx - 1][1](t0 - 1e-3), img, ease((now - t0) / 0.25))
    return img


# ------------------------------------------------------------------ audio
def build_audio(path):
    SR = base.SR
    n = int(SR * DUR)
    out = np.zeros(n)
    music = base.load_wav("music_calm")[:n]
    env = np.ones(len(music))
    env[:int(0.3 * SR)] = np.linspace(0, 1, int(0.3 * SR))
    # duck the music while the game-over card is up, then bring it back for the reveal
    i0, i1, i2 = int(T_OVER * SR), int(T_ASK * SR), int((T_REVEAL - 0.3) * SR)
    env[i0:i1] = np.linspace(1, 0.25, i1 - i0)
    env[i1:i2] = 0.25
    env[i2:i2 + int(0.3 * SR)] = np.linspace(0.25, 1, int(0.3 * SR))
    env[-int(1.5 * SR):] *= np.linspace(1, 0, int(1.5 * SR))
    out[:len(music)] += 0.5 * music * env

    def add(name, t, gain=1.0):
        s = base.load_wav(name)
        i = int(t * SR)
        m = min(len(s), n - i)
        if m > 0:
            out[i:i + m] += gain * s[:m]

    for t, _ in T_TAPS:
        add("sfx_click", t - 0.02, 0.8)
        add("sfx_error", t, 1.0)
        add("sfx_click", t + 1.7, 0.6)
    add("sfx_error", T_OVER + 0.05, 0.8)
    for k in range(3):
        add("sfx_click", T_ASK + k, 1.0)
    add("sfx_number", T_REVEAL, 1.0)
    add("sfx_complete", T_REVEAL + 0.05, 1.0)
    add("sfx_hint", T_END + 0.8, 0.7)
    out = out / max(1e-9, np.abs(out).max()) * 0.9
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out * 32767).astype(np.int16).tobytes())


def main():
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    wav = OUT + ".wav"
    build_audio(wav)
    proc = subprocess.Popen([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", wav,
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", "-shortest", OUT,
    ], stdin=subprocess.PIPE)
    for i in range(NFRAMES):
        proc.stdin.write(frame(i).convert("RGB").tobytes())
        if i % 150 == 0:
            print(f"frame {i}/{NFRAMES}", flush=True)
    proc.stdin.close()
    proc.wait()
    os.remove(wav)
    if proc.returncode:
        sys.exit(proc.returncode)
    print("Wrote", OUT)


if __name__ == "__main__":
    if os.environ.get("PREVIEW"):
        for ts in os.environ["PREVIEW"].split(","):
            frame(int(float(ts) * FPS)).convert("RGB").save(f"fail-{ts}.png")
    else:
        main()
