#!/usr/bin/env python3
"""Render a 30 s Battle Mode video for Sudoku - Original.

Follows the real Battle flow from the game (BattleUI / BattleGameHUD / the Battle
scene builder): Battle home -> Create Battle -> lobby with a 6-character room code
where friends join and get ready -> synchronized GET READY 3-2-1 GO -> the race
with live standings -> results -> end card. Reuses the game screen, palettes, art
and sounds from render_short_v2.py.

Usage: python3 render_battle.py [output.mp4]
       PREVIEW=1,4,8,11,15,23,28 python3 render_battle.py
"""
import math
import os
import random
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw

_argv, sys.argv = sys.argv, sys.argv[:1]
import render_short_v2 as base  # noqa: E402
sys.argv = _argv

from render_short_v2 import (DARK, GOLD, WHITE, art, back, clamp, draw_game,  # noqa: E402
                             ease, font, nav_bar, overlay, paste, star, tinted)

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base.GAME, "exports", "battle-30s.mp4")
W, H, FPS, DUR = base.W, base.H, 30, 30.0
NFRAMES = int(FPS * DUR)
P = DARK
T = P["text"]
T2 = P["text2"]

T_CREATE, T_LOBBY, T_GO, T_RACE, T_RESULTS, T_END = 2.6, 6.2, 11.6, 13.6, 22.6, 26.4
CODE = "B7K4P9"
BATTLE_NAME = "Friday Night Battle"
PLAYERS = [("You", "lion"), ("Alex", "fox"), ("Priya", "panda"), ("Sam", "owl")]
JOIN_AT = [0.0, 1.6, 2.3, 3.0]      # lobby-local join times
READY_AT = [0.0, 2.6, 3.2, 3.7]     # lobby-local ready times
FINISH = {"You": 161, "Alex": 178, "Priya": 200, "Sam": 223}  # finish times in seconds

# ------------------------------------------------------------------ race state
ORDER = base.ORDER
PREFILL = 16
race_events = [(-5.0, "fill", r, c, base.SOLUTION[r][c]) for r, c in ORDER[:PREFILL]]
_rest = ORDER[PREFILL:]
_step = (T_RESULTS - 1.0 - (T_RACE + 0.4)) / len(_rest)
for i, (r, c) in enumerate(_rest):
    race_events.append((T_RACE + 0.4 + i * _step, "fill", r, c, base.SOLUTION[r][c]))
T_SOLVED = race_events[-1][0]
base.EVENTS = race_events
base.GAME_START = -60.0


def progress(name, now):
    """Share of the board filled, 0..1, for each racer."""
    if name == "You":
        done = sum(1 for e in race_events if 0 <= e[0] <= now)
        return 0.38 + 0.62 * done / len(_rest)
    speed = {"Alex": 0.95, "Priya": 0.83, "Sam": 0.74}[name]
    k = clamp((now - T_RACE) / (T_SOLVED - T_RACE))
    surge = 0.09 * math.sin(math.pi * k) if name == "Alex" else 0.0  # Alex leads mid-race
    return min(0.98, 0.38 + 0.62 * k * speed + surge + 0.015 * math.sin(now * 3 + len(name)))


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
        d.rounded_rectangle([W / 2 - w / 2 - 42, top - lh / 2 - 22, W / 2 + w / 2 + 42,
                             top + lh * (len(lines) - 0.5) + 22], 38, fill=color + (int(240 * alpha),))
        for i, l in enumerate(lines):
            d.text((W / 2, top + i * lh), l, font=f, fill=(255, 255, 255, int(255 * alpha)), anchor="mm")
    overlay(img, draw)


def cap_at(img, now, t0, t1, text, color=None):
    if t0 <= now < t1:
        caption(img, text, ease((now - t0) / 0.2) * (1 - ease((now - t1 + 0.2) / 0.2)), color or P["accent"])


def avatar(name, size):
    im = art(f"avatar_{name}", (size, size)).copy()
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse([0, 0, size - 1, size - 1], fill=255)
    im.putalpha(m)
    return im


def tap(img, x, y, t_tap, now):
    """Translucent fingertip that presses at (x, y) around t_tap."""
    if t_tap - 0.45 <= now <= t_tap + 0.25:
        k = ease((now - (t_tap - 0.45)) / 0.35)
        yy = y + 160 * (1 - k)
        r = 46 * (1 - 0.25 * math.sin(clamp((now - t_tap + 0.1) / 0.2) * math.pi))
        overlay(img, lambda d: d.ellipse([x - r, yy - r, x + r, yy + r], fill=(255, 255, 255, 90),
                                         outline=(255, 255, 255, 210), width=5))


def page(title, back_arrow=True):
    img = Image.new("RGBA", (W, H), P["bg"] + (255,))
    d = ImageDraw.Draw(img)
    if back_arrow:
        paste(img, tinted("icon_back", 56, T), 40, 292)
    d.text((120 if back_arrow else 48, 320), title, font=font("Bold", 60), fill=T, anchor="lm")
    return img, d


def button(d, box, label, fill, pressed=False, size=44):
    x0, y0, x1, y1 = box
    if pressed:
        x0, y0, x1, y1 = x0 + 6, y0 + 4, x1 - 6, y1 - 4
    d.rounded_rectangle([x0, y0, x1, y1], (y1 - y0) // 2 if y1 - y0 < 120 else 30, fill=fill)
    d.text(((x0 + x1) / 2, (y0 + y1) / 2), label, font=font("Bold", size), fill=WHITE, anchor="mm")


def chips(d, x, y, labels, selected, w=290, h=84, gap=16, per_row=3):
    for i, lab in enumerate(labels):
        cx = x + (i % per_row) * (w + gap)
        cy = y + (i // per_row) * (h + gap)
        on = lab == selected
        d.rounded_rectangle([cx, cy, cx + w, cy + h], 22, fill=P["accent"] if on else P["muted"])
        d.text((cx + w / 2, cy + h / 2), lab, font=font("Bold" if on else "Medium", 34),
               fill=WHITE if on else T2, anchor="mm")


# ------------------------------------------------------------------ sections
def sec_home(now):
    img = Image.new("RGBA", (W, H), P["bg"] + (255,))
    d = ImageDraw.Draw(img)
    d.text((48, 290), "Battle", font=font("Bold", 76), fill=T)
    d.text((50, 390), "Race other players. Solve first. Win the battle.", font=font("Medium", 34), fill=T2)
    hero = art("hero_card", (984, 577)).copy()
    m = Image.new("L", hero.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, hero.width - 1, hero.height - 1], 40, fill=255)
    hero.putalpha(m)
    paste(img, hero, 48, 460)
    overlay(img, lambda dd: dd.rounded_rectangle([88, 500, 300, 556], 28, fill=(0, 0, 0, 90)))
    d = ImageDraw.Draw(img)
    d.ellipse([110, 518, 130, 538], fill=P["success"])
    d.text((142, 528), "ONLINE", font=font("Bold", 28), fill=WHITE, anchor="lm")
    d.text((90, 880), "Multiplayer Sudoku", font=font("Bold", 52), fill=WHITE)
    d.text((90, 950), "Same puzzle for everyone.", font=font("Medium", 40), fill=(215, 220, 255))
    by = 1080
    pressed = T_CREATE - 0.35 < now < T_CREATE - 0.1
    button(d, (48, by, 1032, by + 128), "", P["sel"] if pressed else P["accent"], pressed)
    paste(img, tinted("icon_plus", 52, WHITE), 330, by + 38)
    d.text((W // 2 + 30, by + 64), "Create Battle", font=font("Bold", 46), fill=WHITE, anchor="mm")
    jy = 1250
    d.rounded_rectangle([48, jy, 1032, jy + 300], 34, fill=P["surface"])
    paste(img, tinted("icon_people", 56, P["accent"]), 88, jy + 36)
    d.text((166, jy + 64), "Join a Battle", font=font("Bold", 44), fill=T, anchor="lm")
    d.rounded_rectangle([88, jy + 130, 992, jy + 240], 24, fill=P["muted"])
    d.text((128, jy + 185), "Enter 6-character code", font=font("Medium", 36), fill=T2, anchor="lm")
    nav_bar(img, "battle", P)
    tap(img, W // 2, by + 64, T_CREATE - 0.25, now)
    cap_at(img, now, 0.0, T_CREATE, "CHALLENGE YOUR\nFRIENDS ONLINE")
    return img


def sec_create(now):
    local = now - T_CREATE
    img, d = page("Create Battle")
    y = 420
    d.text((60, y), "BATTLE NAME", font=font("Bold", 28), fill=T2)
    d.rounded_rectangle([48, y + 44, 1032, y + 144], 24, fill=P["surface"], outline=P["accent"], width=3)
    n = int(clamp(local / 1.0) * len(BATTLE_NAME))
    cursor = "|" if int(now * 3) % 2 == 0 and n < len(BATTLE_NAME) else ""
    d.text((84, y + 94), BATTLE_NAME[:n] + cursor, font=font("Medium", 40), fill=T, anchor="lm")
    y = 620
    d.text((60, y), "PLAYERS", font=font("Bold", 28), fill=T2)
    d.rounded_rectangle([48, y + 44, 1032, y + 164], 24, fill=P["surface"])
    players = 2 + min(2, int(clamp((local - 1.0) / 0.8) * 2 + 0.001))
    for k, (sx, glyph) in enumerate([(120, "−"), (960, "+")]):
        pressed = k == 1 and any(abs(local - t) < 0.12 for t in (1.4, 1.8))
        d.ellipse([sx - 44, y + 60, sx + 44, y + 148], fill=P["sel"] if pressed else P["muted"])
        d.text((sx, y + 102), glyph, font=font("Bold", 56), fill=T, anchor="mm")
    d.text((W // 2, y + 92), str(players), font=font("Bold", 64), fill=T, anchor="mm")
    d.text((W // 2, y + 140), "2–6 players, including you", font=font("Medium", 24), fill=T2, anchor="mm")
    y = 840
    d.text((60, y), "DIFFICULTY", font=font("Bold", 28), fill=T2)
    sel = "Medium" if local > 2.0 else "Easy"
    chips(d, 48, y + 44, ["Beginner", "Easy", "Medium", "Hard", "Expert", "Extreme"], sel, w=318)
    y = 1100
    d.text((60, y), "BOARD", font=font("Bold", 28), fill=T2)
    chips(d, 48, y + 44, ["4×4", "6×6", "9×9"], "9×9", w=318)
    y = 1260
    d.text((60, y), "TIME LIMIT", font=font("Bold", 28), fill=T2)
    chips(d, 48, y + 44, ["Off", "5 min", "10 min"], "Off", w=318)
    press = T_LOBBY - 0.35 < now < T_LOBBY - 0.1
    button(d, (48, 1480, 1032, 1608), "Create Battle", P["sel"] if press else P["accent"], press, 46)
    tap(img, 960, y=y - 1260 + 620 + 104, t_tap=T_CREATE + 1.4, now=now)
    tap(img, 960, 620 + 104, T_CREATE + 1.8, now)
    tap(img, 48 + 318 * 2 + 16 * 2 + 159, 840 + 44 + 42, T_CREATE + 2.0, now)
    tap(img, W // 2, 1544, T_LOBBY - 0.25, now)
    cap_at(img, now, T_CREATE, T_LOBBY, "CREATE A ROOM\nIN SECONDS")
    return img


def sec_lobby(now):
    local = now - T_LOBBY
    img, d = page("Battle Room")
    # room card
    d.rounded_rectangle([48, 410, 1032, 820], 40, fill=P["hero"])
    overlay(img, lambda dd: dd.rounded_rectangle([48, 410, 1032, 820], 40, outline=P["accent"] + (255,), width=4))
    d = ImageDraw.Draw(img)
    d.text((W // 2, 470), BATTLE_NAME, font=font("Bold", 40), fill=WHITE, anchor="mm")
    d.text((W // 2, 528), "ROOM CODE", font=font("Bold", 26), fill=(190, 210, 240), anchor="mm")
    pop = 1 + 0.06 * math.sin(clamp((local - 0.9) / 0.3) * math.pi)
    for k, ch in enumerate(CODE):
        cx = W // 2 - 5 * 66 + k * 132
        d.rounded_rectangle([cx - 56, 560, cx + 56, 680], 20, fill=(0, 0, 0, 0) if False else P["bg"])
        d.text((cx, 620), ch, font=font("Bold", int(80 * pop)), fill=WHITE, anchor="mm")
    d.text((W // 2, 712), "Medium  ·  9×9  ·  No time limit", font=font("Medium", 30), fill=(200, 215, 240), anchor="mm")
    copy_p = 0.75 < local < 0.95
    share_p = 1.25 < local < 1.45
    button(d, (88, 740, 520, 800), "Copy Code", P["sel"] if copy_p else P["accent"], copy_p, 32)
    button(d, (560, 740, 992, 800), "Share Battle", P["sel"] if share_p else P["accent"], share_p, 32)
    # player list
    joined = [i for i, t in enumerate(JOIN_AT) if local >= t]
    d.text((60, 880), f"PLAYERS  {len(joined)}/4", font=font("Bold", 30), fill=T2, anchor="lm")
    for i in joined:
        name, av = PLAYERS[i]
        k = back((local - JOIN_AT[i]) / 0.35) if i else 1.0
        y = 930 + i * 150
        x = 48 + (1 - k) * W
        d.rounded_rectangle([x, y, x + 984, y + 130], 30, fill=P["surface"])
        paste(img, avatar(av, 96), x + 20, y + 17)
        d.text((x + 140, y + 65), name + ("  (host)" if i == 0 else ""), font=font("Bold", 40), fill=T, anchor="lm")
        ready = local >= READY_AT[i]
        pill = P["success"] if ready else P["muted"]
        d.rounded_rectangle([x + 760, y + 37, x + 960, y + 93], 28, fill=pill)
        d.text((x + 860, y + 65), "READY" if ready else "JOINED", font=font("Bold", 28), fill=WHITE, anchor="mm")
    all_ready = len(joined) == 4 and local >= READY_AT[-1]
    cap = "Everyone's ready!" if all_ready else "Waiting for players to join…"
    d.text((W // 2, 1560), cap, font=font("Medium", 34), fill=P["success"] if all_ready else T2, anchor="mm")
    press = T_GO - 0.35 < now < T_GO - 0.1
    button(d, (48, 1610, 1032, 1738), "START BATTLE", (P["sel"] if press else P["accent"]) if all_ready else P["muted"], press, 48)
    if 0.95 < local < 2.0:
        a = ease((local - 0.95) / 0.15) * (1 - ease((local - 1.8) / 0.2))

        def toast(dd):
            dd.rounded_rectangle([290, 1420, 790, 1500], 40, fill=(30, 34, 44, int(240 * a)))
            dd.text((W // 2, 1460), "Room code copied", font=font("Medium", 34), fill=(255, 255, 255, int(255 * a)), anchor="mm")
        overlay(img, toast)
    tap(img, 304, 770, T_LOBBY + 0.85, now)
    tap(img, W // 2, 1674, T_GO - 0.25, now)
    cap_at(img, now, T_LOBBY, T_LOBBY + 1.6, "SHARE THE CODE")
    cap_at(img, now, T_LOBBY + 1.6, T_GO, "FRIENDS JOIN\nFROM ANYWHERE", P["success"])
    return img


def battle_bar(img, now):
    """Battle bar that replaces the stats pill: clock + live standings (never answers)."""
    d = ImageDraw.Draw(img)
    d.rectangle([20, 380, 1060, 588], fill=P["bg"])
    d.rounded_rectangle([36, 388, 1044, 584], 26, fill=P["surface"])
    secs = 95 + int(max(0.0, now - T_RACE) * 8)
    if now >= T_SOLVED:
        secs = FINISH["You"]
    d.text((70, 420), "BATTLE", font=font("Bold", 24), fill=P["accent"], anchor="lm")
    d.text((70, 470), f"{secs // 60:02d}:{secs % 60:02d}", font=font("Bold", 52), fill=T, anchor="lm")
    d.text((70, 530), "Medium · 9×9", font=font("Medium", 24), fill=T2, anchor="lm")
    order = sorted(PLAYERS, key=lambda p: -progress(p[0], now))
    for rank, (name, av) in enumerate(order):
        x = 290 + rank * 188
        me = name == "You"
        d.rounded_rectangle([x, 404, x + 176, 568], 20, fill=P["soft"] if me else P["muted"],
                            outline=P["accent"] if me else None, width=3)
        d.text((x + 22, 432), f"{rank + 1}", font=font("Bold", 30), fill=GOLD if rank == 0 else T, anchor="mm")
        paste(img, avatar(av, 64), x + 56, 408)
        d.text((x + 88, 498), name, font=font("Bold", 28), fill=T, anchor="mm")
        pr = progress(name, now)
        done = me and now >= T_SOLVED
        label = "Solved!" if done else f"{int(pr * 100)}%"
        d.rounded_rectangle([x + 16, 518, x + 160, 534], 8, fill=P["bg"])
        d.rounded_rectangle([x + 16, 518, x + 16 + 144 * pr, 534], 8, fill=P["success"] if done else P["accent"])
        d.text((x + 88, 551), label, font=font("Medium", 22), fill=T2, anchor="mm")


def sec_go(now):
    local = now - T_GO
    img = draw_game(T_RACE, P, freeze=T_RACE)
    battle_bar(img, T_RACE)
    overlay(img, lambda d: d.rectangle([0, 590, W, 1910], fill=P["bg"] + (240,)))
    third = (T_RACE - T_GO - 0.5) / 3

    def draw(d):
        if local < 0.5:
            d.text((W // 2, 1000), "GET READY", font=font("Bold", 110), fill=T, anchor="mm")
            d.text((W // 2, 1100), "Same puzzle for everyone.", font=font("Medium", 44), fill=T2, anchor="mm")
        else:
            k = local - 0.5
            n = 3 - int(k / third)
            kk = (k % third) / third
            label = str(n) if n >= 1 else "GO!"
            size = 340 * (1.2 - 0.3 * ease(kk / 0.4))
            col = P["success"] if n < 1 else WHITE
            d.text((W // 2, 1050), label, font=font("Bold", size), fill=col + (int(255 * (1 - ease((kk - 0.75) / 0.25))),), anchor="mm")
    overlay(img, draw)
    caption(img, "SAME PUZZLE.\nSAME CLOCK.", ease(local / 0.2), P["accent"])
    return img


def sec_race(now):
    img = draw_game(now, P)
    battle_bar(img, now)
    if now >= T_SOLVED:
        local = now - T_SOLVED
        overlay(img, lambda d: d.rectangle([0, 590, W, H], fill=(0, 0, 0, int(150 * ease(local / 0.3)))))
        s = back(local / 0.35)

        def draw(d):
            d.text((W // 2, 1050), "Solved!", font=font("Bold", max(1, int(130 * s))), fill=P["success"], anchor="mm")
            d.text((W // 2, 1160), "Checking your solution with the battle…", font=font("Medium", max(1, int(36 * s))),
                   fill=(220, 228, 240), anchor="mm")
        overlay(img, draw)
    cap_at(img, now, T_RACE, T_RACE + 4.2, "LIVE STANDINGS")
    cap_at(img, now, T_RACE + 4.2, T_RESULTS, "THEY SEE YOUR SPEED,\nNEVER YOUR ANSWERS")
    return img


def sec_results(now):
    local = now - T_RESULTS
    img, d = page("Final Results", back_arrow=False)
    s = back(local / 0.45)
    tr = art("trophy_gold_02", max(2, int(300 * s)))
    paste(img, tr, W // 2 - tr.width // 2, 560 - tr.height // 2 + math.sin(local * 3) * 6)
    a = ease((local - 0.3) / 0.3)

    def head(dd):
        dd.text((W // 2, 780), "YOU WON!", font=font("Bold", 110), fill=GOLD + (int(255 * a),), anchor="mm")
        dd.text((W // 2, 870), "Fastest of 4 players", font=font("Medium", 42), fill=T2 + (int(255 * a),), anchor="mm")
    overlay(img, head)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([48, 930, 1032, 1070], 30, fill=P["surface"])
    for k, (lab, val) in enumerate([("YOUR TIME", "02:41"), ("PLACE", "1st"), ("PLAYERS", "4")]):
        cx = 212 + k * 328
        d.text((cx, 975), lab, font=font("Bold", 24), fill=T2, anchor="mm")
        d.text((cx, 1030), val, font=font("Bold", 48), fill=T, anchor="mm")
    for i, (name, av) in enumerate(PLAYERS):
        k = back((local - 0.5 - i * 0.15) / 0.35)
        if k <= 0:
            continue
        y = 1100 + i * 130
        x = 48 + (1 - k) * W
        me = name == "You"
        d.rounded_rectangle([x, y, x + 984, y + 112], 28, fill=P["soft"] if me else P["surface"])
        medal = [GOLD, (200, 205, 215), (205, 127, 50)][i] if i < 3 else P["muted"]
        d.ellipse([x + 22, y + 26, x + 82, y + 86], fill=medal)
        d.text((x + 52, y + 56), str(i + 1), font=font("Bold", 34), fill=(30, 30, 30) if i < 3 else T, anchor="mm")
        paste(img, avatar(av, 80), x + 104, y + 16)
        d.text((x + 210, y + 56), name, font=font("Bold", 40), fill=T, anchor="lm")
        t = FINISH[name]
        d.text((x + 950, y + 56), f"{t // 60:02d}:{t % 60:02d}", font=font("Bold", 40), fill=T, anchor="rm")
    b = ease((local - 1.3) / 0.3)
    if b > 0:
        button(d, (48, 1640, 520, 1760), "Rematch", P["accent"], size=42)
        button(d, (560, 1640, 1032, 1760), "Back to Battle", P["muted"], size=38)
    # confetti
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
    cap_at(img, now, T_RESULTS, T_END, "WIN THE BATTLE!", P["success"])
    return img


def sec_end(now):
    local = now - T_END
    img = base.end_bg().copy()
    cx = W // 2
    a = ease(local / 0.35)

    def head(d):
        for i, line in enumerate(["CHALLENGE", "YOUR FRIENDS"]):
            sz = 100 * (0.8 + 0.2 * back((local - i * 0.12) / 0.4))
            d.text((cx, 300 + i * 120), line, font=font("Bold", sz), fill=(255, 255, 255, int(255 * a)), anchor="mm")
        d.text((cx, 520), "Online Battle Mode", font=font("Medium", 54), fill=(205, 218, 255, int(255 * a)), anchor="mm")
    overlay(img, head)
    s = back((local - 0.2) / 0.5)
    size = max(2, int(300 * s))
    sw = art("battle", (size, size)).copy()
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], int(size * 0.22), fill=255)
    sw.putalpha(m)
    paste(img, sw, cx - 230 - size // 2, 820 - size // 2)
    icon = Image.open(os.path.join(base.ASSETS, "icon.png")).convert("RGBA").resize((size, size), Image.LANCZOS)
    icon.putalpha(m)
    paste(img, icon, cx + 230 - size // 2, 820 - size // 2)
    b = ease((local - 0.7) / 0.35)
    pulse = 1 + 0.04 * math.sin(max(0.0, local - 1.1) * 6)
    bw, bh = int(780 * pulse), int(150 * pulse)

    def cta(d):
        d.text((cx, 820), "VS", font=font("Bold", 80), fill=GOLD + (int(255 * min(1, max(0, s))),), anchor="mm")
        d.text((cx, 1100), "Sudoku – Original", font=font("Bold", 76), fill=(255, 255, 255, int(255 * b)), anchor="mm")
        y0 = 1330
        d.rounded_rectangle([cx - bw // 2, y0 - bh // 2, cx + bw // 2, y0 + bh // 2], bh // 2, fill=(46, 108, 243, int(255 * b)))
        d.text((cx, y0), "PLAY FREE", font=font("Bold", 66), fill=(255, 255, 255, int(255 * b)), anchor="mm")
        d.text((cx, 1490), "on Google Play", font=font("Medium", 44), fill=(190, 200, 230, int(255 * b)), anchor="mm")
    overlay(img, cta)
    return img


SECTIONS = [(0.0, sec_home), (T_CREATE, sec_create), (T_LOBBY, sec_lobby), (T_GO, sec_go),
            (T_RACE, sec_race), (T_RESULTS, sec_results), (T_END, sec_end)]


def frame(n):
    now = n / FPS
    idx = max(i for i, (t0, _) in enumerate(SECTIONS) if now >= t0)
    img = SECTIONS[idx][1](now)
    t0 = SECTIONS[idx][0]
    if idx and now - t0 < 0.22:
        img = Image.blend(SECTIONS[idx - 1][1](t0 - 1e-3), img, ease((now - t0) / 0.22))
    return img


# ------------------------------------------------------------------ audio
def build_audio(path):
    SR = base.SR
    n = int(SR * DUR)
    out = np.zeros(n)
    music = base.load_wav("music_calm")[:n]
    env = np.ones(len(music))
    env[:int(0.3 * SR)] = np.linspace(0, 1, int(0.3 * SR))
    i0, i1 = int(T_GO * SR), int(T_RACE * SR)
    env[i0:i1] = 0.35   # drop the music under the countdown
    env[-int(1.5 * SR):] *= np.linspace(1, 0, int(1.5 * SR))
    out[:len(music)] += 0.5 * music * env

    def add(name, t, gain=1.0):
        s = base.load_wav(name)
        i = int(t * SR)
        m = min(len(s), n - i)
        if m > 0:
            out[i:i + m] += gain * s[:m]

    for t in (T_CREATE - 0.25, T_CREATE + 1.4, T_CREATE + 1.8, T_CREATE + 2.0, T_LOBBY - 0.25,
              T_LOBBY + 0.85, T_LOBBY + 1.35, T_GO - 0.25):
        add("sfx_click", t, 0.9)
    for k in range(int(len(BATTLE_NAME) / 2)):
        add("sfx_click", T_CREATE + k * 2 / len(BATTLE_NAME), 0.35)
    for t in JOIN_AT[1:]:
        add("sfx_number", T_LOBBY + t, 0.8)
    for t in READY_AT[1:]:
        add("sfx_hint", T_LOBBY + t, 0.5)
    third = (T_RACE - T_GO - 0.5) / 3
    for k in range(3):
        add("sfx_click", T_GO + 0.5 + k * third, 1.0)
        add("sfx_number", T_GO + 0.5 + k * third, 0.7)
    add("sfx_complete", T_RACE - 0.05, 0.7)
    for e in race_events:
        if e[0] > 0:
            add("sfx_number", e[0], 0.8)
    add("sfx_complete", T_SOLVED + 0.05, 1.0)
    add("sfx_complete", T_RESULTS + 0.1, 0.8)
    add("sfx_hint", T_END + 0.7, 0.7)
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
            frame(int(float(ts) * FPS)).convert("RGB").save(f"battle-{ts}.png")
    else:
        main()
