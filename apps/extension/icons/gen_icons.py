"""Generate RealSight toolbar icons: an eye motif in state colors.

Run once:  pip install pillow && python gen_icons.py
Outputs <state>-<size>.png for sizes 16/32/48/128.
States: default (slate), off (gray), scan1/scan2/scan3 (blue pulse frames),
ai (red), real (green), uncertain (amber).
"""

from PIL import Image, ImageDraw

SIZES = [16, 32, 48, 128]
STATES = {
    "default": "#475569",
    "off": "#9ca3af",
    "scan1": "#2563eb",
    "scan2": "#3b82f6",
    "scan3": "#60a5fa",
    "ai": "#c62828",
    "real": "#2e7d32",
    "uncertain": "#d97706",
}
# pupil scale per scan frame gives a pulse effect when frames cycle
PUPIL = {"scan1": 0.16, "scan2": 0.22, "scan3": 0.28}


def draw_icon(color: str, size: int, pupil_scale: float) -> Image.Image:
    s = size * 4  # supersample for clean downscale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = s / 2

    # eye outline (almond) approximated by two arcs via ellipse clip:
    # draw a filled lens shape = intersection of two circles
    r = s * 0.62
    off = s * 0.38
    top = Image.new("L", (s, s), 0)
    ImageDraw.Draw(top).ellipse([cx - r, cy - off - r, cx + r, cy - off + r], fill=255)
    bot = Image.new("L", (s, s), 0)
    ImageDraw.Draw(bot).ellipse([cx - r, cy + off - r, cx + r, cy + off + r], fill=255)
    lens = Image.composite(Image.new("L", (s, s), 255), Image.new("L", (s, s), 0), top)
    lens.paste(0, (0, 0), Image.eval(bot, lambda p: 255 - p))
    img.paste(Image.new("RGBA", (s, s), color), (0, 0), lens)

    # iris (white ring) + pupil (colored, scaled for pulse)
    ir = s * 0.30
    d.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], fill="white")
    pr = s * pupil_scale
    d.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], fill=color)

    return img.resize((size, size), Image.LANCZOS)


for state, color in STATES.items():
    for size in SIZES:
        draw_icon(color, size, PUPIL.get(state, 0.22)).save(f"{state}-{size}.png")
        print(f"{state}-{size}.png")
