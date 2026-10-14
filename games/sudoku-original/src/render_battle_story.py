#!/usr/bin/env python3
"""Render a 42 s story short for Sudoku - Original: "Loser Buys Chai".

Two friends at a cafe. Rohan brags he is the Sudoku king; Meera challenges him to
Battle Mode in Sudoku - Original, loser buys chai. She creates a room, he joins
with the code, they race on the same puzzle with live standings, Rohan leads,
Meera overtakes and wins, Rohan demands a rematch. The dialogue is voiced (see
make_battle_story_voices.py) and shown in speech bubbles. Reuses the game screens,
art and sounds from render_short_v2.py and render_battle.py; the characters and
the cafe are drawn here.

Timeline
  0.0 - 15.6  cafe: the brag and the challenge
 15.6 - 21.8  phone: Meera's battle room, Rohan joins with the code
 21.8 - 24.3  GET READY 3-2-1 GO
 24.3 - 33.2  the race with live standings and both faces
 33.2 - 37.8  results: Meera wins, "Rematch. NOW."
 37.8 - 42.5  end card: logo, "Download it on the Play Store", "It's FREE!"

Usage: python3 render_battle_story.py [output.mp4]
       PREVIEW=2,6,11,17,20.5,23,26.5,31,35,39.5,41.5 python3 render_battle_story.py
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
import render_battle as rb  # noqa: E402
sys.argv = _argv

from render_short_v2 import (DARK, GOLD, WHITE, art, back, clamp, draw_game,  # noqa: E402
                             ease, font, mix, overlay, paste)
from render_battle import button, page, tap  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base.GAME, "exports", "battle-story-42s.mp4")
W, H, FPS, DUR = base.W, base.H, 30, 42.5
NFRAMES = int(FPS * DUR)
P = DARK
T, T2 = P["text"], P["text2"]

T_LOBBY, T_GO, T_RACE, T_RESULTS, T_END = 15.6, 21.8, 24.3, 33.2, 37.8
CODE = "B7K4P9"
T_JOIN = 19.4
T_SOLVED = 32.6
T_REMATCH = 37.35

# ------------------------------------------------------------------ dialogue
# Voice lines (audio/battle-story/<id>-<speaker>.wav, made by make_battle_story_voices.py):
# (id, start, speaker, bubble text, expression of the speaker). Each bubble stays up
# while its line is spoken.
VOICE_DIR = os.path.join(base.GAME, "audio", "battle-story")
_SCRIPT = [
    ("01", 0.4, "rohan", "I'm basically the Sudoku king.\nNobody beats me.", "smug"),
    ("02", 4.1, "meera", "Oh really? Ever tried\nBattle Mode in\nSudoku – Original?", "smirk"),
    ("03", 8.1, "rohan", "Battle Mode?", "curious"),
    ("04", 9.0, "meera", "Same puzzle. Same clock.\nLoser buys chai!", "grin"),
    ("05", 13.5, "rohan", "Deal. Easy chai.", "smug"),
    ("06", 15.9, "meera", "Room code B7K4P9.\nJoin!", "grin"),
    ("07", 19.8, "rohan", "In. Let's go!", "determined"),
    ("08", 25.3, "rohan", "Already 60%!\nToo easy.", "smug"),
    ("09", 28.2, "meera", "Mm-hmm.", "calm"),
    ("10", 29.6, "rohan", "WAIT. How are you\nat 90%?!", "panic"),
    ("11", 34.0, "meera", "Chai's on you,\nKing.", "grin"),
    ("12", 35.6, "rohan", "Rematch. NOW.", "angry"),
    ("13", 38.5, "meera", None, "grin"),
    ("14", 40.3, "rohan", None, "grin"),
]


def _wav_len(lid, who):
    with wave.open(os.path.join(VOICE_DIR, f"{lid}-{who}.wav")) as w:
        return w.getnframes() / w.getframerate()


VOICES = [(lid, t, who, t + _wav_len(lid, who)) for lid, t, who, _, _ in _SCRIPT]
# (start, end, speaker, text, expression); end includes a short hold after speaking
LINES = [(t - 0.1, t + _wav_len(lid, who) + 0.35, who, text, ex) for lid, t, who, text, ex in _SCRIPT if text]
TALK = [(t, end, who) for _, t, who, end in VOICES]

# what each character looks like when not speaking
IDLE = [  # (start, rohan, meera)
    (0.0, "smug", "calm"), (4.1, "curious", "smirk"), (8.1, "curious", "smirk"), (13.5, "smug", "grin"),
    (15.6, "curious", "grin"), (21.8, "determined", "determined"), (25.3, "smug", "calm"),
    (28.9, "panic", "focus"), (32.6, "shock", "grin"), (34.0, "shock", "grin"), (35.6, "angry", "laugh"),
]


def expr_of(who, now):
    for t0, t1, sp, _, ex in LINES:
        if sp == who and t0 <= now < t1:
            return ex, any(w == who and a <= now < b for a, b, w in TALK)
    cur = IDLE[0]
    for row in IDLE:
        if now >= row[0]:
            cur = row
    return (cur[1] if who == "rohan" else cur[2]), False


# ------------------------------------------------------------------ characters
SS = 2
LOOK = {
    "rohan": dict(skin=(214, 160, 120), hair=(28, 22, 22), shirt=(240, 130, 45), shirt2=(200, 100, 30)),
    "meera": dict(skin=(234, 184, 146), hair=(46, 26, 24), shirt=(32, 168, 160), shirt2=(22, 128, 122)),
}


class D2:
    """ImageDraw wrapper: coordinates are scaled by SS for supersampling."""

    def __init__(self, layer):
        self.d = ImageDraw.Draw(layer)

    def ellipse(self, b, **kw):
        self.d.ellipse([v * SS for v in b], **kw)

    def rrect(self, b, r, **kw):
        self.d.rounded_rectangle([v * SS for v in b], r * SS, **kw)

    def poly(self, pts, **kw):
        self.d.polygon([(x * SS, y * SS) for x, y in pts], **kw)

    def line(self, pts, width, fill):
        self.d.line([(x * SS, y * SS) for x, y in pts], width=int(width * SS), fill=fill, joint="curve")
        r = width * SS / 2
        for x, y in (pts[0], pts[-1]):
            self.d.ellipse([x * SS - r, y * SS - r, x * SS + r, y * SS + r], fill=fill)

    def arc(self, b, a0, a1, width, fill):
        self.d.arc([v * SS for v in b], a0, a1, width=int(width * SS), fill=fill)


def curve(x0, x1, fn, n=20):
    return [(x0 + (x1 - x0) * i / n, fn(i / n)) for i in range(n + 1)]


def draw_head(d, who, cx, cy, s, ex, talking, now, look=(0, 0)):
    """Head and face centred on (cx, cy), head radius about 150*s."""
    L = LOOK[who]
    skin = L["skin"]
    if ex == "angry":
        skin = mix(skin, (225, 90, 80), 0.45)
    hr = 150 * s

    # hair behind the head (Meera's long hair)
    if who == "meera":
        d.ellipse([cx - hr * 1.12, cy - hr * 1.1, cx + hr * 1.12, cy + hr * 1.25], fill=L["hair"])
        d.rrect([cx - hr * 1.12, cy - hr * 0.1, cx + hr * 1.12, cy + hr * 1.75], hr * 0.5, fill=L["hair"])
    # ears
    for sx in (-1, 1):
        d.ellipse([cx + sx * hr * 0.98 - 24 * s, cy - 6 * s, cx + sx * hr * 0.98 + 24 * s, cy + 58 * s], fill=skin)
        if who == "meera":
            d.ellipse([cx + sx * hr * 0.98 - 8 * s, cy + 58 * s, cx + sx * hr * 0.98 + 8 * s, cy + 76 * s], fill=GOLD)
    d.ellipse([cx - hr, cy - hr * 1.1, cx + hr, cy + hr * 1.08], fill=skin)

    # hair on top
    if who == "rohan":
        d.ellipse([cx - hr * 1.05, cy - hr * 1.22, cx + hr * 1.05, cy - hr * 0.35], fill=L["hair"])
        spikes = []
        for i in range(8):
            x = cx - hr + i * hr * 0.27
            spikes += [(x, cy - hr * 0.9), (x + hr * 0.13, cy - hr * (1.32 + 0.08 * (i % 2)))]
        spikes += [(cx + hr, cy - hr * 0.9), (cx + hr, cy - hr * 0.6), (cx - hr, cy - hr * 0.6)]
        d.poly(spikes, fill=L["hair"])
        d.poly([(cx - hr * 1.0, cy - hr * 0.55), (cx - hr * 0.5, cy - hr * 0.8), (cx - hr * 0.1, cy - hr * 0.5),
                (cx + hr * 0.4, cy - hr * 0.78), (cx + hr * 1.0, cy - hr * 0.5), (cx + hr, cy - hr * 0.9),
                (cx - hr, cy - hr * 0.9)], fill=L["hair"])
    else:
        d.ellipse([cx - hr * 1.06, cy - hr * 1.2, cx + hr * 1.06, cy - hr * 0.3], fill=L["hair"])
        d.poly([(cx - hr * 1.02, cy - hr * 0.6), (cx - hr * 0.2, cy - hr * 0.95), (cx + hr * 0.15, cy - hr * 0.42),
                (cx + hr * 1.02, cy - hr * 0.55), (cx + hr * 1.0, cy - hr * 0.9), (cx - hr * 1.0, cy - hr * 0.9)], fill=L["hair"])
        d.ellipse([cx + hr * 0.45, cy - hr * 1.45, cx + hr * 0.95, cy - hr * 0.95], fill=L["hair"])  # bun
        d.ellipse([cx + hr * 0.5, cy - hr * 1.05, cx + hr * 0.7, cy - hr * 0.88], fill=(230, 70, 110))  # hair tie

    # eyes
    ink = (45, 30, 30)
    lx, ly = look
    for sx in (-1, 1):
        ex_, ey = cx + sx * 55 * s, cy - 8 * s
        if ex in ("laugh", "grin") and not (ex == "grin" and who == "rohan"):
            d.arc([ex_ - 28 * s, ey - 22 * s, ex_ + 28 * s, ey + 26 * s], 200, 340, 7 * s, fill=ink)
            continue
        if ex in ("smug", "smirk", "calm", "focus", "determined"):
            ry = 18 * s
        elif ex in ("shock", "panic"):
            ry = 38 * s
        else:
            ry = 30 * s
        rx = 28 * s if ex not in ("shock", "panic") else 32 * s
        d.ellipse([ex_ - rx, ey - ry, ex_ + rx, ey + ry], fill=WHITE, outline=ink, width=int(5 * s * SS / 2))
        pr = (9 if ex in ("shock", "panic") else 12) * s
        px, py = ex_ + lx * 10 * s, ey + ly * min(ry - pr, 10 * s)
        d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=ink)
        d.ellipse([px - pr * 0.2 + 3 * s, py - pr * 0.7, px + pr * 0.4 + 3 * s, py - pr * 0.1], fill=WHITE)
        if ex in ("smug", "smirk", "calm", "focus", "determined"):  # heavy lids
            d.line([(ex_ - rx - 2 * s, ey - ry + 3 * s), (ex_ + rx + 2 * s, ey - ry + 3 * s)], 6 * s, fill=ink)
        if who == "meera":  # lashes
            for k in (-1, 0, 1):
                ax = ex_ + sx * (rx * 0.6 + k * 6 * s)
                d.line([(ax, ey - ry), (ax + sx * 8 * s, ey - ry - 10 * s)], 3.5 * s, fill=ink)

    # brows
    for sx in (-1, 1):
        bx = cx + sx * 55 * s
        by = cy - 58 * s
        inner, outer = 0, 0
        if ex in ("angry", "determined"):
            inner, outer = 12, -6
        elif ex in ("panic", "curious"):
            inner, outer = -14 if ex == "panic" else -4, 4
        elif ex == "shock":
            inner, outer = -18, -18
        elif ex in ("smug", "smirk"):
            inner, outer = (-10, 0) if sx == 1 else (4, 0)
        d.line([(bx + sx * 30 * s, by + outer * s), (bx, by - 4 * s + (inner + outer) / 2 * s),
                (bx - sx * 30 * s, by + inner * s)], 9 * s, fill=L["hair"])

    # nose and blush
    d.arc([cx - 13 * s, cy + 22 * s, cx + 13 * s, cy + 50 * s], 200, 340, 5 * s, fill=mix(skin, (0, 0, 0), 0.25))
    if who == "meera" or ex in ("angry", "laugh"):
        for sx in (-1, 1):
            d.ellipse([cx + sx * 88 * s - 24 * s, cy + 36 * s, cx + sx * 88 * s + 24 * s, cy + 58 * s],
                      fill=(240, 120, 120, 120))

    # mouth
    my = cy + 82 * s
    open_ = talking and (int(now * 9) % 3 != 0)
    lip = (120, 40, 50)
    if ex == "shock":
        d.ellipse([cx - 22 * s, my - 26 * s, cx + 22 * s, my + 26 * s], fill=(80, 25, 35))
    elif ex == "panic":
        d.rrect([cx - 50 * s, my - 18 * s, cx + 50 * s, my + 22 * s], 14 * s, fill=WHITE, outline=lip, width=int(5 * s * SS / 2))
        d.line([(cx - 46 * s, my + 2 * s), (cx + 46 * s, my + 2 * s)], 3 * s, fill=(170, 160, 160))
    elif ex == "angry":
        if open_:
            d.ellipse([cx - 44 * s, my - 16 * s, cx + 44 * s, my + 30 * s], fill=(80, 25, 35))
        else:
            d.line(curve(cx - 40 * s, cx + 40 * s, lambda u: my + 8 * s - 10 * s * math.sin(u * math.pi)), 7 * s, fill=lip)
    elif open_:
        h = 26 if ex in ("grin", "laugh", "panic") else 20
        d.ellipse([cx - 36 * s, my - 10 * s, cx + 36 * s, my + h * s], fill=(80, 25, 35))
        d.ellipse([cx - 20 * s, my + (h - 14) * s, cx + 20 * s, my + (h - 2) * s], fill=(220, 100, 110))
    elif ex in ("grin", "laugh"):
        pts = curve(cx - 52 * s, cx + 52 * s, lambda u: my - 6 * s + 34 * s * math.sin(u * math.pi))
        d.poly(pts, fill=(80, 25, 35))
        d.poly(curve(cx - 46 * s, cx + 46 * s, lambda u: my - 6 * s + 8 * s * math.sin(u * math.pi)) +
               [(cx + 46 * s, my - 6 * s)], fill=WHITE)
    elif ex in ("smug", "smirk"):
        d.line(curve(cx - 34 * s, cx + 40 * s, lambda u: my + 4 * s - 14 * s * u * u), 7 * s, fill=lip)
    elif ex == "curious":
        d.ellipse([cx - 12 * s, my - 8 * s, cx + 12 * s, my + 12 * s], fill=(80, 25, 35))
    else:
        d.line(curve(cx - 30 * s, cx + 30 * s, lambda u: my + 5 * s * math.sin(u * math.pi)), 7 * s, fill=lip)

    # sweat
    if ex in ("panic", "shock"):
        for k in range(3):
            ph = (now * 0.9 + k * 0.33) % 1
            x = cx + (-90 + 80 * k) * s
            y = cy - 90 * s + 140 * s * ph
            a = int(230 * (1 - ph))
            r = 10 * s
            d.ellipse([x - r, y - r, x + r, y + r], fill=(140, 200, 255, a))
            d.poly([(x - r * 0.9, y - r * 0.3), (x, y - r * 2.4), (x + r * 0.9, y - r * 0.3)], fill=(140, 200, 255, a))
    if ex == "angry":  # anger mark
        ax, ay = cx + 100 * s, cy - 100 * s
        for qx, qy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            mx_, my_ = ax + qx * 20 * s, ay + qy * 20 * s
            mid = math.degrees(math.atan2(-qy, -qx))
            d.arc([mx_ - 16 * s, my_ - 16 * s, mx_ + 16 * s, my_ + 16 * s], mid - 45, mid + 45, 6 * s, fill=(230, 40, 40))


def draw_body(d, who, cx, top, s, phone_glow=True):
    """Shoulders/torso from y=top down, with two hands holding a phone."""
    L = LOOK[who]
    d.rrect([cx - 40 * s, top - 40 * s, cx + 40 * s, top + 40 * s], 20 * s, fill=mix(L["skin"], (0, 0, 0), 0.12))
    d.poly([(cx - 210 * s, top + 600 * s), (cx - 190 * s, top + 70 * s), (cx - 110 * s, top + 20 * s),
            (cx + 110 * s, top + 20 * s), (cx + 190 * s, top + 70 * s), (cx + 210 * s, top + 600 * s)], fill=L["shirt"])
    d.poly([(cx - 60 * s, top + 20 * s), (cx, top + 80 * s), (cx + 60 * s, top + 20 * s)], fill=L["shirt2"])


def draw_phone_in_hands(d, who, cx, cy, s, glow):
    L = LOOK[who]
    pw, ph = 120 * s, 210 * s
    d.rrect([cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2], 20 * s, fill=(22, 22, 28))
    d.rrect([cx - pw / 2 + 8 * s, cy - ph / 2 + 10 * s, cx + pw / 2 - 8 * s, cy + ph / 2 - 10 * s], 14 * s,
            fill=mix((20, 26, 40), (70, 120, 240), glow))
    for sx in (-1, 1):
        d.ellipse([cx + sx * pw / 2 - 34 * s, cy + 10 * s, cx + sx * pw / 2 + 34 * s, cy + 100 * s], fill=L["skin"])


def person_layer(who, cx, cy, s, now, phone=True, look=(0, 0), bob=0.0):
    ex, talking = expr_of(who, now)
    layer = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = D2(layer)
    cy = cy + bob
    draw_body(d, who, cx, cy + 150 * s, s)
    draw_head(d, who, cx, cy, s, ex, talking, now, look)
    if phone:
        draw_phone_in_hands(d, who, cx, cy + 390 * s, s, 0.6 + 0.4 * math.sin(now * 3))
    return layer.resize((W, H), Image.LANCZOS)


# ------------------------------------------------------------------ cafe scene
def cafe_bg(now):
    y = np.linspace(0, 1, H)[:, None]
    top, bot = np.array([250, 214, 170]), np.array([214, 160, 110])
    arr = (top * (1 - y) + bot * y)[:, None, :].repeat(W, 1).reshape(H, W, 3)
    img = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(img)
    # window with a city skyline
    d.rounded_rectangle([60, 620, 470, 1180], 24, fill=(120, 170, 220))
    rnd = random.Random(3)
    x = 70
    while x < 460:
        w_ = rnd.randint(40, 80)
        h_ = rnd.randint(120, 320)
        d.rectangle([x, 1170 - h_, min(460, x + w_), 1170], fill=(80, 110, 160))
        x += w_ + 6
    d.rounded_rectangle([60, 620, 470, 1180], 24, outline=(120, 80, 50), width=14)
    d.line([(265, 620), (265, 1180)], fill=(120, 80, 50), width=10)
    # shelf with jars
    d.rectangle([610, 820, 1040, 840], fill=(130, 85, 55))
    for k, col in enumerate([(240, 180, 60), (200, 90, 60), (110, 160, 90), (230, 140, 60)]):
        jx = 640 + k * 100
        d.rounded_rectangle([jx, 730, jx + 70, 820], 14, fill=col)
        d.rectangle([jx + 8, 718, jx + 62, 734], fill=(110, 75, 50))
    # hanging lamps
    for lx in (300, 780):
        d.line([(lx, 0), (lx, 300)], fill=(70, 50, 40), width=6)
        d.pieslice([lx - 90, 250, lx + 90, 400], 180, 360, fill=(60, 60, 70))
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse([lx - 260, 230, lx + 260, 760], fill=(255, 230, 160, 70))
        img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(70)))
        d = ImageDraw.Draw(img)
        d.ellipse([lx - 30, 310, lx + 30, 350], fill=(255, 240, 190))
    # sign
    d.rounded_rectangle([330, 420, 750, 520], 20, fill=(70, 45, 35))
    d.text((540, 470), "CHAI & PUZZLES", font=font("Bold", 42), fill=(255, 220, 150), anchor="mm")
    return img


def table_fg(img, now):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 1560, W, H], fill=(150, 95, 60))
    d.rectangle([0, 1540, W, 1580], fill=(120, 75, 45))
    for gx in (200, 880):  # chai glasses with steam
        d.polygon([(gx - 50, 1440), (gx + 50, 1440), (gx + 40, 1560), (gx - 40, 1560)], fill=(235, 235, 240))
        d.polygon([(gx - 44, 1470), (gx + 44, 1470), (gx + 38, 1552), (gx - 38, 1552)], fill=(196, 128, 70))

        def steam(dd, gx=gx):
            for k in range(3):
                ph = (now * 0.6 + k / 3) % 1
                x = gx - 20 + k * 20 + 10 * math.sin(ph * 8 + k)
                yy = 1420 - 140 * ph
                r = 10 + 18 * ph
                dd.ellipse([x - r, yy - r, x + r, yy + r], fill=(255, 255, 255, int(120 * (1 - ph))))
        overlay(img, steam)


def bubble(img, text, who, alpha, anchor_x, anchor_y, side, y_top=None):
    """Speech bubble with a tail pointing at (anchor_x, anchor_y)."""
    if alpha <= 0:
        return
    lines = text.split("\n")
    f = font("Bold", 50)
    tmp = ImageDraw.Draw(img)
    tw = max(tmp.textlength(l, font=f) for l in lines)
    lh = 62
    bw, bh = tw + 80, lh * len(lines) + 70
    s = 0.85 + 0.15 * back(alpha)
    bx = clamp((anchor_x - bw / 2 + side * 120 - 30) / (W - 60 - bw)) * (W - 60 - bw) + 30
    by = y_top if y_top is not None else anchor_y - bh - 70
    col = LOOK[who]["shirt"]

    def draw(d):
        a = int(255 * alpha)
        cxm, cym = bx + bw / 2, by + bh / 2

        def sc(x, y):
            return cxm + (x - cxm) * s, cym + (y - cym) * s
        tx = min(max(anchor_x, bx + 60), bx + bw - 60)
        d.polygon([sc(tx - 30, by + bh - 4), sc(tx + 30, by + bh - 4), sc(anchor_x, anchor_y)], fill=(255, 255, 255, a))
        x0, y0 = sc(bx, by)
        x1, y1 = sc(bx + bw, by + bh)
        d.rounded_rectangle([x0, y0, x1, y1], 40, fill=(255, 255, 255, a), outline=col + (a,), width=6)
        name = "Rohan" if who == "rohan" else "Meera"
        nf = font("Bold", 30)
        nw = d.textlength(name, font=nf)
        d.rounded_rectangle([x0 + 30, y0 - 24, x0 + 60 + nw, y0 + 24], 22, fill=col + (a,))
        d.text((x0 + 45, y0), name, font=nf, fill=(255, 255, 255, a), anchor="lm")
        for i, l in enumerate(lines):
            d.text((cxm, y0 + 40 * s + lh * s * (i + 0.5)), l, font=font("Bold", 50 * s), fill=(35, 30, 40, a), anchor="mm")
    overlay(img, draw)


def speech(img, now, anchors, y_tops=None):
    for t0, t1, sp, text, _ in LINES:
        if t0 <= now < t1:
            a = ease((now - t0) / 0.18) * (1 - ease((now - t1 + 0.15) / 0.15))
            ax, ay, side = anchors[sp]
            bubble(img, text, sp, a, ax, ay, side, (y_tops or {}).get(sp))


CAFE_POS = {"rohan": (300, 760, 1.0), "meera": (790, 760, 1.0)}


def sec_cafe(now):
    img = cafe_bg(now)
    for who, (cx, cy, s) in CAFE_POS.items():
        ex, talking = expr_of(who, now)
        bob = 6 * math.sin(now * 2 + (0 if who == "rohan" else 1.5)) + (4 * math.sin(now * 18) if talking else 0)
        look = (1, 0.2) if who == "rohan" else (-1, 0.2)
        img.alpha_composite(person_layer(who, cx, cy, s, now, phone=now > 9.0, look=look, bob=bob))
    table_fg(img, now)
    speech(img, now, {"rohan": (300, 580, -1), "meera": (790, 580, 1)}, {"rohan": 150, "meera": 150})
    return img


# ------------------------------------------------------------------ face cams
def facecam(img, who, cx, cy, r, now, ring=None):
    ex, talking = expr_of(who, now)
    layer = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = D2(layer)
    bg = (255, 226, 180) if who == "rohan" else (190, 236, 230)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=bg)
    hs = r / 175
    draw_body(d, who, cx, cy + 115 * hs + 150 * hs * 0.0 + 30 * hs, hs)
    draw_head(d, who, cx, cy - 10 * hs, hs, ex, talking, now, (0, 1))
    face = layer.resize((W, H), Image.LANCZOS)
    m = Image.new("L", (W, H), 0)
    ImageDraw.Draw(m).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    face.putalpha(Image.fromarray(np.minimum(np.array(face.getchannel("A")), np.array(m))))
    img.alpha_composite(face)
    col = ring or LOOK[who]["shirt"]
    overlay(img, lambda dd: dd.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col + (255,), width=10))
    name = "Rohan" if who == "rohan" else "Meera"
    overlay(img, lambda dd: (dd.rounded_rectangle([cx - 80, cy + r - 26, cx + 80, cy + r + 26], 26, fill=col + (255,)),
                             dd.text((cx, cy + r), name, font=font("Bold", 32), fill=WHITE, anchor="mm")))


CAM = {"rohan": (190, 180, 135), "meera": (890, 180, 135)}


def cams(img, now):
    for who, (cx, cy, r) in CAM.items():
        facecam(img, who, cx, cy, r, now)
    speech(img, now, {"rohan": (250, 330, 1), "meera": (830, 330, -1)}, {"rohan": 380, "meera": 380})


# ------------------------------------------------------------------ game screens
def sec_lobby(now):
    local = now - T_LOBBY
    img, d = page("Battle Room")
    d.rounded_rectangle([48, 410, 1032, 820], 40, fill=P["hero"])
    overlay(img, lambda dd: dd.rounded_rectangle([48, 410, 1032, 820], 40, outline=P["accent"] + (255,), width=4))
    d = ImageDraw.Draw(img)
    d.text((W // 2, 470), "Loser Buys Chai", font=font("Bold", 40), fill=WHITE, anchor="mm")
    d.text((W // 2, 528), "ROOM CODE", font=font("Bold", 26), fill=(190, 210, 240), anchor="mm")
    for k, ch in enumerate(CODE):
        cx = W // 2 - 5 * 66 + k * 132
        d.rounded_rectangle([cx - 56, 560, cx + 56, 680], 20, fill=P["bg"])
        d.text((cx, 620), ch, font=font("Bold", 80), fill=WHITE, anchor="mm")
    d.text((W // 2, 712), "Medium  ·  9×9  ·  No time limit", font=font("Medium", 30), fill=(200, 215, 240), anchor="mm")
    button(d, (88, 740, 520, 800), "Copy Code", P["accent"], False, 32)
    button(d, (560, 740, 992, 800), "Share Battle", P["accent"], False, 32)
    players = [("Meera", "fox", 0.0, 0.0), ("Rohan", "lion", T_JOIN - T_LOBBY, T_JOIN - T_LOBBY + 0.9)]
    joined = [p for p in players if local >= p[2]]
    d.text((60, 880), f"PLAYERS  {len(joined)}/2", font=font("Bold", 30), fill=T2, anchor="lm")
    for i, (name, av, tj, tr) in enumerate(joined):
        k = back((local - tj) / 0.35) if i else 1.0
        y = 930 + i * 150
        x = 48 + (1 - k) * W
        d.rounded_rectangle([x, y, x + 984, y + 130], 30, fill=P["surface"])
        paste(img, rb.avatar(av, 96), x + 20, y + 17)
        d.text((x + 140, y + 65), name + ("  (host)" if i == 0 else ""), font=font("Bold", 40), fill=T, anchor="lm")
        ready = local >= tr
        d.rounded_rectangle([x + 760, y + 37, x + 960, y + 93], 28, fill=P["success"] if ready else P["muted"])
        d.text((x + 860, y + 65), "READY" if ready else "JOINED", font=font("Bold", 28), fill=WHITE, anchor="mm")
    all_ready = len(joined) == 2 and local >= players[1][3]
    d.text((W // 2, 1560), "Everyone's ready!" if all_ready else "Waiting for players to join…",
           font=font("Medium", 34), fill=P["success"] if all_ready else T2, anchor="mm")
    press = T_GO - 0.35 < now < T_GO - 0.1
    button(d, (48, 1610, 1032, 1738), "START BATTLE", (P["sel"] if press else P["accent"]) if all_ready else P["muted"], press, 48)
    tap(img, W // 2, 1674, T_GO - 0.25, now)
    return framed(img, now)


def framed(game, now):
    """Game screen shrunk into the lower part of the frame, face cams on top."""
    img = Image.new("RGBA", (W, H), (16, 18, 28, 255))
    sc = 0.70
    gw, gh = int(W * sc), int(H * sc)
    g = game.convert("RGB").crop((0, 250, W, H)).resize((gw, int((H - 250) * sc)), Image.LANCZOS).convert("RGBA")
    m = Image.new("L", g.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, g.width - 1, g.height - 1], 40, fill=255)
    g.putalpha(m)
    x0, y0 = (W - gw) // 2, H - g.height - 50
    overlay(img, lambda d: d.rounded_rectangle([x0 - 14, y0 - 14, x0 + gw + 14, y0 + g.height + 14], 52, fill=(40, 42, 54)))
    img.alpha_composite(g, (x0, y0))
    overlay(img, lambda d: d.text((W // 2, 180), "VS", font=font("Bold", 90), fill=GOLD, anchor="mm",
                                  stroke_width=6, stroke_fill=(40, 20, 10)))
    cams(img, now)
    return img


def progress(name, now):
    k = clamp((now - T_RACE) / (T_SOLVED - T_RACE))
    if name == "Meera":
        return float(np.interp(k, [0, 0.15, 0.5, 0.62, 0.999], [0.05, 0.25, 0.6, 0.9, 0.99])) if now < T_SOLVED else 1.0
    return float(np.interp(k, [0, 0.15, 0.6, 1], [0.05, 0.6, 0.76, 0.86]))


def battle_bar(img, now):
    d = ImageDraw.Draw(img)
    d.rectangle([20, 380, 1060, 588], fill=P["bg"])
    d.rounded_rectangle([36, 388, 1044, 584], 26, fill=P["surface"])
    secs = 100 + int(max(0.0, min(now, T_SOLVED) - T_RACE) * 8)
    d.text((70, 420), "BATTLE", font=font("Bold", 24), fill=P["accent"], anchor="lm")
    d.text((70, 470), f"{secs // 60:02d}:{secs % 60:02d}", font=font("Bold", 52), fill=T, anchor="lm")
    d.text((70, 530), "Medium · 9×9", font=font("Medium", 24), fill=T2, anchor="lm")
    order = sorted([("Meera", "fox"), ("Rohan", "lion")], key=lambda p: -progress(p[0], now))
    for rank, (name, av) in enumerate(order):
        x = 300 + rank * 370
        d.rounded_rectangle([x, 404, x + 350, 568], 20, fill=P["soft"] if rank == 0 else P["muted"],
                            outline=GOLD if rank == 0 else None, width=3)
        d.text((x + 28, 440), f"{rank + 1}", font=font("Bold", 36), fill=GOLD if rank == 0 else T, anchor="mm")
        paste(img, rb.avatar(av, 72), x + 56, 408)
        d.text((x + 150, 444), name, font=font("Bold", 34), fill=T, anchor="lm")
        pr = progress(name, now)
        done = pr >= 1.0
        d.rounded_rectangle([x + 20, 500, x + 330, 518], 9, fill=P["bg"])
        d.rounded_rectangle([x + 20, 500, x + 20 + 310 * pr, 518], 9, fill=P["success"] if done else P["accent"])
        d.text((x + 175, 546), "Solved!" if done else f"{int(pr * 100)}%", font=font("Bold", 28), fill=T, anchor="mm")


def race_board(now):
    n = len(rb._rest)
    done = int(n * clamp((progress("Meera", now) - 0.38) / 0.62))
    base.EVENTS = rb.race_events[:rb.PREFILL] + [(T_RACE + 0.1 * i, "fill", r, c, base.SOLUTION[r][c])
                                                 for i, (r, c) in enumerate(rb._rest[:done])]
    img = draw_game(now, P)
    battle_bar(img, now)
    return img


def sec_go(now):
    local = now - T_GO
    img = race_board(T_RACE)
    overlay(img, lambda d: d.rectangle([0, 590, W, 1910], fill=P["bg"] + (240,)))
    third = (T_RACE - T_GO - 0.5) / 3

    def draw(d):
        if local < 0.5:
            d.text((W // 2, 1000), "GET READY", font=font("Bold", 110), fill=T, anchor="mm")
        else:
            k = local - 0.5
            n = 3 - int(k / third)
            kk = (k % third) / third
            label = str(n) if n >= 1 else "GO!"
            size = 340 * (1.2 - 0.3 * ease(kk / 0.4))
            d.text((W // 2, 1050), label, font=font("Bold", size),
                   fill=(P["success"] if n < 1 else WHITE) + (int(255 * (1 - ease((kk - 0.75) / 0.25))),), anchor="mm")
    overlay(img, draw)
    return framed(img, now)


def sec_race(now):
    img = race_board(now)
    if now >= T_SOLVED:
        local = now - T_SOLVED
        overlay(img, lambda d: d.rectangle([0, 590, W, H], fill=(0, 0, 0, int(150 * ease(local / 0.3)))))
        s = back(local / 0.35)
        overlay(img, lambda d: d.text((W // 2, 1100), "Meera solved it!", font=font("Bold", max(1, int(100 * s))),
                                      fill=P["success"], anchor="mm"))
    return framed(img, now)


def sec_results(now):
    local = now - T_RESULTS
    img, d = page("Final Results", back_arrow=False)
    s = back(local / 0.45)
    tr = art("trophy_gold_02", max(2, int(260 * s)))
    paste(img, tr, W // 2 - tr.width // 2, 560 - tr.height // 2 + math.sin(local * 3) * 6)
    a = ease((local - 0.3) / 0.3)
    overlay(img, lambda dd: (dd.text((W // 2, 770), "MEERA WINS!", font=font("Bold", 100), fill=GOLD + (int(255 * a),), anchor="mm"),
                             dd.text((W // 2, 860), "Rohan buys the chai", font=font("Medium", 42), fill=T2 + (int(255 * a),), anchor="mm")))
    d = ImageDraw.Draw(img)
    for i, (name, av, t) in enumerate([("Meera", "fox", 161), ("Rohan", "lion", 185)]):
        k = back((local - 0.5 - i * 0.15) / 0.35)
        if k <= 0:
            continue
        y = 960 + i * 140
        x = 48 + (1 - k) * W
        d.rounded_rectangle([x, y, x + 984, y + 120], 28, fill=P["soft"] if i == 0 else P["surface"])
        medal = GOLD if i == 0 else (200, 205, 215)
        d.ellipse([x + 22, y + 30, x + 82, y + 90], fill=medal)
        d.text((x + 52, y + 60), str(i + 1), font=font("Bold", 34), fill=(30, 30, 30), anchor="mm")
        paste(img, rb.avatar(av, 84), x + 104, y + 18)
        d.text((x + 210, y + 60), name, font=font("Bold", 42), fill=T, anchor="lm")
        d.text((x + 950, y + 60), f"{t // 60:02d}:{t % 60:02d}", font=font("Bold", 42), fill=T, anchor="rm")
    if local > 1.3:
        press = T_REMATCH - 0.15 < now < T_REMATCH + 0.1
        button(d, (48, 1300, 520, 1420), "Rematch", P["sel"] if press else P["accent"], press, 42)
        button(d, (560, 1300, 1032, 1420), "Back to Battle", P["muted"], False, 38)
        tap(img, 284, 1360, T_REMATCH, now)
    rnd = random.Random(7)

    def confetti(dd):
        for _ in range(40):
            x0 = rnd.uniform(0, W)
            sp = rnd.uniform(500, 900)
            y0 = -50 + (local * sp + rnd.uniform(0, 400)) % (H + 100) - 100
            col = rnd.choice([GOLD, P["accent"], P["success"], (255, 90, 120), WHITE])
            sz = rnd.uniform(10, 20)
            ang = local * rnd.uniform(2, 6)
            dx, dy = sz * math.cos(ang), sz * 0.5 * math.sin(ang)
            dd.polygon([(x0 - dx, y0 - dy), (x0 + dy, y0 - dx), (x0 + dx, y0 + dy), (x0 - dy, y0 + dx)], fill=col + (200,))
    if local > 0.2:
        overlay(img, confetti)
    return framed(img, now)


def sec_end(now):
    """End card: the game logo, then "Download it on the Play Store" and "It's FREE!"."""
    local = now - T_END
    img = base.end_bg().copy()
    s = back(local / 0.6)
    size = max(2, int(560 * s * (1 + 0.02 * math.sin(max(0.0, local - 0.6) * 4))))
    icon = Image.open(os.path.join(base.ASSETS, "icon.png")).convert("RGBA").resize((size, size), Image.LANCZOS)
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], int(size * 0.22), fill=255)
    icon.putalpha(m)
    paste(img, icon, W // 2 - size // 2, 760 - size // 2)
    t_dl, t_free = VOICES[-2][1], VOICES[-1][1]
    a = ease((now - t_dl + 0.15) / 0.3)
    if a > 0:
        def dl(d):
            d.text((W // 2, 1160), "Download it on", font=font("Medium", 58), fill=(205, 218, 255, int(255 * a)), anchor="mm")
            bw, bh, y0 = 700, 150, 1300
            d.rounded_rectangle([W // 2 - bw // 2, y0 - bh // 2, W // 2 + bw // 2, y0 + bh // 2], 34,
                                fill=(10, 10, 14, int(255 * a)), outline=(170, 170, 180, int(255 * a)), width=4)
            # Play-style triangle mark
            px, py = W // 2 - 250, y0
            d.polygon([(px - 34, py - 46), (px + 46, py), (px - 34, py + 46)], fill=(0, 220, 130, int(255 * a)))
            d.polygon([(px - 34, py - 46), (px + 6, py), (px - 34, py + 46)], fill=(0, 200, 255, int(255 * a)))
            d.text((W // 2 + 50, y0), "Play Store", font=font("Bold", 74), fill=(255, 255, 255, int(255 * a)), anchor="mm")
        overlay(img, dl)
    b = back((now - t_free + 0.1) / 0.35)
    if b > 0:
        sz = 120 * b * (1 + 0.04 * math.sin(max(0.0, now - t_free - 0.4) * 7))
        overlay(img, lambda d: d.text((W // 2, 1520), "It's FREE!", font=font("Bold", sz), fill=GOLD, anchor="mm",
                                      stroke_width=6, stroke_fill=(60, 30, 10)))
    return img


SECTIONS = [(0.0, sec_cafe), (T_LOBBY, sec_lobby), (T_GO, sec_go), (T_RACE, sec_race),
            (T_RESULTS, sec_results), (T_END, sec_end)]


def frame(n):
    now = n / FPS
    idx = max(i for i, (t0, _) in enumerate(SECTIONS) if now >= t0)
    img = SECTIONS[idx][1](now)
    t0 = SECTIONS[idx][0]
    if idx and now - t0 < 0.25:
        img = Image.blend(SECTIONS[idx - 1][1](t0 - 1e-3), img, ease((now - t0) / 0.25))
    return img


# ------------------------------------------------------------------ audio
def build_audio(path):
    SR = base.SR
    n = int(SR * DUR)
    out = np.zeros(n)
    t = np.arange(n) / SR

    def add(sig, at, gain=1.0):
        i = int(at * SR)
        m = min(len(sig), n - i)
        if m > 0:
            out[i:i + m] += gain * sig[:m]

    music = base.load_wav("music_calm")
    mus = np.zeros(n)
    k = 0
    while k < n:  # loop the music
        m = min(len(music), n - k)
        mus[k:k + m] = music[:m]
        k += m
    env = np.interp(t, [0, 0.4, DUR - 1.5, DUR], [0, 1, 1, 0])

    # voices, with the music ducked while someone speaks
    duck = np.ones(n)
    for lid, t0, who, t1 in VOICES:
        with wave.open(os.path.join(VOICE_DIR, f"{lid}-{who}.wav")) as w:
            assert w.getframerate() == SR
            v = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
        add(v / max(1e-9, np.abs(v).max()), t0, 0.95)
        a, b = int((t0 - 0.15) * SR), int((t1 + 0.2) * SR)
        duck[max(0, a):b] = 0.35
    duck = np.convolve(duck, np.ones(4410) / 4410, mode="same")
    out_music = 0.35 * mus * env * duck

    def sfx(name, at, gain=1.0):
        add(base.load_wav(name), at, gain)

    sfx("sfx_click", T_GO - 0.25, 1.0)
    sfx("sfx_hint", T_JOIN, 0.8)
    third = (T_RACE - T_GO - 0.5) / 3
    for j in range(3):
        sfx("sfx_click", T_GO + 0.5 + j * third, 1.0)
    sfx("sfx_complete", T_RACE - 0.05, 0.8)
    for j in range(24):
        sfx("sfx_number", T_RACE + 0.4 + j * (T_SOLVED - T_RACE - 0.6) / 24, 0.35)
    sfx("sfx_complete", T_SOLVED, 1.0)
    sfx("sfx_complete", T_RESULTS + 0.1, 0.8)
    sfx("sfx_click", T_REMATCH, 1.0)
    sfx("sfx_hint", T_END + 0.8, 0.7)
    out += out_music
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
            frame(int(float(ts) * FPS)).convert("RGB").save(f"story-{ts}.png")
    else:
        main()
