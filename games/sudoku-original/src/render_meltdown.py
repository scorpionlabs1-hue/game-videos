#!/usr/bin/env python3
"""Render a 26 s "meltdown" short for Sudoku - Original.

A cartoon player is 58 minutes into an Expert puzzle. Every mistake makes him
sweat more, his eye starts twitching, numbers spin round his head, his face goes
red and steam comes out of his ears, and after the third mistake he squeezes his
phone so hard the screen cracks. Punchline: new phone, new plan, tap Hint.
Reuses the game screen, palettes, art and sounds from render_short_v2.py; the
character, the cracks and the extra sound effects are drawn/synthesised here.

Timeline
  0.0 - 14.8  player holding the phone; mistakes at 4.2, 8.6 and 12.2
 14.8 - 17.0  CRACK! shake, flying glass, shocked face
 17.0 - 19.6  zoom into the cracked, glitching screen: "RIP PHONE."
 19.6 - 22.4  new phone, finger taps Hint, the answer pops in
 22.4 - 26.0  end card: "HARD ENOUGH TO CRACK YOU?"

Usage: python3 render_meltdown.py [output.mp4]
       PREVIEW=1,5,10,13.5,15,16.5,18,21.5,24 python3 render_meltdown.py
"""
import math
import os
import random
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

_argv, sys.argv = sys.argv, sys.argv[:1]
import render_short_v2 as base  # noqa: E402
sys.argv = _argv

from render_short_v2 import (DARK, GOLD, WHITE, art, back, cell_rect, clamp,  # noqa: E402
                             draw_game, ease, font, mix, overlay, paste, star)

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base.GAME, "exports", "meltdown-26s.mp4")
W, H, FPS, DUR = base.W, base.H, 30, 26.0
NFRAMES = int(FPS * DUR)
P = DARK

T_MISS = [4.2, 8.6, 12.2]
T_CRACK, T_ZOOM, T_RIP, T_HINT, T_END = 14.8, 17.0, 17.5, 19.6, 22.4
T_TAP = 21.0

# ------------------------------------------------------------------ game states
SOL, ORDER = base.SOLUTION, base.ORDER


def wrong_value(r, c):
    return next(v for v in range(1, 10) if v != SOL[r][c] and v not in base.GRID0[r])


EV_PLAY = [(0.6 + 0.7 * i, "fill", *ORDER[i], SOL[ORDER[i][0]][ORDER[i][1]]) for i in range(4)]
for k, t in enumerate(T_MISS):
    r, c = ORDER[4 + k]
    EV_PLAY.append((t, "wrong", r, c, wrong_value(r, c)))
    if k < 2:
        EV_PLAY.append((t + 1.4, "erase", r, c, 0))
EV_PLAY.sort(key=lambda e: e[0])

HR, HC = ORDER[4]
EV_HINT = [(-10.0 + i, "fill", *ORDER[i], SOL[ORDER[i][0]][ORDER[i][1]]) for i in range(4)]
EV_HINT.append((-1.0, "erase", HR, HC, 0))
EV_HINT.append((T_TAP + 0.15, "fill", HR, HC, SOL[HR][HC]))
base.GAME_START = -60.0


def game_screen(now, events, timer, red=0.0, freeze=None):
    """The in-game screen with the difficulty set to Expert and a custom timer."""
    base.EVENTS = events
    img = draw_game(now, P, freeze=freeze)
    col = mix(P["text"], (255, 70, 70), red)

    def patch(d):
        d.rectangle([450, 486, 630, 528], fill=P["bg"])
        d.text((540, 506), "Expert", font=font("Bold", 30), fill=P["text"], anchor="mm")
        d.rectangle([784, 404, 944, 462], fill=P["surface"])
        s = int(timer)
        d.text((786, 413), f"{s // 60:02d}:{s % 60:02d}", font=font("Bold", 32), fill=col)
    overlay(img, patch)
    return img


def cell_center(r, c):
    x0, y0, x1, y1 = cell_rect(r, c)
    return (x0 + x1) / 2, (y0 + y1) / 2


def key_center(v):
    return 36 + (v - 1) * 112 + 54, 1770 + 64


def fingertip(img, x, y, press):
    r = 46 * (1 - 0.25 * press)
    overlay(img, lambda d: d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 90),
                                     outline=(255, 255, 255, 210), width=5))


# ------------------------------------------------------------------ cracked glass
def _make_cracks():
    rnd = random.Random(11)
    ix, iy = 600, 1120
    segs = []  # (x0, y0, x1, y1, distance from impact, width)

    def walk(x, y, ang, length, width, depth):
        step_len, dist = 0.0, math.hypot(x - ix, y - iy)
        while step_len < length and -50 < x < W + 50 and -50 < y < H + 50:
            s = rnd.uniform(35, 85)
            ang += rnd.uniform(-0.28, 0.28)
            nx, ny = x + s * math.cos(ang), y + s * math.sin(ang)
            segs.append((x, y, nx, ny, dist, width))
            dist += s
            step_len += s
            x, y = nx, ny
            if depth < 2 and rnd.random() < 0.16:
                walk(x, y, ang + rnd.choice([-1, 1]) * rnd.uniform(0.5, 1.1), rnd.uniform(120, 380), max(2, width - 1), depth + 1)

    n = 15
    rays = [i * 2 * math.pi / n + rnd.uniform(-0.15, 0.15) for i in range(n)]
    for a in rays:
        walk(ix, iy, a, rnd.uniform(650, 1700), 4, 0)
    # broken rings around the impact
    for rad in (70, 150, 270, 420):
        for i in range(n):
            if rnd.random() < 0.25 and rad > 100:
                continue
            a0, a1 = rays[i], rays[(i + 1) % n] + (2 * math.pi if i == n - 1 else 0)
            r0, r1 = rad * rnd.uniform(0.85, 1.15), rad * rnd.uniform(0.85, 1.15)
            segs.append((ix + r0 * math.cos(a0), iy + r0 * math.sin(a0),
                         ix + r1 * math.cos(a1), iy + r1 * math.sin(a1), rad, 3))
    shards = []
    for i in range(n):
        a0, a1 = rays[i], rays[(i + 1) % n]
        r = rnd.uniform(40, 75)
        shards.append([(ix, iy), (ix + r * math.cos(a0), iy + r * math.sin(a0)), (ix + r * math.cos(a1), iy + r * math.sin(a1))])
    return (ix, iy), segs, shards


IMPACT, CRACKS, CENTER_SHARDS = _make_cracks()


def crack_overlay(img, local):
    """Draw the cracks on a game-sized screen image, `local` seconds after impact."""
    if local < 0:
        return img
    reach = 2200 * ease(local / 0.3)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x0, y0, x1, y1, dist, w in CRACKS:
        if dist < reach:
            d.line([(x0, y0), (x1, y1)], fill=(0, 0, 0, 150), width=w + 5)
    for x0, y0, x1, y1, dist, w in CRACKS:
        if dist < reach:
            d.line([(x0, y0), (x1, y1)], fill=(235, 245, 255, 235), width=w)
    for i, sh in enumerate(CENTER_SHARDS):
        d.polygon(sh, fill=(220, 235, 255, 90 + 60 * (i % 2)))
    img = img.copy()
    img.alpha_composite(layer)
    # dead LCD: an ink blot spreading from the corner and a stuck green line
    if local > 0.4:
        k = ease((local - 0.4) / 2.5)
        blot = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(blot).ellipse([820 - 260 * k, 1540 - 300 * k, 1300 + 200 * k, 2100], fill=(5, 5, 8, 245))
        img.alpha_composite(blot.filter(ImageFilter.GaussianBlur(28)))
        overlay(img, lambda d: d.rectangle([318, 0, 323, H], fill=(60, 255, 120, 210)))
    # glitch bands
    rnd = random.Random(int(local * 12))
    if local > 0.1 and rnd.random() < 0.7:
        for _ in range(rnd.randint(1, 3)):
            y = rnd.randint(0, H - 80)
            h = rnd.randint(12, 70)
            dx = rnd.randint(-60, 60)
            band = img.crop((0, y, W, y + h))
            tint = Image.new("RGBA", band.size, rnd.choice([(255, 0, 140, 60), (0, 230, 255, 60)]))
            band.alpha_composite(tint)
            img.paste(band, (dx, y))
    return img


# ------------------------------------------------------------------ character
SKIN, SKIN_DARK, HAIR = (246, 196, 160), (222, 162, 128), (54, 36, 30)
SHIRT, SHIRT_DARK = (64, 112, 214), (44, 82, 170)
HX, HY = 540, 430
SS = 2  # supersampling for the character


def rot_ellipse(cx, cy, rx, ry, ang, n=40):
    ca, sa = math.cos(ang), math.sin(ang)
    return [(cx + rx * math.cos(t) * ca - ry * math.sin(t) * sa, cy + rx * math.cos(t) * sa + ry * math.sin(t) * ca)
            for t in (2 * math.pi * i / n for i in range(n))]


class D2:
    """ImageDraw wrapper that scales every coordinate by SS."""

    def __init__(self, layer):
        self.d = ImageDraw.Draw(layer)

    def _p(self, pts):
        return [(x * SS, y * SS) for x, y in pts]

    def ellipse(self, b, **kw):
        self.d.ellipse([v * SS for v in b], **kw)

    def rrect(self, b, r, **kw):
        self.d.rounded_rectangle([v * SS for v in b], r * SS, **kw)

    def poly(self, pts, **kw):
        self.d.polygon(self._p(pts), **kw)

    def line(self, pts, width, **kw):
        self.d.line(self._p(pts), width=int(width * SS), joint="curve", **kw)
        r = width * SS / 2
        for x, y in self._p([pts[0], pts[-1]]):
            self.d.ellipse([x - r, y - r, x + r, y + r], fill=kw.get("fill"))

    def arc(self, b, a0, a1, width, **kw):
        self.d.arc([v * SS for v in b], a0, a1, width=int(width * SS), **kw)


def curve(x0, x1, y_fn, n=24):
    return [(x0 + (x1 - x0) * i / n, y_fn(i / n)) for i in range(n + 1)]


def mood(now):
    """Stress, anger and shock levels over time (all 0..1)."""
    stress = np.interp(now, [0, 3.0, T_MISS[0] + 0.3, T_MISS[1] + 0.3, T_MISS[2] + 0.3, T_CRACK],
                       [0.05, 0.12, 0.38, 0.62, 0.85, 1.0])
    anger = np.interp(now, [10.8, T_MISS[2] + 0.4, T_CRACK - 0.1, T_CRACK + 0.3, T_CRACK + 1.4], [0, 0.55, 1.0, 1.0, 0.0])
    shock = 1.0 if now >= T_CRACK + 0.15 else 0.0
    return float(stress), float(anger), shock


def draw_guy(now, layer):
    stress, anger, shock = mood(now)
    d = D2(layer)
    tremble = anger * 6 * math.sin(now * 55) if not shock else 0
    hx, hy = HX + tremble, HY - 8 * shock
    skin = mix(SKIN, (232, 92, 78), anger * 0.85) if not shock else mix(SKIN, (236, 226, 214), 0.45)

    # torso and neck
    d.poly([(170, 1920), (230, 760), (380, 690), (700, 690), (850, 760), (910, 1920)], fill=SHIRT)
    d.poly([(380, 690), (540, 790), (700, 690)], fill=SHIRT_DARK)
    d.rrect([470, 600, 610, 730], 40, fill=SKIN_DARK)
    d.poly([(420, 690), (540, 770), (660, 690), (640, 700), (540, 745), (440, 700)], fill=(232, 236, 245))

    # ears, head
    for sx in (-1, 1):
        d.ellipse([hx + sx * 198 - 34, hy - 10, hx + sx * 198 + 34, hy + 78], fill=skin)
        d.ellipse([hx + sx * 198 - 16, hy + 12, hx + sx * 198 + 16, hy + 56], fill=mix(skin, SKIN_DARK, 0.6))
    d.ellipse([hx - 200, hy - 235, hx + 200, hy + 235], fill=skin)

    # hair: stands up more as stress rises
    lift = 30 * stress + 40 * shock
    d.ellipse([hx - 212, hy - 260, hx + 212, hy - 100], fill=HAIR)
    spikes = []
    for i in range(9):
        x = hx - 200 + i * 50
        spikes += [(x, hy - 190), (x + 25, hy - 262 - lift * (0.6 + 0.4 * math.sin(i * 1.7)) - 12 * (i % 2))]
    spikes += [(hx + 210, hy - 190), (hx + 210, hy - 120), (hx - 210, hy - 120)]
    d.poly(spikes, fill=HAIR)
    d.poly([(hx - 205, hy - 120), (hx - 120, hy - 175), (hx - 40, hy - 120), (hx + 50, hy - 170),
            (hx + 140, hy - 118), (hx + 205, hy - 150), (hx + 205, hy - 210), (hx - 205, hy - 210)], fill=HAIR)

    # eyes
    look = 0 if shock else 20
    ery = 46 + 10 * stress + 16 * shock - 14 * anger
    pr = 17 - 6 * stress - 3 * shock + 2 * anger
    twitch = stress > 0.45 and not shock and (now * 1.6) % 1 < 0.12
    for sx in (-1, 1):
        ex, ey = hx + sx * 82, hy - 20
        if stress > 0.25:
            bag = int(140 * clamp((stress - 0.25) / 0.5))
            d.arc([ex - 44, ey + ery - 30, ex + 44, ey + ery + 22], 20, 160, 5, fill=(150, 90, 110, bag))
        d.ellipse([ex - 44, ey - ery, ex + 44, ey + ery], fill=(255, 255, 255), outline=(60, 40, 40), width=6)
        if anger > 0.3 and not shock:
            for k in range(3):
                vx = ex - 30 + k * 26
                d.line([(vx, ey - ery + 8), (vx + 8, ey - 6), (vx + 2, ey + 10)], 2.5, fill=(230, 60, 60))
        d.ellipse([ex - pr, ey + look - pr, ex + pr, ey + look + pr], fill=(40, 28, 28))
        d.ellipse([ex - pr * 0.3 + 5, ey + look - pr * 0.6, ex + pr * 0.3 + 5, ey + look], fill=WHITE)
        if twitch and sx == -1:
            d.ellipse([ex - 48, ey - ery - 6, ex + 48, ey + ery * 0.35], fill=skin)
            d.line([(ex - 44, ey + ery * 0.2), (ex + 44, ey + ery * 0.2)], 6, fill=(60, 40, 40))

    # brows: worried (inner ends up) -> angry (inner ends down) -> shocked (both high)
    worry = clamp(stress * 1.6) * (1 - anger)
    for sx in (-1, 1):
        ex = hx + sx * 82
        base_y = hy - 20 - ery - 26 - 30 * shock
        inner = base_y - 34 * worry + 42 * anger
        outer = base_y + 8 * worry - 10 * anger
        d.line([(ex - sx * 8 - sx * 46, outer), (ex - sx * 8 + sx * 0, (inner + outer) / 2 - 6), (ex - sx * 8 + sx * 48, inner)][::sx], 15,
               fill=HAIR)

    # nose and cheeks
    d.arc([hx - 22, hy + 30, hx + 22, hy + 76], 200, 340, 7, fill=SKIN_DARK)
    if anger > 0.2:
        for sx in (-1, 1):
            d.ellipse([hx + sx * 130 - 40, hy + 70, hx + sx * 130 + 40, hy + 110], fill=(225, 60, 60, int(170 * anger)))

    # mouth
    my = hy + 132
    if shock:
        open_ = 1 if now < T_ZOOM else 0.7
        d.ellipse([hx - 48, my - 50 * open_, hx + 48, my + 62 * open_], fill=(70, 20, 30), outline=(60, 30, 30), width=6)
        d.ellipse([hx - 30, my + 20 * open_, hx + 30, my + 56 * open_], fill=(220, 90, 100))
    elif anger > 0.35 or stress > 0.55:
        mw = 86 + 30 * anger
        mh = 30 + 18 * anger
        d.rrect([hx - mw, my - mh, hx + mw, my + mh], 22, fill=WHITE, outline=(60, 30, 30), width=7)
        for k in range(1, 6):
            x = hx - mw + k * 2 * mw / 6
            d.line([(x, my - mh + 4), (x, my + mh - 4)], 4, fill=(170, 160, 160))
        d.line([(hx - mw + 4, my), (hx + mw - 4, my)], 4, fill=(170, 160, 160))
    elif stress > 0.2:
        wob = 10 * math.sin(now * 7)
        d.line(curve(hx - 72, hx + 72, lambda u: my + 10 * math.sin(u * 4 * math.pi + wob * 0.1) + 6), 9, fill=(110, 40, 50))
    else:
        d.line(curve(hx - 50, hx + 50, lambda u: my - 5 * math.sin(u * math.pi) + 3), 9, fill=(110, 40, 50))

    # anger mark on the temple
    if anger > 0.45 and not shock:
        ax, ay = hx + 150, hy - 140
        a = int(255 * clamp((anger - 0.45) * 3))
        pulse = 1 + 0.15 * math.sin(now * 14)
        for qx, qy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            cx, cy = ax + qx * 34 * pulse, ay + qy * 34 * pulse
            mid = math.degrees(math.atan2(-qy, -qx))
            d.arc([cx - 26, cy - 26, cx + 26, cy + 26], mid - 45, mid + 45, 9, fill=(230, 40, 40, a))
    return stress, anger, shock


def sweat(now, stress, d):
    if stress < 0.2:
        return
    n = int(1 + 6 * (stress - 0.2) / 0.8)
    for i in range(n):
        period = 1.6 - 0.2 * (i % 3)
        ph = (now / period + i * 0.37) % 1
        x = HX + (-150 + (i * 97) % 300)
        y0 = HY - 95 + (i * 53) % 70
        y = y0 + 260 * ph * ph
        a = int(230 * (1 - ph))
        r = 11 + 3 * (i % 2)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(140, 200, 255, a))
        d.poly([(x - r * 0.9, y - r * 0.3), (x, y - r * 2.4), (x + r * 0.9, y - r * 0.3)], fill=(140, 200, 255, a))
        d.ellipse([x - r * 0.4, y - r * 0.5, x + r * 0.1, y], fill=(255, 255, 255, a))
    # big anime drop on the side of the head
    if stress > 0.4:
        a = int(255 * clamp((stress - 0.4) * 4))
        x, y = HX - 255, HY - 150
        d.ellipse([x - 26, y - 10, x + 26, y + 50], fill=(150, 210, 255, a), outline=(80, 150, 230, a), width=4)
        d.poly([(x - 24, y + 14), (x, y - 50), (x + 24, y + 14)], fill=(150, 210, 255, a))


def steam(now, anger, d):
    if anger < 0.5:
        return
    for sx in (-1, 1):
        for k in range(5):
            ph = (now * 1.4 + k / 5) % 1
            x = HX + sx * (240 + 120 * ph) + 15 * math.sin(ph * 9 + k)
            y = HY + 20 - 260 * ph
            r = 22 + 60 * ph
            a = int(200 * (1 - ph) * clamp((anger - 0.5) * 3))
            d.ellipse([x - r, y - r, x + r, y + r], fill=(245, 245, 250, a))


def orbit_digits(now, stress, img):
    k = clamp((stress - 0.45) / 0.2) * (0 if now >= T_CRACK else 1)
    if k <= 0:
        return

    def draw(dd):
        spin = now * (1.5 + 2.5 * stress)
        for i in range(9):
            a = spin + i * 2 * math.pi / 9
            x = HX + 310 * math.cos(a)
            y = HY - 250 + 70 * math.sin(a)
            front = math.sin(a) > 0
            al = int(255 * k * (1 if front else 0.45))
            dd.text((x, y), str(i + 1), font=font("Bold", 64 if front else 48), fill=(255, 210, 70, al), anchor="mm",
                    stroke_width=4, stroke_fill=(40, 20, 10, al))
    overlay(img, draw)


# ------------------------------------------------------------------ scene
PX, PY, PW, PH = 230, 830, 620, 1072
SX, SY, SW, SH = PX + 22, PY + 24, 576, 1024


def room_bg(now, stress, anger):
    y = np.linspace(0, 1, H)[:, None]
    top = np.array([46, 36, 62]) * (1 - anger) + np.array([90, 22, 30]) * anger
    bot = np.array([14, 11, 20])
    arr = (top * (1 - y) + bot * y)[:, None, :].repeat(W, 1).reshape(H, W, 3)
    img = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    beat = 0.5 + 0.5 * math.sin(now * (6 + 6 * stress)) if stress > 0.4 else 0.3
    ImageDraw.Draw(glow).ellipse([90, 40, 990, 900], fill=(255, 190, 120, int(60 + 40 * stress * beat)))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(120)))
    return img


def phone_screen(now):
    """Game screen as shown on the phone (game coordinates, 1080x1920)."""
    stress = mood(now)[0]
    t = min(now, T_CRACK)
    timer = 58 * 60 + 7 + t
    img = game_screen(t, EV_PLAY, timer, red=clamp((stress - 0.5) * 3))
    for k, tm in enumerate(T_MISS):  # fingertip hits the wrong key
        if tm - 0.6 <= now <= tm + 0.25:
            r, c = ORDER[4 + k]
            sx, sy = cell_center(r, c)
            kx, ky = key_center(wrong_value(r, c))
            u = ease((now - (tm - 0.6)) / 0.5)
            fingertip(img, sx + (kx - sx) * u, sy + 60 + (ky - sy - 60) * u, math.sin(clamp((now - tm + 0.1) / 0.2) * math.pi))
    if now >= T_MISS[2] + 0.5:
        local = now - T_MISS[2] - 0.5
        overlay(img, lambda d: d.rectangle([0, 0, W, H], fill=(0, 0, 0, int(160 * ease(local / 0.25)))))
        s = back(local / 0.35)
        if s > 0:
            cw, ch, cx, cy = 820 * s, 600 * s, W / 2, 1000

            def card(d):
                d.rounded_rectangle([cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2], int(48 * s), fill=P["surface"] + (255,))
            overlay(img, card)
            if s > 0.6:
                hb = art("heart_broken", int(190 * s))
                paste(img, hb, cx - hb.width // 2, cy - ch / 2 + 40 * s)
                overlay(img, lambda d: (d.text((cx, cy + 80 * s), "Out of lives!", font=font("Bold", 76 * s), fill=P["text"], anchor="mm"),
                                        d.text((cx, cy + 170 * s), "58 minutes. Gone.", font=font("Medium", 42 * s), fill=P["text2"], anchor="mm")))
    if now >= T_CRACK:
        img = crack_overlay(img, now - T_CRACK)
    return img


def shake_offset(now):
    stress, anger, _ = mood(now)
    amp = 0
    if T_CRACK <= now < T_CRACK + 0.9:
        amp = 38 * (1 - (now - T_CRACK) / 0.9) ** 2
    elif anger > 0.4 and now < T_CRACK:
        amp = 5 * anger
    rnd = random.Random(int(now * FPS))
    return rnd.uniform(-amp, amp), rnd.uniform(-amp, amp)


def scene(now):
    stress, anger, shock = mood(now)
    img = room_bg(now, stress, anger)

    # character (supersampled)
    layer = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    draw_guy(now, layer)
    d2 = D2(layer)
    sweat(now, stress, d2)
    steam(now, anger, d2)
    img.alpha_composite(layer.resize((W, H), Image.LANCZOS))
    orbit_digits(now, stress, img)

    # phone in his hands; squeezed and trembling while he's angry
    trem = (anger * 7 * math.sin(now * 61), anger * 5 * math.cos(now * 47)) if now < T_CRACK else (0, 0)
    px, py = PX + trem[0], PY + trem[1]
    hands = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    hd = D2(hands)
    squeeze = 18 * anger if now < T_CRACK + 0.2 else 0
    for sx in (-1, 1):
        cx = px + PW / 2 + sx * (PW / 2 + 30 - squeeze)
        hd.poly(rot_ellipse(cx, py + 760, 110, 170, sx * 0.25), fill=mix(SKIN, (232, 92, 78), anger * 0.5))
    img.alpha_composite(hands.resize((W, H), Image.LANCZOS))

    overlay(img, lambda d: (d.rounded_rectangle([px, py, px + PW, py + PH], 72, fill=(22, 22, 28)),
                            d.rounded_rectangle([px + 6, py + 6, px + PW - 6, py + PH - 6], 66, outline=(70, 72, 84), width=3)))
    scr = phone_screen(now).convert("RGB").resize((SW, SH), Image.LANCZOS).convert("RGBA")
    m = Image.new("L", (SW, SH), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, SW - 1, SH - 1], 50, fill=255)
    scr.putalpha(m)
    img.alpha_composite(scr, (int(px + 22), int(py + 24)))
    overlay(img, lambda d: d.ellipse([px + PW / 2 - 11, py + 40, px + PW / 2 + 11, py + 62], fill=(10, 10, 14)))

    # fingers wrapped over the edges
    fingers = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    fd = D2(fingers)
    fcol = mix(SKIN, (232, 92, 78), anger * 0.5)
    for sx in (-1, 1):
        edge = px + (PW if sx == 1 else 0)
        for k in range(4):
            fy = py + 600 + k * 74
            fd.poly(rot_ellipse(edge - sx * (14 + squeeze * 0.6), fy, 46, 30, 0), fill=fcol, outline=mix(fcol, (0, 0, 0), 0.2))
        fd.poly(rot_ellipse(edge - sx * (8 + squeeze), py + 470, 34, 74, -sx * 0.35), fill=fcol, outline=mix(fcol, (0, 0, 0), 0.2))
    img.alpha_composite(fingers.resize((W, H), Image.LANCZOS))

    # impact flash, flying glass and a comic "CRACK!"
    if now >= T_CRACK:
        local = now - T_CRACK
        ix = SX + IMPACT[0] * SW / W
        iy = SY + IMPACT[1] * SH / H
        if local < 0.12:
            overlay(img, lambda d: d.rectangle([0, 0, W, H], fill=(255, 255, 255, int(230 * (1 - local / 0.12)))))
        rnd = random.Random(5)

        def glass(d):
            for _ in range(40):
                a = rnd.uniform(0, 2 * math.pi)
                v = rnd.uniform(500, 1500)
                sz = rnd.uniform(8, 22)
                x = ix + v * math.cos(a) * local
                y = iy + v * math.sin(a) * local + 1400 * local * local
                al = int(255 * clamp(1 - local / 1.1))
                rot = rnd.uniform(0, 6) + local * 8
                d.polygon([(x + sz * math.cos(rot + k * 2.1), y + sz * math.sin(rot + k * 2.1)) for k in range(3)],
                          fill=(215, 235, 255, al), outline=(255, 255, 255, al))
        overlay(img, glass)
        if local < 1.2:
            s = back(local / 0.25)
            a = int(255 * clamp((1.2 - local) / 0.25))

            def boom(d):
                cx, cy = W / 2, 330
                pts = []
                for k in range(24):
                    rr = (330 if k % 2 == 0 else 200) * s
                    ang = k * math.pi / 12 + 0.1
                    pts.append((cx + rr * math.cos(ang), cy + rr * 0.62 * math.sin(ang)))
                d.polygon(pts, fill=(255, 214, 40, a), outline=(40, 20, 10, a), width=8)
                d.text((cx, cy), "CRACK!", font=font("Bold", 150 * s), fill=(230, 40, 40, a), anchor="mm",
                       stroke_width=10, stroke_fill=(255, 255, 255, a))
            overlay(img, boom)
    return img


# ------------------------------------------------------------------ captions
def caption(img, text, alpha, color, y=110, size=66):
    if alpha <= 0:
        return

    def draw(d):
        f = font("Bold", size)
        while d.textlength(text, font=f) > 940:
            f = font("Bold", f.size - 4)
        w = d.textlength(text, font=f)
        d.rounded_rectangle([W / 2 - w / 2 - 40, y - f.size * 0.6 - 20, W / 2 + w / 2 + 40, y + f.size * 0.6 + 20],
                            36, fill=color + (int(240 * alpha),))
        d.text((W / 2, y), text, font=f, fill=(255, 255, 255, int(255 * alpha)), anchor="mm")
    overlay(img, draw)


RED = (225, 50, 60)
CAPTIONS = [
    (0.2, 3.9, "EXPERT SUDOKU. MINUTE 58.", P["accent"]),
    (3.9, 7.8, "FIRST MISTAKE… STAY CALM", (235, 140, 30)),
    (7.8, 11.4, "NOTHING FITS ANYMORE!", RED),
    (11.4, T_CRACK, "HE'S ABOUT TO SNAP…", RED),
    (T_CRACK + 1.2, T_ZOOM, "…OOPS.", (90, 90, 110)),
    (T_RIP, T_HINT, "RIP PHONE.", (90, 90, 110)),
    (T_HINT, T_TAP - 0.1, "NEW PHONE. NEW PLAN:", P["accent"]),
    (T_TAP - 0.1, T_END, "JUST TAP HINT.", (40, 170, 90)),
]


def captions(img, now):
    for t0, t1, s, col in CAPTIONS:
        if t0 <= now < t1:
            caption(img, s, ease((now - t0) / 0.15) * (1 - ease((now - t1 + 0.15) / 0.15)), col)


# ------------------------------------------------------------------ sections
def sec_scene(now):
    img = scene(now)
    dx, dy = shake_offset(now)
    if dx or dy:
        moved = Image.new("RGBA", (W, H), (14, 11, 20, 255))
        moved.alpha_composite(img, (int(dx), int(dy)))
        img = moved
    return img


def sec_zoom(now):
    """Push in from the whole scene to the phone's cracked screen."""
    local = now - T_ZOOM
    k = ease(local / 0.5)
    full = phone_screen(now).convert("RGBA")
    if k >= 1:
        img = full
    else:
        sc = scene(now)
        x0, y0 = SX * k, SY * k
        x1, y1 = W + (SX + SW - W) * k, H + (SY + SH - H) * k
        img = sc.crop((int(x0), int(y0), int(x1), int(y1))).resize((W, H), Image.LANCZOS)
        if k > 0.6:
            img = Image.blend(img, full, (k - 0.6) / 0.4)
    if now >= T_RIP:
        a = ease((now - T_RIP) / 0.3)
        overlay(img, lambda d: d.rectangle([0, 0, W, H], fill=(0, 0, 0, int(70 * a))))
    return img


def sec_hint(now):
    local = now - T_HINT
    img = game_screen(now, EV_HINT, 42 + local)
    hx, hy = 36 + 3 * 256 + 120, 1634 + 59
    if now < T_TAP:
        pulse = 0.5 + 0.5 * math.sin(local * 9)
        overlay(img, lambda d: d.rounded_rectangle([hx - 130 - 8 * pulse, hy - 68 - 8 * pulse, hx + 130 + 8 * pulse, hy + 68 + 8 * pulse],
                                                   28, outline=GOLD + (int(150 + 105 * pulse),), width=8))
    if T_TAP - 0.8 <= now <= T_TAP + 0.3:
        u = ease((now - (T_TAP - 0.8)) / 0.6)
        fingertip(img, 700 + (hx - 700) * u, 1350 + (hy - 1350) * u, math.sin(clamp((now - T_TAP + 0.1) / 0.2) * math.pi))
    if now >= T_TAP + 0.15:
        lt = now - T_TAP - 0.15
        x, y = cell_center(HR, HC)

        def draw(d):
            for k in range(6):
                a = k * math.pi / 3 + lt * 2
                rr = 80 + 130 * ease(lt / 0.5)
                star(d, x + rr * math.cos(a), y + rr * math.sin(a), 26 * (1 - ease((lt - 0.6) / 0.6)), GOLD, rot=lt * 3)
            d.ellipse([x - 66, y - 66, x + 66, y + 66], outline=GOLD + (int(255 * (1 - ease((lt - 0.8) / 0.4))),), width=9)
        overlay(img, draw)
    if local < 0.12:
        overlay(img, lambda d: d.rectangle([0, 0, W, H], fill=(255, 255, 255, int(200 * (1 - local / 0.12)))))
    return img


def sec_end(now):
    local = now - T_END
    img = base.end_bg().copy()
    cx = W // 2
    a = ease(local / 0.35)

    def head(d):
        for i, line in enumerate(["HARD ENOUGH", "TO CRACK YOU?"]):
            sz = 92 * (0.8 + 0.2 * back((local - i * 0.12) / 0.4))
            d.text((cx, 330 + i * 116), line, font=font("Bold", sz), fill=(255, 255, 255, int(255 * a)), anchor="mm")
        d.text((cx, 560), "Expert puzzles. Unlimited hints.", font=font("Medium", 48), fill=(205, 218, 255, int(255 * a)), anchor="mm")
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


SECTIONS = [(0.0, sec_scene), (T_ZOOM, sec_zoom), (T_HINT, sec_hint), (T_END, sec_end)]


def frame(n):
    now = n / FPS
    idx = max(i for i, (t0, _) in enumerate(SECTIONS) if now >= t0)
    img = SECTIONS[idx][1](now)
    t0 = SECTIONS[idx][0]
    if idx == 3 and now - t0 < 0.25:
        img = Image.blend(SECTIONS[2][1](t0 - 1e-3), img, ease((now - t0) / 0.25))
    captions(img, now)
    return img


# ------------------------------------------------------------------ audio
def build_audio(path):
    SR = base.SR
    n = int(SR * DUR)
    out = np.zeros(n)
    t = np.arange(n) / SR
    rng = np.random.default_rng(3)

    def add(sig, at, gain=1.0):
        i = int(at * SR)
        m = min(len(sig), n - i)
        if m > 0:
            out[i:i + m] += gain * sig[:m]

    def sfx(name, at, gain=1.0):
        add(base.load_wav(name), at, gain)

    # calm music that fades away as the tension builds, then comes back for the tip
    music = base.load_wav("music_calm")
    mus = np.zeros(n)
    m = min(len(music), n)
    mus[:m] = music[:m]
    env = np.interp(t, [0, 0.3, 4, 11, T_CRACK - 0.05, T_CRACK, T_HINT - 0.2, T_HINT + 0.3, DUR - 1.5, DUR],
                    [0, 1, 1, 0.25, 0.15, 0, 0, 1, 1, 0])
    if len(music) < n:  # loop it for the tip and end card
        k = int((T_HINT - 0.2) * SR)
        tail = music[:n - k]
        mus[k:k + len(tail)] = tail
    out += 0.45 * mus * env

    # clock ticks speeding up
    tick = np.sin(2 * np.pi * 2400 * np.arange(int(0.03 * SR)) / SR) * np.exp(-np.arange(int(0.03 * SR)) / (0.004 * SR))
    tt = 3.0
    while tt < T_CRACK:
        add(tick, tt, 0.25 + 0.25 * (tt / T_CRACK))
        tt += np.interp(tt, [3, 9, 14], [0.5, 0.33, 0.18])

    # heartbeat: lub-dub, faster and louder
    def thump(f, dur):
        k = np.arange(int(dur * SR)) / SR
        return np.sin(2 * np.pi * f * k * (1 - 0.3 * k / dur)) * np.exp(-k / (dur / 4))
    hb = 5.0
    while hb < T_CRACK - 0.2:
        g = 0.4 + 0.6 * (hb - 5) / (T_CRACK - 5)
        add(thump(58, 0.22), hb, 0.9 * g)
        add(thump(52, 0.2), hb + 0.17, 0.6 * g)
        hb += np.interp(hb, [5, 14], [0.95, 0.42])

    # rising tension drone
    i0, i1 = int(7.0 * SR), int(T_CRACK * SR)
    tt = t[i0:i1] - 7.0
    f = 90 + 70 * (tt / (T_CRACK - 7.0)) ** 2
    ph = 2 * np.pi * np.cumsum(f) / SR
    drone = (np.sin(ph) + 0.5 * np.sin(1.5 * ph) + 0.25 * np.sin(2.01 * ph)) * (tt / (T_CRACK - 7.0)) ** 1.5
    out[i0:i1] += 0.28 * drone

    for k, tm in enumerate(T_MISS):
        sfx("sfx_click", tm - 0.02, 0.8)
        sfx("sfx_error", tm, 1.0 + 0.2 * k)
    sfx("sfx_error", T_MISS[2] + 0.55, 0.8)

    # the crack: thud, sharp noise burst and glass tinkles
    L = int(0.9 * SR)
    k = np.arange(L) / SR
    noise = rng.standard_normal(L)
    burst = np.diff(noise, prepend=0) * np.exp(-k / 0.05)
    thud = np.sin(2 * np.pi * 50 * k * (1 - 0.4 * k)) * np.exp(-k / 0.12)
    crack = 0.7 * burst + 1.2 * thud
    for j in range(14):
        at = rng.uniform(0.02, 0.6)
        fr = rng.uniform(2800, 6500)
        kk = np.arange(int(0.25 * SR)) / SR
        ping = np.sin(2 * np.pi * fr * kk) * np.exp(-kk / 0.04) * 0.25
        s = int(at * SR)
        crack[s:s + len(ping)] += ping[:L - s]
    add(crack, T_CRACK, 1.3)

    # sad trombone for "RIP PHONE."
    notes = [(233.1, 0.45), (220.0, 0.45), (207.7, 0.45), (196.0, 1.1)]
    at = T_ZOOM + 0.2
    for fr, dur in notes:
        kk = np.arange(int(dur * SR)) / SR
        vib = 1 + (0.012 * np.sin(2 * np.pi * 6 * kk) if dur > 1 else 0)
        phs = 2 * np.pi * np.cumsum(fr * vib) / SR
        saw = sum(np.sin(h * phs) / h for h in range(1, 8))
        env_ = np.minimum(1, kk / 0.04) * np.minimum(1, (dur - kk) / 0.08)
        add(0.35 * saw * env_, at)
        at += dur

    sfx("sfx_click", T_TAP - 0.02, 1.0)
    sfx("sfx_hint", T_TAP + 0.05, 1.0)
    sfx("sfx_number", T_TAP + 0.15, 0.9)
    sfx("sfx_complete", T_TAP + 0.25, 0.7)
    sfx("sfx_hint", T_END + 0.8, 0.7)

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
            frame(int(float(ts) * FPS)).convert("RGB").save(f"meltdown-{ts}.png")
    else:
        main()
