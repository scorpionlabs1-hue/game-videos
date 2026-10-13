#!/usr/bin/env python3
"""Build the Instagram profile kit for @scorpion__labs / Sudoku - Original.

Writes to games/sudoku-original/instagram/:
  profile-picture.png      1080x1080, padded for the circle crop
  highlight-*.png          1080x1920 story covers (the icon sits in the centre circle)
  post-1..6-*.png          1080x1350 (4:5) launch grid posts
Reuses the game screen, palettes and art from render_short_v2.py.
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

_argv, sys.argv = sys.argv, sys.argv[:1]
import render_short_v2 as base  # noqa: E402
sys.argv = _argv
from render_short_v2 import DARK, GOLD, THEMES, WHITE, art, font, overlay, paste, star, tinted  # noqa: E402

OUT = os.path.join(base.GAME, "instagram")
os.makedirs(OUT, exist_ok=True)
BLUE = (46, 108, 243)
NAVY = (11, 14, 20)


def gradient(w, h, top=(18, 40, 110), bot=(7, 9, 14), glow=True):
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img, "RGBA")
    for y in range(h):
        k = y / (h - 1)
        d.line([(0, y), (w, y)], fill=tuple(int(top[i] * (1 - k) + bot[i] * k) for i in range(3)) + (255,))
    if glow:
        g = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse([w * 0.1, h * 0.12, w * 0.9, h * 0.62], fill=BLUE + (110,))
        img.alpha_composite(g.filter(ImageFilter.GaussianBlur(w // 7)))
    return img


def rounded(im, radius):
    im = im.copy()
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius, fill=255)
    im.putalpha(Image.composite(im.getchannel("A"), m, m) if im.mode == "RGBA" else m)
    return im


def icon(size):
    im = Image.open(os.path.join(base.ASSETS, "icon.png")).convert("RGBA").resize((size, size), Image.LANCZOS)
    return rounded(im, int(size * 0.22))


def text_c(d, xy, s, size, fill=WHITE, weight="Bold", **kw):
    d.text(xy, s, font=font(weight, size), fill=fill, anchor="mm", **kw)


def pill(d, cx, cy, s, size=40, fill=BLUE, pad=36):
    f = font("Bold", size)
    w = d.textlength(s, font=f)
    d.rounded_rectangle([cx - w / 2 - pad, cy - size * 0.95, cx + w / 2 + pad, cy + size * 0.95], size, fill=fill)
    d.text((cx, cy), s, font=f, fill=WHITE, anchor="mm")


def footer(img, d, y=1270):
    paste(img, icon(64), 60, y - 32)
    d.text((140, y), "Sudoku – Original", font=font("Bold", 34), fill=WHITE, anchor="lm")
    d.text((1020, y), "Free on Google Play", font=font("Medium", 30), fill=(190, 205, 240), anchor="rm")


def phone_shot(img_rgba, width):
    """A game-screen frame inside a simple phone bezel, scaled to `width`."""
    scr = img_rgba.resize((width, int(width * img_rgba.height / img_rgba.width)), Image.LANCZOS)
    scr = rounded(scr, int(width * 0.06))
    pad = int(width * 0.035)
    frame = Image.new("RGBA", (scr.width + 2 * pad, scr.height + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(frame).rounded_rectangle([0, 0, frame.width - 1, frame.height - 1], int(width * 0.09),
                                            fill=(28, 30, 38, 255), outline=(80, 86, 100, 255), width=3)
    frame.alpha_composite(scr, (pad, pad))
    sh = Image.new("RGBA", (frame.width + 120, frame.height + 120), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([60, 80, frame.width + 60, frame.height + 80], int(width * 0.09), fill=(0, 0, 0, 170))
    sh = sh.filter(ImageFilter.GaussianBlur(30))
    sh.alpha_composite(frame, (60, 60))
    return sh


def game_frame(P=DARK, t=8.0):
    return base.draw_game(t, P, freeze=t)


# ------------------------------------------------------------------ profile picture
def profile_picture():
    img = gradient(1080, 1080)
    paste(img, icon(760), 160, 160)
    img.convert("RGB").save(os.path.join(OUT, "profile-picture.png"))


# ------------------------------------------------------------------ highlight covers
HIGHLIGHTS = [
    ("play", "Play", None),
    ("battle", "Battle", "battle"),
    ("themes", "Themes", "menu_themes"),
    ("daily", "Daily", "trophy_gold_02"),
    ("tips", "Tips", "action_hint"),
]


def highlights():
    for key, label, name in HIGHLIGHTS:
        img = gradient(1080, 1920, top=(22, 52, 140), bot=(8, 12, 30))
        d = ImageDraw.Draw(img, "RGBA")
        overlay(img, lambda dd: dd.ellipse([240, 660, 840, 1260], fill=(255, 255, 255, 28), outline=(255, 255, 255, 90), width=6))
        if name is None:
            paste(img, icon(380), 350, 770)
        elif name in ("battle", "menu_themes"):
            im = rounded(art(name, 380), 80)
            paste(img, im, 350, 770)
        else:
            im = art(name, 400)
            paste(img, im, 340, 760)
        text_c(d, (540, 1400), label.upper(), 64, fill=(220, 230, 255))
        img.convert("RGB").save(os.path.join(OUT, f"highlight-{key}.png"))


# ------------------------------------------------------------------ posts (1080x1350)
def post_intro():
    img = gradient(1080, 1350)
    d = ImageDraw.Draw(img, "RGBA")
    text_c(d, (540, 150), "MEET", 52, fill=(170, 195, 255))
    text_c(d, (540, 240), "Sudoku – Original", 92)
    paste(img, icon(520), 280, 340)
    text_c(d, (540, 950), "The classic number puzzle,", 46, weight="Medium", fill=(215, 225, 250))
    text_c(d, (540, 1010), "made for your phone.", 46, weight="Medium", fill=(215, 225, 250))
    for i, s in enumerate(["6 levels", "Daily puzzles", "Online battles"]):
        pill(d, 200 + i * 340, 1130, s, 32, fill=(46, 108, 243))
    footer(img, d)
    return img


def post_themes():
    img = gradient(1080, 1350, top=(40, 20, 70), bot=(8, 8, 18))
    d = ImageDraw.Draw(img, "RGBA")
    text_c(d, (540, 120), "10 BEAUTIFUL THEMES", 76)
    text_c(d, (540, 200), "Pick your vibe. Switch any time, even mid-game.", 36, weight="Medium", fill=(215, 205, 240))
    picks = [THEMES[1], THEMES[2], THEMES[4], THEMES[7]]
    for i, P in enumerate(picks):
        crop = game_frame(P).crop((0, 250, 1080, 1630))
        ph = phone_shot(crop, 290)
        x = 110 + (i % 2) * 470
        y = 225 + (i // 2) * 490
        paste(img, ph, x, y)
        pill(d, x + ph.width // 2, y + 500, P["name"], 28, fill=P["accent"])
    footer(img, d)
    return img


def post_battle():
    img = gradient(1080, 1350, top=(40, 30, 140), bot=(8, 8, 22))
    d = ImageDraw.Draw(img, "RGBA")
    text_c(d, (540, 120), "ONLINE BATTLE MODE", 78)
    text_c(d, (540, 200), "Same puzzle. Same clock. Who solves it first?", 36, weight="Medium", fill=(215, 220, 255))
    hero = rounded(art("hero_card", (900, 528)), 40)
    paste(img, hero, 90, 270)
    steps = [("1", "Create a room"), ("2", "Share the 6-letter code"), ("3", "Race your friends live")]
    for i, (n, s) in enumerate(steps):
        y = 870 + i * 115
        overlay(img, lambda dd, y=y: dd.rounded_rectangle([90, y - 48, 990, y + 48], 48, fill=(255, 255, 255, 22)))
        d.ellipse([110, y - 36, 182, y + 36], fill=GOLD)
        text_c(d, (146, y), n, 40, fill=(30, 30, 30))
        d.text((215, y), s, font=font("Bold", 42), fill=WHITE, anchor="lm")
    footer(img, d)
    return img


def post_daily():
    img = gradient(1080, 1350, top=(8, 90, 140), bot=(6, 12, 24))
    d = ImageDraw.Draw(img, "RGBA")
    text_c(d, (540, 120), "DAILY CHALLENGE", 82)
    text_c(d, (540, 200), "A new puzzle every day. Build your streak.", 38, weight="Medium", fill=(215, 235, 250))
    paste(img, art("trophy_gold_02", 420), 330, 250)
    for i, m in enumerate(["milestone_bronze", "milestone_silver", "milestone_gold"]):
        paste(img, art(m, 170), 175 + i * 280, 700)
    text_c(d, (540, 930), "Earn milestone medals & monthly trophies", 40, weight="Medium", fill=(225, 238, 250))
    for i, t in enumerate(["trophy_gold_06", "trophy_gold_07", "trophy_gold_10"]):
        paste(img, art(t, 190), 195 + i * 250, 990)
    footer(img, d)
    return img


def post_puzzle():
    """Engagement post: find the missing number (answer in the caption/comments)."""
    img = gradient(1080, 1350, top=(20, 30, 60), bot=(8, 9, 14), glow=False)
    d = ImageDraw.Draw(img, "RGBA")
    text_c(d, (540, 110), "CAN YOU FIND", 80)
    text_c(d, (540, 200), "THE MISSING NUMBER?", 80, fill=GOLD)
    row = base.SOLUTION[1][:]
    cs = 108
    x0 = (1080 - 9 * cs) // 2
    y0 = 420
    d.rounded_rectangle([x0 - 8, y0 - 8, x0 + 9 * cs + 8, y0 + cs + 8], 14, fill=DARK["thick"])
    for c in range(9):
        x = x0 + c * cs
        last = c == 8
        d.rectangle([x + 2, y0 + 2, x + cs - 2, y0 + cs - 2], fill=DARK["sel"] if last else DARK["cell"])
        text_c(d, (x + cs / 2, y0 + cs / 2 + 2), "?" if last else str(row[c]), 64,
               fill=GOLD if last else DARK["given"], weight="Bold" if last else "Regular")
    for c in (3, 6):
        d.line([(x0 + c * cs, y0), (x0 + c * cs, y0 + cs)], fill=DARK["thick"], width=6)
    text_c(d, (540, 650), "Every row needs 1–9 exactly once.", 42, weight="Medium", fill=(210, 220, 240))
    text_c(d, (540, 760), "Comment your answer below", 54, weight="Bold")
    text_c(d, (540, 900), "Too easy? The game goes up to Extreme.", 40, weight="Medium", fill=(180, 195, 225))
    footer(img, d)
    return img


def post_howto():
    img = gradient(1080, 1350, top=(16, 60, 50), bot=(6, 12, 10))
    d = ImageDraw.Draw(img, "RGBA")
    text_c(d, (540, 120), "HOW TO PLAY SUDOKU", 76)
    text_c(d, (540, 200), "3 rules. Pure logic. No guessing.", 40, weight="Medium", fill=(205, 235, 220))
    rules = [("Every ROW", "contains 1–9 once"), ("Every COLUMN", "contains 1–9 once"), ("Every 3×3 BOX", "contains 1–9 once")]
    for i, (a, b) in enumerate(rules):
        y = 340 + i * 230
        overlay(img, lambda dd, y=y: dd.rounded_rectangle([90, y, 990, y + 190], 40, fill=(255, 255, 255, 24)))
        d.ellipse([125, y + 45, 225, y + 145], fill=(30, 158, 98))
        text_c(d, (175, y + 95), str(i + 1), 56)
        d.text((260, y + 70), a, font=font("Bold", 52), fill=WHITE, anchor="lm")
        d.text((260, y + 130), b, font=font("Medium", 40), fill=(205, 235, 220), anchor="lm")
    tips = [("action_pencil", "Pencil notes"), ("action_hint", "Hints"), ("action_undo", "Undo")]
    for i, (n, s) in enumerate(tips):
        x = 200 + i * 340
        paste(img, art(n, 110), x - 55, 1040)
        text_c(d, (x, 1180), s, 34, weight="Medium", fill=(205, 235, 220))
    footer(img, d)
    return img


POSTS = [("1-intro", post_intro), ("2-themes", post_themes), ("3-battle", post_battle),
         ("4-daily", post_daily), ("5-puzzle", post_puzzle), ("6-how-to-play", post_howto)]


def grid_preview(paths):
    """How the profile grid looks (3:4 tiles, newest first)."""
    tw, th = 360, 480
    g = Image.new("RGB", (3 * tw + 8, 2 * th + 4), (255, 255, 255))
    for i, p in enumerate(reversed(paths)):
        im = Image.open(p).convert("RGB")
        im = im.resize((tw, int(tw * im.height / im.width)))
        top = (im.height - th) // 2
        g.paste(im.crop((0, top, tw, top + th)), ((i % 3) * (tw + 4), (i // 3) * (th + 4)))
    g.save(os.path.join(OUT, "grid-preview.png"))


def main():
    profile_picture()
    highlights()
    paths = []
    for key, fn in POSTS:
        p = os.path.join(OUT, f"post-{key}.png")
        fn().convert("RGB").save(p)
        paths.append(p)
    grid_preview(paths)
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
