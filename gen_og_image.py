"""
Generate og-default.png — the Open Graph / Twitter Card default image
for pratikdhanave.github.io.

Size: 1200x630px (standard OG image)
Run:  python3 gen_og_image.py
Output: og-default.png in the repo root
"""

from PIL import Image, ImageDraw, ImageFont
import os

W, H = 1200, 630

# ── Colours ─────────────────────────────────────────────────────────────────
BG_TOP      = (10,  18,  40)   # deep navy
BG_BOTTOM   = (20,  36,  72)   # slightly lighter navy
ACCENT      = (99, 179, 237)   # sky blue  (#63B3ED)
ACCENT2     = (154, 117, 234)  # soft purple (#9A75EA)
WHITE       = (255, 255, 255)
LIGHT_GREY  = (180, 195, 215)
DIM_GREY    = (100, 120, 150)

# ── Font helper ──────────────────────────────────────────────────────────────
FONT_PATHS = [
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/ArialHB.ttc",
]

def load_font(size, bold=False):
    for path in FONT_PATHS:
        if os.path.exists(path):
            try:
                # .ttc files: index 1 is often Bold for Helvetica Neue
                idx = 1 if (bold and path.endswith(".ttc")) else 0
                return ImageFont.truetype(path, size, index=idx)
            except Exception:
                continue
    return ImageFont.load_default()

# ── Canvas ───────────────────────────────────────────────────────────────────
img  = Image.new("RGB", (W, H), BG_TOP)
draw = ImageDraw.Draw(img)

# Gradient background (top → bottom)
for y in range(H):
    t = y / H
    r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
    g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
    b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

# ── Decorative accent bar (left edge) ────────────────────────────────────────
bar_w = 6
for y in range(120, 510):
    t = (y - 120) / (510 - 120)
    r = int(ACCENT[0] + (ACCENT2[0] - ACCENT[0]) * t)
    g = int(ACCENT[1] + (ACCENT2[1] - ACCENT[1]) * t)
    b = int(ACCENT[2] + (ACCENT2[2] - ACCENT[2]) * t)
    draw.line([(72, y), (72 + bar_w, y)], fill=(r, g, b))

# ── Subtle dot-grid pattern (top-right quadrant) ─────────────────────────────
for gx in range(700, 1160, 36):
    for gy in range(60, 340, 36):
        draw.ellipse([(gx-1, gy-1), (gx+1, gy+1)], fill=(40, 65, 110))

# ── Fonts ─────────────────────────────────────────────────────────────────────
f_tag    = load_font(20)
f_name   = load_font(74, bold=True)
f_title  = load_font(34)
f_chips  = load_font(22)
f_url    = load_font(20)

# ── Tag line above name ───────────────────────────────────────────────────────
TAG = "pratikdhanave.github.io"
draw.text((100, 138), TAG, font=f_tag, fill=ACCENT)

# ── Name ──────────────────────────────────────────────────────────────────────
NAME = "Pratik Dhanave"
draw.text((100, 172), NAME, font=f_name, fill=WHITE)

# ── Title ─────────────────────────────────────────────────────────────────────
TITLE = "Multi-Agent AI Engineer  ·  Distributed Systems  ·  Cloud Architect"
draw.text((100, 272), TITLE, font=f_title, fill=LIGHT_GREY)

# ── Thin separator line ───────────────────────────────────────────────────────
draw.line([(100, 336), (900, 336)], fill=(50, 75, 120), width=1)

# ── Skill chips ───────────────────────────────────────────────────────────────
chips = ["Go", "HIPAA-grade AI", "MARA", "GCP", "FinTech", "Healthcare AI"]
cx = 100
cy = 362
pad_x, pad_y, radius = 18, 10, 8

for chip in chips:
    bbox = draw.textbbox((0, 0), chip, font=f_chips)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    box = [cx, cy, cx + tw + pad_x * 2, cy + th + pad_y * 2]
    draw.rounded_rectangle(box, radius=radius, fill=(30, 52, 95), outline=(60, 90, 140))
    draw.text((cx + pad_x, cy + pad_y), chip, font=f_chips, fill=ACCENT)
    cx += tw + pad_x * 2 + 14

# ── Bottom strip ──────────────────────────────────────────────────────────────
draw.rectangle([(0, H - 58), (W, H)], fill=(8, 15, 35))
draw.text((100, H - 40), "Building production-grade AI systems · 147 articles · Open Source", font=f_url, fill=DIM_GREY)

# ── Small accent circle (bottom-right branding dot) ──────────────────────────
draw.ellipse([(1110, H - 58 - 60), (1170, H - 58)], fill=(20, 40, 80), outline=ACCENT, width=2)
draw.text((1122, H - 58 - 38), "PD", font=load_font(22, bold=True), fill=ACCENT)

# ── Save ──────────────────────────────────────────────────────────────────────
OUT = os.path.join(os.path.dirname(__file__), "og-default.png")
img.save(OUT, "PNG", optimize=True)
print(f"✅ Saved {OUT}  ({W}x{H}px)")
