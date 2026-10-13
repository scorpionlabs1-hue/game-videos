#!/usr/bin/env python3
"""Render the 30 s "what's new" gameplay short for Sudoku - Original (v2).

Built from the game's own source assets (copied into assets/game/): the 10 theme
palettes from ThemeCatalog.cs / ThemePalette.cs, the Roboto fonts, the action,
heart, Battle and Daily Challenge art, and the game's music and sound effects.

Timeline
  0.0 - 13.0  gameplay (Dark theme): a puzzle gets solved, with one mistake
 13.0 - 15.6  "Puzzle Complete!"
 15.6 - 19.6  NEW: 10 themes, the board cycles through every palette
 19.6 - 23.2  NEW: online Battle Mode, joining a room by code
 23.2 - 26.6  NEW: Daily Challenge progress rings and milestone trophies
 26.6 - 30.0  end card

Usage: python3 render_short_v2.py [output.mp4]
       PREVIEW=1.5,17,21 python3 render_short_v2.py   # writes preview PNGs instead
"""
import math
import os
import subprocess
import sys
import wave
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(HERE)
ASSETS = os.path.join(GAME, "assets")
GA = os.path.join(ASSETS, "game")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(GAME, "exports", "short-30s-whats-new.mp4")

W, H, FPS, DUR = 1080, 1920, 30, 30.0
NFRAMES = int(FPS * DUR)

T_SOLVED, T_THEMES, T_BATTLE, T_DAILY, T_END = 13.0, 15.6, 19.6, 23.2, 26.6
GAME_START, GAME_END = 0.5, 12.7


# ------------------------------------------------------------------ assets
@lru_cache(None)
def font(weight, size):
    return ImageFont.truetype(os.path.join(GA, "fonts", f"Roboto-{weight}.ttf"), max(1, int(size)))


@lru_cache(None)
def art(name, size=None):
    im = Image.open(os.path.join(GA, "art", name + ".png")).convert("RGBA")
    if size:
        w, h = size if isinstance(size, tuple) else (size, int(size * im.height / im.width))
        im = im.resize((w, h), Image.LANCZOS)
    return im


@lru_cache(None)
def tinted(name, size, color):
    im = art(name, size)
    solid = Image.new("RGBA", im.size, color + (255,))
    solid.putalpha(im.getchannel("A"))
    return solid


def hx(s):
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def pal(name, mode, bg, surface, muted, hero, accent, soft, text, text2, thin, thick,
        cell, peer, same, sel, cell_err, given, player, err_text, error, success):
    keys = dict(bg=bg, surface=surface, muted=muted, hero=hero, accent=accent, soft=soft, text=text,
                text2=text2, thin=thin, thick=thick, cell=cell, peer=peer, same=same, sel=sel,
                cell_err=cell_err, given=given, player=player, err_text=err_text, error=error, success=success)
    p = {k: hx(v) for k, v in keys.items()}
    p["name"], p["mode"] = name, mode
    return p


# Straight from Assets/Scripts/UI/ThemePalette.cs and ThemeCatalog.cs (picker order).
THEMES = [
    pal("Light", "light", "EFF3F9", "FFFFFF", "EAEFF7", "2A5C8C", "3A7BFD", "E7F0FF", "21304A", "7C8AA0", "DCE2EC", "35415C",
        "FEFEFE", "EAF0FA", "D2E1FD", "A2C4FF", "FFE0E1", "24324B", "2F6BE0", "D93B41", "E5484D", "1FA97C"),
    pal("Dark", "dark", "0B0E14", "161A22", "20242E", "1D3E5E", "2E6CF3", "17233B", "F2F5F9", "8B94A3", "2C313A", "6B7686",
        "1A1D24", "232936", "2A3550", "3A6FD0", "4A2328", "E8ECF2", "6BA5FF", "FF6B70", "FF5A5F", "34C48B"),
    pal("Ocean Blue", "dark", "0A1B30", "11304F", "183C60", "0F5D8C", "1797BA", "123F5E", "F2F9FF", "9CB9D3", "244A6E", "7DB7DC",
        "0E2742", "15375A", "1F5A88", "1C7298", "5A2238", "F4FAFF", "5FDDF7", "FF7B86", "FF6B78", "3DDC9A"),
    pal("Forest Green", "dark", "0C1F16", "163628", "1E4533", "1F6B47", "1E9E62", "1B4A35", "F4EFDD", "AFC4AE", "2A4B3B", "A8D4B2",
        "122C20", "1A3B2C", "2A6646", "2B7650", "5A2A26", "F6F1DE", "86E6AA", "FF8C7C", "FF7466", "5EDB8F"),
    pal("Sunset", "dark", "1D0F2E", "2E1A42", "3C2352", "8C3A5E", "E8672A", "4A2540", "FFF2E8", "D4B6C7", "46305B", "F3A675",
        "26153A", "33204A", "5E3066", "9C3F6D", "5E1C26", "FFF2E8", "FFB36E", "FF5E62", "FF5E62", "4FD39A"),
    pal("Royal Purple", "dark", "190E2C", "2A1A47", "35225A", "5B35B5", "8B5CF6", "3A2A63", "FFFFFF", "C5B7E2", "3D2C62", "D4AF5F",
        "21143C", "2D1D50", "4A3380", "6B4CC0", "521E3C", "FFFFFF", "F5C86B", "FF7D8F", "FF6B7D", "5ED3A0"),
    pal("Cherry", "dark", "230A12", "3A1420", "4A1C2B", "8E2440", "D63A5C", "52202F", "FFF0F3", "D9ACB6", "4E2231", "EBA0B0",
        "2E0F19", "44192A", "6E2A42", "9E2F4C", "5C3B12", "FFF0F3", "FFA3B5", "FFD166", "FF6B6B", "5CD6A0"),
    pal("Mint", "light", "E4F6EE", "FFFFFF", "DFF2E8", "17775A", "11825D", "D2F2E3", "12352A", "557A6C", "CBE3D7", "1F5A45",
        "FCFFFD", "E6F5EE", "B3E6CC", "7ED4AE", "FFE0E3", "12352A", "0A6A80", "D23A45", "DD4550", "1A9A70"),
    pal("Midnight", "dark", "04081A", "0C1530", "13204A", "2438A8", "3D5AFE", "141F52", "F5F8FF", "8FA0C6", "18264F", "5A8BFF",
        "08102A", "0F1C44", "1A3285", "2B47D9", "4A1830", "F5F8FF", "5FD2FF", "FF5C7A", "FF4D6A", "2EE59D"),
    pal("Classic Light", "light", "F3F3F3", "FFFFFF", "EEEEEE", "2F3A4A", "1E63D6", "E3ECFB", "1A1A1A", "616161", "CFCFCF", "1A1A1A",
        "FFFFFF", "EFEFEF", "C8DAF7", "9FC2F3", "FBDADB", "111111", "1C57C0", "C8232C", "D12F36", "1B8F60"),
]
DARK = THEMES[1]
GOLD = (255, 196, 40)
WHITE = (255, 255, 255)

# ------------------------------------------------------------------ puzzle
PUZZLE = ["007003006", "504276380", "300085200", "261507800", "748030125",
          "005802764", "102760008", "079358602", "600900400"]
GRID0 = [[int(c) for c in r] for r in PUZZLE]


def solve(g):
    g = [r[:] for r in g]

    def ok(r, c, v):
        if v in g[r] or any(g[i][c] == v for i in range(9)):
            return False
        br, bc = r // 3 * 3, c // 3 * 3
        return all(g[br + i][bc + j] != v for i in range(3) for j in range(3))

    def rec():
        for r in range(9):
            for c in range(9):
                if g[r][c] == 0:
                    for v in range(1, 10):
                        if ok(r, c, v):
                            g[r][c] = v
                            if rec():
                                return True
                            g[r][c] = 0
                    return False
        return True

    assert rec()
    return g


SOLUTION = solve(GRID0)


def candidates(g, r, c):
    used = set(g[r]) | {g[i][c] for i in range(9)}
    br, bc = r // 3 * 3, c // 3 * 3
    used |= {g[br + i][bc + j] for i in range(3) for j in range(3)}
    return [v for v in range(1, 10) if v not in used]


def solve_order():
    g = [r[:] for r in GRID0]
    order = []
    while True:
        empty = [(r, c) for r in range(9) for c in range(9) if g[r][c] == 0]
        if not empty:
            return order
        singles = [(r, c) for r, c in empty if len(candidates(g, r, c)) == 1]
        r, c = singles[0] if singles else empty[0]
        g[r][c] = SOLUTION[r][c]
        order.append((r, c))


ORDER = solve_order()
MISTAKE_AT = 15
EVENTS = []
_step = (GAME_END - GAME_START) / (len(ORDER) + 2)
_t = GAME_START
for _i, (_r, _c) in enumerate(ORDER):
    if _i == MISTAKE_AT:
        _wrong = next(v for v in range(1, 10) if v != SOLUTION[_r][_c] and v not in GRID0[_r])
        EVENTS.append((_t, "wrong", _r, _c, _wrong))
        _t += _step * 1.5
        EVENTS.append((_t, "erase", _r, _c, 0))
        _t += _step * 0.5
    EVENTS.append((_t, "fill", _r, _c, SOLUTION[_r][_c]))
    _t += _step
T_MISTAKE = EVENTS[MISTAKE_AT][0]


def game_state(now):
    g = [r[:] for r in GRID0]
    wrong, lives, score, last = None, 3, 0, None
    for ev in EVENTS:
        et, kind, r, c, v = ev
        if et > now:
            break
        last = ev
        if kind == "fill":
            g[r][c] = v
            score += 30
            wrong = None
        elif kind == "wrong":
            wrong, lives = (r, c, v), lives - 1
        else:
            wrong = None
    return g, wrong, lives, score, last


# ------------------------------------------------------------------ helpers
def clamp(x):
    return max(0.0, min(1.0, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def back(x):
    x = clamp(x)
    return 1 + 2.70158 * (x - 1) ** 3 + 1.70158 * (x - 1) ** 2


def mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def overlay(img, fn):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    fn(ImageDraw.Draw(layer))
    img.alpha_composite(layer)


def paste(img, im, x, y, alpha=1.0):
    if alpha < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda a: int(a * alpha)))
    img.alpha_composite(im, (int(x), int(y)))


def star(d, cx, cy, R, fill, rot=0.0):
    pts = []
    for i in range(10):
        a = rot - math.pi / 2 + i * math.pi / 5
        rr = R if i % 2 == 0 else R * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)


def caption(img, text, alpha, color, y=150):
    if alpha <= 0:
        return

    def draw(d):
        f = font("Bold", 70)
        b = d.textbbox((W // 2, y), text, font=f, anchor="mm")
        d.rounded_rectangle([b[0] - 42, b[1] - 28, b[2] + 42, b[3] + 28], 36, fill=color + (int(240 * alpha),))
        d.text((W // 2, y), text, font=f, fill=(255, 255, 255, int(255 * alpha)), anchor="mm")
    overlay(img, draw)


def switch(d, x, y, on, P):
    d.rounded_rectangle([x, y, x + 84, y + 44], 22, fill=P["accent"] if on else P["muted"])
    kx = x + 62 if on else x + 22
    d.ellipse([kx - 18, y + 4, kx + 18, y + 40], fill=WHITE)


# ------------------------------------------------------------------ game screen
BX, BY, BS = 36, 600, 1008
CS = BS / 9


def cell_rect(r, c):
    return [BX + c * CS, BY + r * CS, BX + (c + 1) * CS, BY + (r + 1) * CS]


def draw_game(now, P, solved_wave=None, freeze=None):
    t_state = freeze if freeze is not None else now
    img = Image.new("RGBA", (W, H), P["bg"] + (255,))
    d = ImageDraw.Draw(img)
    g, wrong, lives, score, last = game_state(t_state)
    sel = (last[2], last[3]) if last else (4, 3)
    sel_val = g[sel[0]][sel[1]] or (wrong[2] if wrong else 0)
    T, T2 = P["text"], P["text2"]

    # top bar
    paste(img, tinted("icon_back", 56, T), 36, 292)
    d.text((112, 280), "Sudoku", font=font("Bold", 54), fill=T)
    d.text((116, 344), "O R I G I N A L", font=font("Bold", 20), fill=P["accent"])
    for i, name in enumerate(["menu_themes", "menu_settings"]):
        x = 860 + i * 100
        m = Image.new("L", (84, 84), 0)
        ImageDraw.Draw(m).rounded_rectangle([0, 0, 83, 83], 22, fill=255)
        ic = art(name, 84).copy()
        ic.putalpha(m)
        paste(img, ic, x, 282)
    d.ellipse([760, 288, 832, 360], fill=P["surface"])
    heart = art("heart_full", 44)
    paste(img, heart, 774, 302)

    # stats pill
    d.rounded_rectangle([36, 392, 1044, 472], 24, fill=P["surface"])
    d.ellipse([60, 410, 100, 454], fill=(255, 122, 30))
    d.ellipse([69, 425, 91, 454], fill=(255, 212, 70))
    d.text((112, 402), "Streak", font=font("Medium", 20), fill=T2)
    d.text((112, 424), "5", font=font("Bold", 32), fill=T)
    d.rounded_rectangle([300, 402, 720, 462], 16, fill=P["soft"])
    d.text((510, 432), f"Score: {240 + score}", font=font("Bold", 32), fill=P["player"], anchor="mm")
    secs = int(64 + clamp((t_state - GAME_START) / 60) * 60)
    d.ellipse([742, 416, 774, 448], outline=P["accent"], width=4)
    d.line([(758, 422), (758, 433), (766, 438)], fill=P["accent"], width=3)
    d.text((786, 413), f"{secs // 60:02d}:{secs % 60:02d}", font=font("Bold", 32), fill=T)
    d.rounded_rectangle([952, 404, 1030, 460], 16, fill=P["accent"])
    d.rectangle([977, 418, 985, 446], fill=WHITE)
    d.rectangle([997, 418, 1005, 446], fill=WHITE)

    # difficulty divider and info row
    d.line([(330, 506), (440, 506)], fill=P["thin"], width=3)
    d.line([(640, 506), (750, 506)], fill=P["thin"], width=3)
    d.text((540, 506), "Medium", font=font("Bold", 30), fill=T, anchor="mm")
    d.text((40, 532), f"Mistakes {3 - lives}/3", font=font("Medium", 26), fill=T2)
    for i in range(3):
        h = art("heart_full" if i < lives else "heart_broken", 40)
        paste(img, h, 236 + i * 46, 528, 1.0 if i < lives else 0.55)
    d.text((660, 534), "Quick Input", font=font("Medium", 26), fill=T2)
    switch(d, 818, 530, False, P)
    d.ellipse([948, 520, 1036, 584], fill=P["surface"])
    paste(img, art("action_hint", 44), 970, 530)

    # board
    d.rounded_rectangle([BX - 6, BY - 6, BX + BS + 6, BY + BS + 6], 16, fill=P["thick"])
    sr, sc = sel
    for r in range(9):
        for c in range(9):
            x0, y0, x1, y1 = cell_rect(r, c)
            v = g[r][c]
            col = P["cell"]
            if r == sr or c == sc or (r // 3 == sr // 3 and c // 3 == sc // 3):
                col = P["peer"]
            if sel_val and v == sel_val:
                col = P["same"]
            if (r, c) == sel and solved_wave is None:
                col = P["sel"]
                if wrong and (r, c) == wrong[:2]:
                    col = P["cell_err"]
            if solved_wave is not None:
                k = solved_wave - (r + c) * 0.035
                col = mix(P["cell"], P["accent"], math.sin(k / 0.45 * math.pi)) if 0 < k < 0.45 else P["cell"]
            gl = 1.5 if c % 3 else 3.5
            gr = 1.5 if c % 3 != 2 else 3.5
            gt = 1.5 if r % 3 else 3.5
            gb = 1.5 if r % 3 != 2 else 3.5
            d.rectangle([x0 + gl, y0 + gt, x1 - gr, y1 - gb], fill=col)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            if v:
                given = GRID0[r][c] != 0
                fc = P["given"] if given else P["player"]
                size = 66
                if last and last[1] == "fill" and not given and (r, c) == last[2:4]:
                    size = 66 * (0.55 + 0.45 * back((t_state - last[0]) / 0.18))
                d.text((cx, cy + 2), str(v), font=font("Regular" if given else "Medium", size), fill=fc, anchor="mm")
            elif wrong and (r, c) == wrong[:2]:
                age = t_state - last[0]
                shake = math.sin(age * 60) * 10 * clamp(1 - age / 0.4)
                d.text((cx + shake, cy + 2), str(wrong[2]), font=font("Medium", 66), fill=P["err_text"], anchor="mm")
    # board lines over cells
    for i in range(10):
        w_ = 5 if i % 3 == 0 else 2
        colr = P["thick"] if i % 3 == 0 else P["thin"]
        d.line([(BX + i * CS, BY), (BX + i * CS, BY + BS)], fill=colr, width=w_)
        d.line([(BX, BY + i * CS), (BX + BS, BY + i * CS)], fill=colr, width=w_)

    if last and solved_wave is None and freeze is None:
        age = now - last[0]
        if age < 0.35:
            x0, y0, x1, y1 = cell_rect(last[2], last[3])
            cx, cy, rad = (x0 + x1) / 2, (y0 + y1) / 2, 20 + age * 260
            a = int(170 * (1 - age / 0.35))
            overlay(img, lambda dd: dd.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=(255, 255, 255, a), width=6))
            d = ImageDraw.Draw(img)

    # action row (real art)
    ty = 1634
    for i, (name, label) in enumerate([("action_undo", "Undo"), ("action_erase", "Erase"),
                                       ("action_pencil", "Pencil"), ("action_hint", "Hint")]):
        x0 = 36 + i * 256
        active = freeze is None and last and last[1] == "erase" and label == "Erase" and now - last[0] < 0.25
        d.rounded_rectangle([x0, ty, x0 + 240, ty + 118], 20, fill=P["accent"] if active else P["surface"])
        paste(img, art(name, 60), x0 + 90, ty + 10)
        d.text((x0 + 120, ty + 94), label, font=font("Medium", 26), fill=WHITE if active else T2, anchor="mm")
    d.ellipse([948, ty + 2, 980, ty + 34], fill=P["accent"])
    d.text((964, ty + 18), "2", font=font("Bold", 20), fill=WHITE, anchor="mm")

    # number pad
    py = 1770
    remaining = {v: 9 - sum(row.count(v) for row in g) for v in range(1, 10)}
    pressed = last[4] if freeze is None and last and last[1] in ("fill", "wrong") and now - last[0] < 0.2 else None
    for v in range(1, 10):
        x0 = 36 + (v - 1) * 112
        on = v == pressed
        if remaining[v] > 0 or on:
            d.rounded_rectangle([x0 + 4, py, x0 + 104, py + 128], 18, fill=P["accent"] if on else P["surface"])
            d.text((x0 + 54, py + 54), str(v), font=font("Medium", 64), fill=WHITE if on else P["accent"], anchor="mm")
            d.text((x0 + 54, py + 108), str(max(0, remaining[v])), font=font("Medium", 22), fill=WHITE if on else T2, anchor="mm")
    return img


# ------------------------------------------------------------------ sections
def sec_game(now):
    img = draw_game(now, DARK)
    caps = [(0.0, 3.0, "CAN YOU SOLVE THIS?", DARK["accent"]),
            (3.0, T_MISTAKE - 0.1, "NO GUESSING. PURE LOGIC.", DARK["accent"]),
            (T_MISTAKE - 0.1, T_MISTAKE + 2.4, "CAREFUL… ONLY 3 LIVES!", DARK["error"]),
            (T_MISTAKE + 2.4, T_SOLVED, "ALMOST THERE…", DARK["accent"])]
    for t0, t1, s, col in caps:
        if t0 <= now < t1:
            caption(img, s, ease((now - t0) / 0.2) * (1 - ease((now - t1 + 0.2) / 0.2)), col)
    return img


def sec_solved(now):
    local = now - T_SOLVED
    img = draw_game(T_SOLVED, DARK, solved_wave=local)
    overlay(img, lambda d: d.rectangle([0, 0, W, H], fill=(0, 0, 0, int(165 * ease((local - 0.55) / 0.3)))))
    s = back((local - 0.7) / 0.4)
    if s > 0:
        def draw(d):
            for k in range(3):
                star(d, W // 2 - 150 + k * 150, 760 - (40 if k == 1 else 0), (72 if k == 1 else 56) * s, GOLD, rot=local * 0.4)
            d.text((W // 2, 950), "Puzzle Complete!", font=font("Bold", 100 * s), fill=DARK["success"], anchor="mm")
            secs = 64 + int(GAME_END - GAME_START)
            d.text((W // 2, 1060), f"Medium  •  {secs // 60:02d}:{secs % 60:02d}  •  New best time!",
                   font=font("Medium", 44 * s), fill=(220, 228, 240), anchor="mm")
        overlay(img, draw)
    return img


def sec_themes(now):
    local = now - T_THEMES
    per = (T_BATTLE - T_THEMES - 0.4) / len(THEMES)
    i = min(int(max(0.0, local - 0.2) / per), len(THEMES) - 1)
    P = THEMES[i]
    img = draw_game(now, P, freeze=GAME_START + (GAME_END - GAME_START) * 0.62)
    # theme swatch sheet over the number pad
    def draw(d):
        d.rounded_rectangle([24, 1600, 1056, 1912], 40, fill=P["surface"] + (250,), outline=P["thin"], width=2)
        d.text((W // 2, 1660), P["name"], font=font("Bold", 52), fill=P["text"], anchor="mm")
        for k, Q in enumerate(THEMES):
            cx = 84 + k * 101
            cy = 1790
            if k == i:
                d.ellipse([cx - 46, cy - 46, cx + 46, cy + 46], outline=P["accent"], width=7)
            d.ellipse([cx - 36, cy - 36, cx + 36, cy + 36], fill=Q["bg"], outline=Q["thick"], width=3)
            d.pieslice([cx - 36, cy - 36, cx + 36, cy + 36], 200, 340, fill=Q["accent"])
            d.ellipse([cx - 14, cy - 2, cx + 14, cy + 26], fill=Q["player"])
        d.text((W // 2, 1876), "Switch any time, even mid-game", font=font("Medium", 30), fill=P["text2"], anchor="mm")
    overlay(img, draw)
    caption(img, "NEW: 10 BEAUTIFUL THEMES", ease(local / 0.25), P["accent"])
    return img


CODE = "K7QM4X"


def nav_bar(img, active, P):
    d = ImageDraw.Draw(img)
    d.rectangle([0, 1740, W, H], fill=P["surface"])
    for k, (name, label) in enumerate([("home", "Home"), ("challenges", "Challenges"), ("battle", "Battle"), ("profile", "Profile")]):
        cx = 135 + k * 270
        on = name == active
        paste(img, art(name, 110 if on else 96), cx - (55 if on else 48), 1752 if on else 1760, 1.0 if on else 0.75)
        d.text((cx, 1888), label, font=font("Bold" if on else "Medium", 28), fill=P["accent"] if on else P["text2"], anchor="mm")


def sec_battle(now):
    P = DARK
    local = now - T_BATTLE
    img = Image.new("RGBA", (W, H), P["bg"] + (255,))
    d = ImageDraw.Draw(img)
    d.text((48, 290), "Battle", font=font("Bold", 76), fill=P["text"])
    d.text((50, 390), "Race other players. Solve first. Win the battle.", font=font("Medium", 34), fill=P["text2"])
    hero = art("hero_card", (984, 577)).copy()
    m = Image.new("L", hero.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, hero.width - 1, hero.height - 1], 40, fill=255)
    hero.putalpha(m)
    paste(img, hero, 48, 460)
    overlay(img, lambda dd: dd.rounded_rectangle([88, 500, 300, 556], 28, fill=(0, 0, 0, 90)))
    d = ImageDraw.Draw(img)
    d.ellipse([110, 518, 130, 538], fill=P["success"])
    d.text((142, 528), "ONLINE", font=font("Bold", 28), fill=WHITE, anchor="lm")
    d.text((90, 880), "Same puzzle. Same clock.", font=font("Bold", 52), fill=WHITE)
    d.text((90, 950), "Who solves it first?", font=font("Medium", 40), fill=(215, 220, 255))

    # Create Battle
    by = 1080
    d.rounded_rectangle([48, by, 1032, by + 128], 30, fill=P["accent"])
    paste(img, tinted("icon_plus", 52, WHITE), 330, by + 38)
    d.text((W // 2 + 30, by + 64), "Create Battle", font=font("Bold", 46), fill=WHITE, anchor="mm")

    # Join card with the code being typed
    jy = 1250
    d.rounded_rectangle([48, jy, 1032, jy + 440], 34, fill=P["surface"])
    paste(img, tinted("icon_people", 56, P["accent"]), 88, jy + 36)
    d.text((166, jy + 64), "Join a Battle", font=font("Bold", 44), fill=P["text"], anchor="lm")
    d.text((88, jy + 120), "Enter the 6-character room code", font=font("Medium", 30), fill=P["text2"])
    n = int(clamp((local - 0.5) / 1.3) * len(CODE) + 0.001)
    for k in range(6):
        x0 = 88 + k * 150
        filled = k < n
        d.rounded_rectangle([x0, jy + 180, x0 + 128, jy + 300], 20, fill=P["muted"],
                            outline=P["accent"] if k == n else P["thin"], width=4)
        if filled:
            d.text((x0 + 64, jy + 242), CODE[k], font=font("Bold", 64), fill=P["text"], anchor="mm")
    ready = n == len(CODE)
    press = 2.05 < local < 2.25
    d.rounded_rectangle([88, jy + 330, 992, jy + 412], 24, fill=(P["accent"] if ready else P["muted"]) if not press else P["sel"])
    d.text((W // 2, jy + 371), "Join", font=font("Bold", 40), fill=WHITE if ready else P["text2"], anchor="mm")
    nav_bar(img, "battle", P)

    if local > 2.3:
        k = ease((local - 2.3) / 0.2)

        def busy(dd):
            dd.rectangle([0, 0, W, H], fill=(0, 0, 0, int(170 * k)))
            dd.rounded_rectangle([240, 820, 840, 1100], 36, fill=P["surface"] + (int(255 * k),))
            for j in range(12):
                a = j * math.pi / 6 + local * 6
                alpha = int(255 * k * (0.25 + 0.75 * ((j / 12 + local * 0.95) % 1)))
                dd.line([(540 + 26 * math.cos(a), 910 + 26 * math.sin(a)),
                         (540 + 46 * math.cos(a), 910 + 46 * math.sin(a))], fill=P["accent"] + (alpha,), width=8)
            dd.text((W // 2, 1020), "Joining battle…", font=font("Bold", 42), fill=P["text"] + (int(255 * k),), anchor="mm")
        overlay(img, busy)
    caption(img, "NEW: ONLINE BATTLE MODE", ease(local / 0.25), P["accent"])
    return img


def sec_daily(now):
    P = DARK
    local = now - T_DAILY
    img = Image.new("RGBA", (W, H), P["bg"] + (255,))
    hero = art("daily_hero_bg", (W, 960))
    paste(img, hero, 0, 0)
    d = ImageDraw.Draw(img)
    paste(img, tinted("icon_back", 56, WHITE), 40, 290)
    d.text((120, 318), "Daily Challenge", font=font("Bold", 50), fill=WHITE, anchor="lm")
    paste(img, tinted("icon_trophy", 60, WHITE), 970, 288)
    d.text((70, 430), "2026", font=font("Medium", 34), fill=(225, 240, 255))
    d.text((66, 470), "October", font=font("Bold", 84), fill=WHITE)
    done = int(clamp((local - 0.2) / 1.6) * 12)
    d.rounded_rectangle([70, 580, 250, 640], 30, fill=(0, 0, 0, 60))
    overlay(img, lambda dd: dd.rounded_rectangle([70, 580, 250, 640], 30, fill=(0, 30, 60, 90)))
    d = ImageDraw.Draw(img)
    star(d, 104, 610, 18, GOLD)
    d.text((132, 610), f"{done}/31", font=font("Bold", 32), fill=WHITE, anchor="lm")
    tr = art("trophy_gold_02", 300)
    bob = math.sin(local * 3) * 8
    paste(img, tr, 700, 380 + bob)

    # sheet
    sy = 720
    d.rounded_rectangle([0, sy, W, H + 60], 56, fill=P["surface"])
    # 3-game challenge bar with milestone trophies
    d.text((60, sy + 70), "3-Game Challenge", font=font("Bold", 40), fill=P["text"], anchor="lm")
    games = min(3, int(clamp((local - 0.4) / 1.8) * 3 + 0.0001))
    d.text((1020, sy + 70), f"{games}/3", font=font("Bold", 40), fill=P["text"], anchor="rm")
    for k, medal in enumerate(["milestone_bronze", "milestone_silver", "milestone_gold"]):
        x0 = 60 + k * 320
        d.rounded_rectangle([x0, sy + 140, x0 + 260, sy + 160], 10, fill=P["muted"])
        if k < games:
            d.rounded_rectangle([x0, sy + 140, x0 + 260, sy + 160], 10, fill=GOLD)
        on = k < games
        size = 96 if on else 80
        if on:
            age = local - (0.4 + 1.8 * (k + 1) / 3)
            size = int(80 + 30 * math.sin(clamp(age / 0.35) * math.pi) + 16)
        paste(img, art(medal, size), x0 + 270 - size // 2 + 10, sy + 150 - size // 2, 1.0 if on else 0.35)

    # calendar with progress rings
    gy = sy + 250
    for k, dname in enumerate(["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]):
        d.text((96 + k * 148, gy), dname, font=font("Bold", 26), fill=P["text2"], anchor="mm")
    first = 4  # 1 Oct 2026 is a Thursday
    for day in range(1, 32):
        idx = first + day - 1
        cx, cy = 96 + (idx % 7) * 148, gy + 80 + (idx // 7) * 120
        if day <= 12:
            k = clamp((local - 0.2 - (day - 1) * 0.12) / 0.3)
            d.ellipse([cx - 44, cy - 44, cx + 44, cy + 44], outline=P["muted"], width=8)
            if k > 0:
                d.arc([cx - 44, cy - 44, cx + 44, cy + 44], -90, -90 + 360 * k, fill=P["success"], width=8)
            if k >= 1:
                d.ellipse([cx - 32, cy - 32, cx + 32, cy + 32], fill=P["accent"])
            d.text((cx, cy), str(day), font=font("Bold", 36), fill=WHITE if k >= 1 else P["text"], anchor="mm")
        elif day == 13:
            d.ellipse([cx - 44, cy - 44, cx + 44, cy + 44], outline=P["accent"], width=6)
            d.text((cx, cy), "13", font=font("Bold", 36), fill=P["accent"], anchor="mm")
        else:
            d.text((cx, cy), str(day), font=font("Medium", 34), fill=P["text2"], anchor="mm")

    # trophy room strip
    ry = 1690
    d.text((60, ry), "Trophy Room", font=font("Bold", 38), fill=P["text"], anchor="lm")
    for k, t in enumerate(["trophy_gold_06", "trophy_gold_07", "trophy_gold_10"]):
        a = ease((local - 1.6 - k * 0.2) / 0.3)
        sz = int(150 * (0.6 + 0.4 * back((local - 1.6 - k * 0.2) / 0.35)))
        paste(img, art(t, max(1, sz)), 520 + k * 180 - sz // 2, ry + 10 - sz // 2 + 70, a)
    caption(img, "NEW: DAILY TROPHIES", ease(local / 0.25), P["accent"])
    return img


@lru_cache(None)
def end_bg():
    y = np.linspace(0, 1, H)[:, None]
    top, bot = np.array([18, 40, 110]), np.array([7, 9, 14])
    arr = (top * (1 - y) + bot * y)[:, None, :].repeat(W, 1).reshape(H, W, 3)
    img = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([140, 300, 940, 1100], fill=(46, 108, 243, 120))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(150)))
    return img


def sec_end(now):
    local = now - T_END
    img = end_bg().copy()
    cx, cy = W // 2, 600

    def rays(d):
        for k in range(16):
            a0 = k * math.pi / 8 + local * 0.35
            d.polygon([(cx, cy), (cx + 1400 * math.cos(a0), cy + 1400 * math.sin(a0)),
                       (cx + 1400 * math.cos(a0 + 0.12), cy + 1400 * math.sin(a0 + 0.12))], fill=(90, 150, 255, 26))
    overlay(img, rays)
    s = back(local / 0.55)
    size = max(2, int(480 * s))
    icon = Image.open(os.path.join(ASSETS, "icon.png")).convert("RGBA").resize((size, size), Image.LANCZOS)
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], int(size * 0.22), fill=255)
    icon.putalpha(m)
    paste(img, icon, cx - size // 2, cy - size // 2)
    a = ease((local - 0.35) / 0.4)

    def text(d):
        d.text((cx, 950), "Sudoku – Original", font=font("Bold", 86), fill=(255, 255, 255, int(255 * a)), anchor="mm")
        d.text((cx, 1035), "Train your mind. Every day.", font=font("Medium", 44), fill=(205, 218, 255, int(255 * a)), anchor="mm")
        chips = ["10 Themes", "Online Battles", "Daily Trophies", "Cloud Save"]
        f = font("Bold", 34)
        widths = [d.textlength(c, font=f) + 56 for c in chips]
        rows = [chips[:2], chips[2:]]
        y = 1140
        idx = 0
        for row in rows:
            tot = sum(widths[idx:idx + len(row)]) + 20 * (len(row) - 1)
            x = cx - tot / 2
            for c in row:
                k = ease((local - 0.6 - idx * 0.12) / 0.3)
                w_ = widths[idx]
                d.rounded_rectangle([x, y, x + w_, y + 70], 35, fill=(46, 108, 243, int(90 * k)),
                                    outline=(120, 165, 255, int(255 * k)), width=3)
                d.text((x + w_ / 2, y + 35), c, font=f, fill=(255, 255, 255, int(255 * k)), anchor="mm")
                x += w_ + 20
                idx += 1
            y += 90
    overlay(img, text)
    b = ease((local - 1.2) / 0.4)
    pulse = 1 + 0.04 * math.sin(max(0.0, local - 1.6) * 6)
    bw, bh = int(780 * pulse), int(150 * pulse)

    def button(d):
        y0 = 1480
        d.rounded_rectangle([cx - bw // 2, y0 - bh // 2, cx + bw // 2, y0 + bh // 2], bh // 2, fill=(46, 108, 243, int(255 * b)))
        d.text((cx, y0), "FREE on Google Play", font=font("Bold", 60), fill=(255, 255, 255, int(255 * b)), anchor="mm")
        d.text((cx, 1630), "Search “Sudoku Original”", font=font("Medium", 40), fill=(190, 200, 230, int(255 * b)), anchor="mm")
    overlay(img, button)
    return img


SECTIONS = [(0.0, sec_game), (T_SOLVED, sec_solved), (T_THEMES, sec_themes),
            (T_BATTLE, sec_battle), (T_DAILY, sec_daily), (T_END, sec_end)]
XFADE = 0.22


def frame(n):
    now = n / FPS
    idx = max(i for i, (t0, _) in enumerate(SECTIONS) if now >= t0)
    img = SECTIONS[idx][1](now)
    t0 = SECTIONS[idx][0]
    if idx >= 2 and now - t0 < XFADE:  # crossfade from the previous section
        prev = SECTIONS[idx - 1][1](t0 - 1e-3)
        img = Image.blend(prev, img, ease((now - t0) / XFADE))
    return img


# ------------------------------------------------------------------ audio
SR = 44100


def load_wav(name):
    with wave.open(os.path.join(GA, "audio", name + ".wav")) as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
        if w.getnchannels() == 2:
            data = data.reshape(-1, 2).mean(1)
        assert w.getframerate() == SR
    return data


def build_audio(path):
    n = int(SR * DUR)
    out = np.zeros(n)
    music = load_wav("music_calm")[:n]
    env = np.ones(len(music))
    fade_in, fade_out = int(0.3 * SR), int(2.0 * SR)
    env[:fade_in] = np.linspace(0, 1, fade_in)
    env[-fade_out:] = np.linspace(1, 0, fade_out)
    out[:len(music)] += 0.55 * music * env

    def add(name, t, gain=1.0):
        s = load_wav(name)
        i0 = int(t * SR)
        m = min(len(s), n - i0)
        if m > 0:
            out[i0:i0 + m] += gain * s[:m]

    for et, kind, *_ in EVENTS:
        add({"fill": "sfx_number", "wrong": "sfx_error", "erase": "sfx_click"}[kind], et, 0.9)
    add("sfx_complete", T_SOLVED + 0.05, 1.0)
    per = (T_BATTLE - T_THEMES - 0.4) / len(THEMES)
    for k in range(len(THEMES)):
        add("sfx_click", T_THEMES + 0.2 + k * per, 0.9)
    for k in range(len(CODE)):
        add("sfx_click", T_BATTLE + 0.5 + (k + 1) * 1.3 / len(CODE) - 0.05, 0.9)
    add("sfx_number", T_BATTLE + 2.1, 0.9)
    for k in range(3):
        add("sfx_hint", T_DAILY + 0.4 + 1.8 * (k + 1) / 3, 0.7)
    add("sfx_complete", T_END + 0.1, 0.6)
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
    for n in range(NFRAMES):
        proc.stdin.write(frame(n).convert("RGB").tobytes())
        if n % 150 == 0:
            print(f"frame {n}/{NFRAMES}", flush=True)
    proc.stdin.close()
    proc.wait()
    os.remove(wav)
    if proc.returncode:
        sys.exit(proc.returncode)
    print("Wrote", OUT)


if __name__ == "__main__":
    if os.environ.get("PREVIEW"):
        for ts in os.environ["PREVIEW"].split(","):
            frame(int(float(ts) * FPS)).convert("RGB").save(f"preview-{ts}.png")
    else:
        main()
