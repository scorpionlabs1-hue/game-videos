#!/usr/bin/env python3
"""Render a 30 s vertical (1080x1920) gameplay short for Sudoku - Original.

Timeline
  0.0 - 17.0  gameplay: the board from the store screenshot gets solved
 17.0 - 19.5  "Puzzle solved" celebration
 19.5 - 26.0  feature montage using the Play Store screenshots
 26.0 - 30.0  end card with icon and call to action

Audio (music, taps, error and success sounds) is synthesised, so there are
no licensing issues.

Usage: python3 render_short.py [output.mp4]
"""
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.dirname(HERE)
ASSETS = os.path.join(GAME, "assets")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(GAME, "exports", "short-30s-gameplay.mp4")

W, H, FPS, DUR = 1080, 1920, 30, 30.0
NFRAMES = int(FPS * DUR)
SR = 48000

FONT_DIR = "/usr/share/fonts/opentype/inter"
_fonts = {}


def font(weight, size):
    key = (weight, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(os.path.join(FONT_DIR, f"Inter-{weight}.otf"), size)
    return _fonts[key]


# Colours sampled from the in-game screenshot
BG = (13, 13, 21)
PANEL = (22, 29, 37)
CELL = (22, 29, 37)
CELL_HL = (30, 42, 62)
CELL_SAME = (38, 55, 83)
CELL_SEL = (35, 105, 235)
BORDER = (40, 110, 240)
GIVEN = (232, 232, 240)
USER = (95, 155, 255)
ERR = (240, 75, 85)
SCORE_BG = (20, 50, 110)
MUTED = (150, 155, 170)
GOLD = (255, 196, 40)

# Puzzle transcribed from the store screenshot (player entries removed).
PUZZLE = [
    "007003006",
    "504276380",
    "300085200",
    "261507800",
    "748030125",
    "005802764",
    "102760008",
    "079358602",
    "600900400",
]
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
    """Fill cells the way a player would: naked singles first."""
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


# ---------------------------------------------------------------- timeline
GAME_START, GAME_END = 0.6, 16.6
SOLVED_T, MONTAGE_T, END_T = 17.0, 19.5, 26.0
ORDER = solve_order()
MISTAKE_AT = 17  # index of the move that gets a wrong number first

events = []  # (time, kind, r, c, value)
moves = len(ORDER) + 2  # + wrong entry + erase
step = (GAME_END - GAME_START) / moves
t = GAME_START
for i, (r, c) in enumerate(ORDER):
    if i == MISTAKE_AT:
        wrong = next(v for v in range(1, 10) if v != SOLUTION[r][c] and v not in GRID0[r])
        events.append((t, "wrong", r, c, wrong))
        t += step * 1.4
        events.append((t, "erase", r, c, 0))
        t += step * 0.6
    events.append((t, "fill", r, c, SOLUTION[r][c]))
    t += step


def game_state(now):
    g = [r[:] for r in GRID0]
    wrong = None
    lives = 3
    score = 0
    last = None
    for et, kind, r, c, v in events:
        if et > now:
            break
        last = (et, kind, r, c, v)
        if kind == "fill":
            g[r][c] = v
            score += 15
            wrong = None
        elif kind == "wrong":
            wrong = (r, c, v)
            lives -= 1
        elif kind == "erase":
            wrong = None
    return g, wrong, lives, score, last


# ---------------------------------------------------------------- helpers
def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def ease_out_back(x):
    x = max(0.0, min(1.0, x))
    c1 = 1.70158
    return 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2


def text_c(d, xy, s, f, fill, anchor="mm", **kw):
    d.text(xy, s, font=f, fill=fill, anchor=anchor, **kw)


def heart(d, cx, cy, s, fill):
    r = s * 0.28
    d.ellipse([cx - 2 * r, cy - r * 1.6, cx, cy + r * 0.4], fill=fill)
    d.ellipse([cx, cy - r * 1.6, cx + 2 * r, cy + r * 0.4], fill=fill)
    d.polygon([(cx - 1.95 * r, cy - 0.35 * r), (cx + 1.95 * r, cy - 0.35 * r), (cx, cy + 1.9 * r)], fill=fill)


def star(d, cx, cy, R, fill, rot=0.0):
    pts = []
    for i in range(10):
        a = rot - math.pi / 2 + i * math.pi / 5
        rr = R if i % 2 == 0 else R * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)


def caption(img, s, alpha, y=150, size=76, color=(255, 255, 255), pill=BORDER):
    if alpha <= 0:
        return
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font("Black", size)
    box = d.textbbox((W // 2, y), s, font=f, anchor="mm")
    pad_x, pad_y = 40, 26
    a = int(255 * alpha)
    d.rounded_rectangle([box[0] - pad_x, box[1] - pad_y, box[2] + pad_x, box[3] + pad_y], 34,
                        fill=pill + (int(235 * alpha),))
    d.text((W // 2, y), s, font=f, fill=color + (a,), anchor="mm")
    img.alpha_composite(layer)


# ---------------------------------------------------------------- gameplay
BX, BY, BS = 36, 560, 1008  # board
CS = BS / 9


def cell_rect(r, c):
    gap, boxgap = 3, 7
    x0 = BX + c * CS + (boxgap if c % 3 == 0 else gap) / 2
    y0 = BY + r * CS + (boxgap if r % 3 == 0 else gap) / 2
    x1 = BX + (c + 1) * CS - (boxgap if c % 3 == 2 else gap) / 2
    y1 = BY + (r + 1) * CS - (boxgap if r % 3 == 2 else gap) / 2
    return [x0, y0, x1, y1]


def draw_game(now, solved_wave=None):
    img = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(img)
    g, wrong, lives, score, last = game_state(now)
    sel = (last[2], last[3]) if last else (8, 4)
    sel_val = g[sel[0]][sel[1]] or (wrong[2] if wrong else 0)

    # header
    d.ellipse([40, 300, 96, 356], outline=(200, 200, 210), width=4)
    d.line([(58, 328), (80, 328)], fill=(200, 200, 210), width=5)
    d.line([(58, 328), (69, 317)], fill=(200, 200, 210), width=5)
    d.line([(58, 328), (69, 339)], fill=(200, 200, 210), width=5)
    d.text((120, 300), "Sudoku", font=font("Bold", 50), fill=(240, 240, 248))
    d.text((124, 356), "O R I G I N A L", font=font("SemiBold", 20), fill=BORDER)
    for i, col in enumerate([(140, 80, 240), (235, 60, 90)]):
        x = 700 + i * 100
        d.rounded_rectangle([x, 300, x + 80, 380], 20, fill=col)
    heart(d, 840, 342, 40, (255, 255, 255))
    d.rounded_rectangle([722, 324, 758, 360], 6, fill=(255, 255, 255))
    d.ellipse([905, 300, 985, 380], fill=(55, 60, 75))
    for k in range(8):
        a = k * math.pi / 4
        d.line([(945, 340), (945 + 30 * math.cos(a), 340 + 30 * math.sin(a))], fill=(200, 205, 215), width=10)
    d.ellipse([929, 324, 961, 356], fill=(55, 60, 75))

    # stats row
    d.rounded_rectangle([36, 400, 1044, 480], 22, fill=PANEL)
    d.ellipse([60, 418, 100, 462], fill=(255, 120, 30))
    d.ellipse([68, 432, 92, 462], fill=(255, 210, 60))
    d.text((112, 412), "Streak", font=font("Medium", 20), fill=MUTED)
    d.text((112, 434), "5", font=font("Bold", 32), fill=(240, 240, 248))
    d.rounded_rectangle([300, 410, 720, 470], 14, fill=SCORE_BG)
    text_c(d, (510, 440), f"Score: {112 + score}", font("SemiBold", 32), (70, 140, 255))
    secs = int(55 + max(0.0, min(now, GAME_END + 0.3) - GAME_START) * 1.0)
    d.ellipse([740, 424, 772, 456], outline=(70, 140, 255), width=4)
    d.line([(756, 430), (756, 441), (764, 446)], fill=(70, 140, 255), width=3)
    d.text((782, 422), f"{secs // 60:02d}:{secs % 60:02d}", font=font("SemiBold", 32), fill=(240, 240, 248))
    d.rounded_rectangle([950, 412, 1030, 468], 14, fill=CELL_SEL)
    d.rectangle([976, 426, 984, 454], fill=(255, 255, 255))
    d.rectangle([996, 426, 1004, 454], fill=(255, 255, 255))

    # mistakes / difficulty
    d.text((40, 496), f"Mistakes {3 - lives}/3", font=font("Medium", 26), fill=MUTED)
    text_c(d, (540, 510), "Beginner", font("SemiBold", 28), (230, 230, 238))
    for i in range(3):
        col = (235, 50, 60) if i < lives else (60, 64, 78)
        heart(d, 60 + i * 52, 548, 46, col)
    d.text((760, 496), "Quick input", font=font("Medium", 26), fill=MUTED)
    d.rounded_rectangle([960, 494, 1040, 532], 19, fill=CELL_SEL)
    d.ellipse([1004, 497, 1036, 529], fill=(255, 255, 255))

    # board
    by = BY + 10
    d.rounded_rectangle([BX - 8, by - 8, BX + BS + 8, by + BS + 8], 18, fill=BG, outline=BORDER, width=5)
    sr, sc = sel
    for r in range(9):
        for c in range(9):
            rect = cell_rect(r, c)
            rect = [rect[0], rect[1] + 10, rect[2], rect[3] + 10]
            v = g[r][c]
            col = CELL
            if r == sr or c == sc or (r // 3 == sr // 3 and c // 3 == sc // 3):
                col = CELL_HL
            if sel_val and v == sel_val:
                col = CELL_SAME
            if (r, c) == sel and not solved_wave:
                col = CELL_SEL
                if wrong and (r, c) == (wrong[0], wrong[1]):
                    col = (95, 25, 38)
            if solved_wave is not None:
                k = solved_wave - (r + c) * 0.035
                if 0 < k < 0.45:
                    pulse = math.sin(k / 0.45 * math.pi)
                    col = tuple(int(CELL[i] + (BORDER[i] - CELL[i]) * pulse) for i in range(3))
                else:
                    col = CELL
            d.rectangle(rect, fill=col)
            cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
            if v:
                is_given = GRID0[r][c] != 0
                fcol = GIVEN if is_given else USER
                if (r, c) == sel and not solved_wave:
                    fcol = (255, 255, 255)
                size = 64
                if last and not is_given and (r, c) == (last[2], last[3]) and last[1] == "fill":
                    pop = now - last[0]
                    size = int(64 * (0.6 + 0.4 * ease_out_back(pop / 0.18)))
                text_c(d, (cx, cy + 2), str(v), font("SemiBold", size), fcol)
            elif wrong and (r, c) == (wrong[0], wrong[1]):
                shake = math.sin((now - last[0]) * 60) * 10 * max(0, 1 - (now - last[0]) / 0.4)
                text_c(d, (cx + shake, cy + 2), str(wrong[2]), font("SemiBold", 64), ERR)

    # tap ripple
    if last and not solved_wave:
        age = now - last[0]
        if age < 0.35:
            rect = cell_rect(last[2], last[3])
            cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2 + 10
            rad = 20 + age * 260
            a = int(160 * (1 - age / 0.35))
            layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(layer).ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=(255, 255, 255, a), width=6)
            img.alpha_composite(layer)
            d = ImageDraw.Draw(img)

    # tools
    ty = 1610
    tools = ["Undo", "Erase", "Pencil", "Hint"]
    for i, name in enumerate(tools):
        x0 = 36 + i * 256
        active = last and last[1] == "erase" and name == "Erase" and now - last[0] < 0.25
        d.rounded_rectangle([x0, ty, x0 + 240, ty + 120], 18, fill=CELL_SEL if active else PANEL)
        text_c(d, (x0 + 120, ty + 92), name, font("Medium", 26), (200, 205, 215))
    ic = (90, 150, 255)
    d.arc([126, 1626, 166, 1666], 200, 20, fill=ic, width=6)
    d.polygon([(118, 1636), (138, 1630), (128, 1652)], fill=ic)
    d.polygon([(390, 1660), (420, 1630), (440, 1650), (410, 1680)], fill=(220, 225, 240))
    d.polygon([(645, 1675), (650, 1655), (690, 1625), (700, 1635), (660, 1665)], fill=(120, 160, 255))
    d.ellipse([921, 1624, 951, 1654], fill=GOLD)
    d.rectangle([929, 1654, 943, 1664], fill=(200, 200, 210))
    d.ellipse([975, 1612, 1003, 1640], fill=CELL_SEL)
    text_c(d, (989, 1626), "2", font("Bold", 18), (255, 255, 255))

    # number pad
    py = 1760
    remaining = {v: 9 - sum(row.count(v) for row in g) for v in range(1, 10)}
    pressed = last[4] if last and last[1] in ("fill", "wrong") and now - last[0] < 0.2 else None
    for v in range(1, 10):
        x0 = 36 + (v - 1) * 112
        on = v == pressed
        d.rounded_rectangle([x0 + 4, py, x0 + 104, py + 140], 18, fill=CELL_SEL if on else PANEL)
        if remaining[v] > 0:
            text_c(d, (x0 + 54, py + 56), str(v), font("Bold", 62), (255, 255, 255) if on else (70, 140, 255))
            text_c(d, (x0 + 54, py + 116), str(remaining[v]), font("Medium", 22), (220, 225, 240) if on else MUTED)
        else:
            text_c(d, (x0 + 54, py + 70), "✓", font("Bold", 50), (60, 64, 78))
    return img


# ---------------------------------------------------------------- montage
_cache = {}


def load(name):
    if name not in _cache:
        _cache[name] = Image.open(os.path.join(ASSETS, name)).convert("RGBA")
    return _cache[name]


def gradient_bg():
    if "bg" not in _cache:
        y = np.linspace(0, 1, H)[:, None]
        top, bot = np.array([18, 40, 110]), np.array([8, 8, 18])
        arr = (top * (1 - y) + bot * y)[:, None, :].repeat(W, 1)
        img = Image.fromarray(arr.astype(np.uint8).reshape(H, W, 3)).convert("RGBA")
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse([140, 500, 940, 1500], fill=(40, 110, 240, 110))
        img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(160)))
        _cache["bg"] = img
    return _cache["bg"].copy()


def phone(shot, scale=1.0):
    key = ("phone", shot)
    if key not in _cache:
        pw, ph = 640, int(640 * 1600 / 722)
        screen = load(shot).resize((pw, ph), Image.LANCZOS)
        mask = Image.new("L", (pw, ph), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw, ph], 48, fill=255)
        frame = Image.new("RGBA", (pw + 36, ph + 36), (0, 0, 0, 0))
        ImageDraw.Draw(frame).rounded_rectangle([0, 0, pw + 35, ph + 35], 64, fill=(30, 32, 40, 255),
                                               outline=(80, 85, 100, 255), width=3)
        frame.paste(screen, (18, 18), mask)
        shadow = Image.new("RGBA", (frame.width + 160, frame.height + 160), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle([80, 100, frame.width + 80, frame.height + 100], 64, fill=(0, 0, 0, 170))
        shadow = shadow.filter(ImageFilter.GaussianBlur(40))
        shadow.alpha_composite(frame, (80, 80))
        _cache[key] = shadow
    p = _cache[key]
    if scale != 1.0:
        p = p.resize((int(p.width * scale), int(p.height * scale)), Image.LANCZOS)
    return p


MONTAGE = [
    ("store-1.jpg", "6 DIFFICULTY LEVELS", "Beginner to Extreme, plus 4×4 & 6×6"),
    ("store-2.jpg", "DAILY CHALLENGE", "A fresh puzzle every day"),
    ("store-4.jpg", "TRACK YOUR PROGRESS", "Streaks, stats & best times"),
]


def draw_montage(now):
    img = gradient_bg()
    seg = (END_T - MONTAGE_T) / len(MONTAGE)
    i = min(int((now - MONTAGE_T) / seg), len(MONTAGE) - 1)
    local = now - MONTAGE_T - i * seg
    shot, title, sub = MONTAGE[i]
    enter = ease_out_back(local / 0.45)
    scale = 0.96 + 0.04 * (local / seg)
    p = phone(shot, scale)
    x = int((W - p.width) / 2 + (1 - enter) * W)
    y = int(470 + (1 - ease(local / 0.45)) * 40)
    img.alpha_composite(p, (x, y))
    a = ease((local - 0.1) / 0.3)
    caption(img, title, a, y=200, size=72)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((W // 2, 320), sub, font=font("SemiBold", 44), fill=(220, 228, 255, int(255 * a)), anchor="mm")
    img.alpha_composite(layer)
    # Battle mode teaser on the last card
    return img


def draw_end(now):
    img = gradient_bg()
    local = now - END_T
    d = ImageDraw.Draw(img)
    # rotating rays
    rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rays)
    cx, cy = W // 2, 640
    for k in range(16):
        a0 = k * math.pi / 8 + local * 0.35
        rd.polygon([(cx, cy), (cx + 1400 * math.cos(a0), cy + 1400 * math.sin(a0)),
                    (cx + 1400 * math.cos(a0 + 0.12), cy + 1400 * math.sin(a0 + 0.12))], fill=(80, 140, 255, 28))
    img.alpha_composite(rays)
    s = ease_out_back(local / 0.6)
    size = max(1, int(520 * s))
    icon = load("icon.png").resize((size, size), Image.LANCZOS)
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size, size], int(size * 0.22), fill=255)
    icon.putalpha(m)
    img.alpha_composite(icon, (cx - size // 2, cy - size // 2))
    a = ease((local - 0.4) / 0.4)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.text((W // 2, 1010), "Sudoku – Original", font=font("Black", 84), fill=(255, 255, 255, int(255 * a)), anchor="mm")
    ld.text((W // 2, 1100), "Train your mind. Every day.", font=font("SemiBold", 46), fill=(200, 215, 255, int(255 * a)), anchor="mm")
    for k in range(5):
        star(ld, W // 2 - 160 + k * 80, 1200, 32, GOLD + (int(255 * a),))
    img.alpha_composite(layer)
    b = ease((local - 0.9) / 0.4)
    pulse = 1 + 0.04 * math.sin(max(0.0, local - 1.3) * 6)
    bw, bh = int(760 * pulse), int(150 * pulse)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    y0 = 1380
    ld.rounded_rectangle([cx - bw // 2, y0 - bh // 2, cx + bw // 2, y0 + bh // 2], bh // 2,
                         fill=(35, 105, 235, int(255 * b)))
    ld.text((cx, y0), "FREE on Google Play", font=font("Black", 58), fill=(255, 255, 255, int(255 * b)), anchor="mm")
    ld.text((cx, 1530), "Search “Sudoku Original”", font=font("Medium", 40), fill=(190, 200, 230, int(255 * b)), anchor="mm")
    img.alpha_composite(layer)
    return img


# ---------------------------------------------------------------- frames
GAME_CAPTIONS = [
    (0.0, 3.2, "CAN YOU SOLVE THIS?"),
    (3.2, events[MISTAKE_AT][0] - 0.1, "NO GUESSING. PURE LOGIC."),
    (events[MISTAKE_AT][0] - 0.1, events[MISTAKE_AT][0] + 2.6, "CAREFUL… ONLY 3 LIVES!"),
    (events[MISTAKE_AT][0] + 2.6, GAME_END + 0.2, "ALMOST THERE…"),
]


def frame(n):
    now = n / FPS
    if now < SOLVED_T:
        img = draw_game(now)
        for t0, t1, s in GAME_CAPTIONS:
            if t0 <= now < t1:
                a = ease((now - t0) / 0.2) * (1 - ease((now - (t1 - 0.2)) / 0.2))
                caption(img, s, a, pill=ERR if "CAREFUL" in s else BORDER)
        return img
    if now < MONTAGE_T:
        local = now - SOLVED_T
        img = draw_game(SOLVED_T, solved_wave=local)
        dim = Image.new("RGBA", img.size, (5, 8, 20, int(205 * ease((local - 0.55) / 0.3))))
        img.alpha_composite(dim)
        s = ease_out_back((local - 0.8) / 0.4)
        if s > 0:
            layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ld = ImageDraw.Draw(layer)
            for k in range(3):
                star(ld, W // 2 - 150 + k * 150, 800 - (40 if k == 1 else 0), (70 if k == 1 else 56) * s, GOLD, rot=local * 0.5)
            ld.text((W // 2, 990), "PUZZLE SOLVED!", font=font("Black", max(1, int(96 * s))), fill=(255, 255, 255), anchor="mm")
            secs = int(55 + GAME_END - GAME_START)
            ld.text((W // 2, 1100), f"Time {secs // 60:02d}:{secs % 60:02d}  •  Score {112 + 15 * len(ORDER)}",
                    font=font("SemiBold", max(1, int(48 * s))), fill=(200, 215, 255), anchor="mm")
            img.alpha_composite(layer)
        if local > MONTAGE_T - SOLVED_T - 0.25:
            k = (local - (MONTAGE_T - SOLVED_T - 0.25)) / 0.25
            img.alpha_composite(Image.new("RGBA", img.size, (0, 0, 0, int(255 * ease(k)))))
        return img
    if now < END_T:
        img = draw_montage(now)
        if now - MONTAGE_T < 0.25:
            img.alpha_composite(Image.new("RGBA", img.size, (0, 0, 0, int(255 * (1 - ease((now - MONTAGE_T) / 0.25))))))
        return img
    return draw_end(now)


# ---------------------------------------------------------------- audio
def synth_audio(path):
    n = int(SR * DUR)
    t = np.arange(n) / SR
    out = np.zeros(n)

    def note(f, start, length, amp, kind="pluck"):
        i0 = int(start * SR)
        m = min(int(length * SR), n - i0)
        if m <= 0:
            return
        tt = np.arange(m) / SR
        if kind == "pluck":
            env = np.exp(-tt * 5.0) * np.minimum(1, tt * 200)
            w = np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)
        else:  # pad
            env = np.minimum(1, tt / 0.4) * np.minimum(1, (length - tt) / 0.6)
            w = sum(np.sin(2 * np.pi * f * d * tt) for d in (1.0, 1.003, 0.997)) / 3
        out[i0:i0 + m] += amp * env * w

    def hz(semi):
        return 440 * 2 ** ((semi - 9) / 12)  # semitones from C4

    bpm = 100
    beat = 60 / bpm
    chords = [[0, 4, 7], [-5, -1, 2], [-3, 0, 4], [-7, -3, 0]]  # C G Am F
    bar = 4 * beat
    music_end = END_T + 4.0
    k = 0
    tt0 = 0.0
    while tt0 < music_end:
        ch = chords[k % 4]
        for s in ch:
            note(hz(s - 12), tt0, bar + 0.4, 0.05, "pad")
        note(hz(ch[0] - 24), tt0, bar, 0.08, "pluck")
        arp = ch + [ch[1] + 12]
        for j in range(8):
            note(hz(arp[j % 4] + 12), tt0 + j * beat / 2, beat, 0.035, "pluck")
        tt0 += bar
        k += 1
    fade = np.clip((DUR - t) / 1.5, 0, 1)
    out *= fade

    rng = np.random.default_rng(1)
    for et, kind, r, c, v in events:
        i0 = int(et * SR)
        m = int(0.06 * SR)
        tt = np.arange(m) / SR
        if kind == "fill":
            click = (np.sin(2 * np.pi * (900 + 40 * v) * tt) * np.exp(-tt * 70)
                     + 0.3 * rng.standard_normal(m) * np.exp(-tt * 200))
            out[i0:i0 + m] += 0.22 * click
        elif kind == "wrong":
            m = int(0.35 * SR)
            tt = np.arange(m) / SR
            buzz = np.sign(np.sin(2 * np.pi * 140 * tt)) * np.exp(-tt * 6)
            out[i0:i0 + m] += 0.12 * buzz
        elif kind == "erase":
            out[i0:i0 + m] += 0.1 * rng.standard_normal(m) * np.exp(-tt * 40)
    # success arpeggio
    for j, s in enumerate([0, 4, 7, 12, 16]):
        note(hz(s + 12), SOLVED_T + 0.05 + j * 0.09, 1.2, 0.18, "pluck")
    # montage whooshes
    seg = (END_T - MONTAGE_T) / len(MONTAGE)
    for i in range(len(MONTAGE) + 1):
        i0 = int((MONTAGE_T + i * seg) * SR)
        m = int(0.35 * SR)
        tt = np.arange(m) / SR
        noise = rng.standard_normal(m)
        noise = np.convolve(noise, np.ones(30) / 30, mode="same")
        out[i0:i0 + m] += 0.5 * noise * np.sin(np.pi * tt / 0.35) ** 2
    out = out / max(1e-9, np.abs(out).max()) * 0.85
    pcm = (out * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


def main():
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    wav = OUT + ".wav"
    synth_audio(wav)
    proc = subprocess.Popen([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", wav,
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "160k", "-ar", str(SR), "-ac", "2",
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
