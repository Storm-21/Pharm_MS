"""
Generate the PharmMS logo assets.

Produces:
    pharms.ico              multi-resolution Windows icon (16..256 px)
    frontend/public/logo.svg        vector brand mark for the UI
    frontend/public/logo.png        raster brand mark (512 px) for print/reports
    frontend/public/logo-192.png    PWA / favicon size

The mark is a rounded-square badge containing a pharmacy cross whose arms are
formed by two capsules, sitting over a subtle radial glow. It is drawn
procedurally so the artwork is reproducible and version-controllable rather than
being an opaque binary someone has to re-draw.

Run:  python make_logo.py
"""

import os
import struct

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND_PUBLIC = os.path.normpath(os.path.join(HERE, '..', 'frontend', 'public'))

# Brand palette
BLUE_DARK = (30, 58, 138)      # indigo-900
BLUE = (37, 99, 235)           # blue-600
BLUE_LIGHT = (96, 165, 250)    # blue-400
CYAN = (34, 211, 238)          # cyan-400
WHITE = (255, 255, 255)

ICON_SIZES = [16, 24, 32, 48, 64, 128, 256]


def rounded_mask(size, radius, supersample=4):
    """Anti-aliased rounded-square alpha mask."""
    big = size * supersample
    mask = Image.new('L', (big, big), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, big - 1, big - 1], radius=radius * supersample, fill=255)
    return mask.resize((size, size), Image.LANCZOS)


def draw_badge(size):
    """The rounded blue tile with a radial glow."""
    ss = 4
    big = size * ss
    tile = Image.new('RGBA', (big, big), (0, 0, 0, 0))

    # Vertical gradient body.
    gradient = Image.new('RGBA', (big, big))
    gd = ImageDraw.Draw(gradient)
    for y in range(big):
        t = y / max(1, big - 1)
        r = int(BLUE_DARK[0] + (BLUE[0] - BLUE_DARK[0]) * t)
        g = int(BLUE_DARK[1] + (BLUE[1] - BLUE_DARK[1]) * t)
        b = int(BLUE_DARK[2] + (BLUE[2] - BLUE_DARK[2]) * t)
        gd.line([(0, y), (big, y)], fill=(r, g, b, 255))

    # Soft radial highlight towards the top-left.
    glow = Image.new('RGBA', (big, big), (0, 0, 0, 0))
    glow_d = ImageDraw.Draw(glow)
    glow_d.ellipse(
        [-big * 0.35, -big * 0.45, big * 0.75, big * 0.65],
        fill=CYAN + (95,),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(big * 0.12))
    gradient = Image.alpha_composite(gradient, glow)

    tile = Image.alpha_composite(tile, gradient)
    mask = rounded_mask(big, int(big * 0.22), supersample=1)
    tile.putalpha(mask)
    return tile.resize((size, size), Image.LANCZOS)


def draw_cross(draw, size, scale=1.0):
    """
    Draw the cross made of two capsules.

    Returns nothing; draws onto `draw` which is bound to an RGBA image at
    `size`. `scale` shrinks the mark inside the tile.
    """
    cx = cy = size / 2
    arm = size * 0.135 * scale        # half-thickness of an arm
    length = size * 0.33 * scale      # half-length of an arm
    radius = arm                      # fully rounded ends

    # Drop shadow for depth.
    shadow_offset = size * 0.012
    for dx, dy in ((shadow_offset, shadow_offset),):
        draw.rounded_rectangle(
            [cx - length + dx, cy - arm + dy, cx + length + dx, cy + arm + dy],
            radius=radius, fill=(0, 0, 0, 70),
        )
        draw.rounded_rectangle(
            [cx - arm + dx, cy - length + dy, cx + arm + dx, cy + length + dy],
            radius=radius, fill=(0, 0, 0, 70),
        )

    # Vertical arm: white with a faint blue edge.
    draw.rounded_rectangle(
        [cx - arm, cy - length, cx + arm, cy + length],
        radius=radius, fill=WHITE,
    )
    # Horizontal arm: cyan-tinted so the two arms read as separate capsules.
    draw.rounded_rectangle(
        [cx - length, cy - arm, cx + length, cy + arm],
        radius=radius, fill=(224, 247, 255, 255),
    )
    # Thin inner highlight on the vertical capsule.
    inset = arm * 0.42
    draw.rounded_rectangle(
        [cx - arm + inset, cy - length + inset, cx - arm + inset * 2.1, cy + length - inset],
        radius=arm * 0.3, fill=(255, 255, 255, 235),
    )


def make_icon(size):
    ss = 4
    big = size * ss
    badge = draw_badge(big)
    draw = ImageDraw.Draw(badge)
    draw_cross(draw, big, scale=1.0)
    return badge.resize((size, size), Image.LANCZOS)


def make_mark(size, transparent=True):
    """Standalone mark (no tile) for use on light backgrounds."""
    ss = 4
    big = size * ss
    img = Image.new('RGBA', (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if not transparent:
        img = draw_badge(big)
        draw = ImageDraw.Draw(img)
    draw_cross(draw, big, scale=1.02)
    return img.resize((size, size), Image.LANCZOS)


def write_ico(path, images):
    """Write a multi-resolution .ico with PNG-compressed entries (Vista+)."""
    import io as _io
    entries = []
    for img in images:
        buf = _io.BytesIO()
        img.save(buf, format='PNG')
        entries.append((img.width, img.height, buf.getvalue()))

    header = struct.pack('<HHH', 0, 1, len(entries))
    directory = b''
    offset = 6 + 16 * len(entries)
    payload = b''
    for width, height, data in entries:
        directory += struct.pack(
            '<BBBBHHII',
            0 if width >= 256 else width,
            0 if height >= 256 else height,
            0, 0, 1, 32, len(data), offset,
        )
        payload += data
        offset += len(data)

    with open(path, 'wb') as handle:
        handle.write(header + directory + payload)


LOGO_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128" width="128" height="128"
     role="img" aria-label="Pharmacy Management System">
 <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#1e3a8a"/>
      <stop offset="100%" stop-color="#2563eb"/>
    </linearGradient>
    <radialGradient id="glow" cx="26%" cy="18%" r="70%">
      <stop offset="0%" stop-color="#22d3ee" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#22d3ee" stop-opacity="0"/>
    </radialGradient>
    <filter id="soft" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="1.2" dy="1.2" stdDeviation="1.2" flood-color="#0b1220" flood-opacity="0.35"/>
    </filter>
 </defs>
 <rect x="0" y="0" width="128" height="128" rx="28" fill="url(#bg)"/>
 <rect x="0" y="0" width="128" height="128" rx="28" fill="url(#glow)"/>
 <g filter="url(#soft)">
    <rect x="53" y="21.8" width="22" height="84.4" rx="11" fill="#ffffff"/>
    <rect x="21.8" y="53" width="84.4" height="22" rx="11" fill="#e0f7ff"/>
    <rect x="58.6" y="30.6" width="4.6" height="60" rx="2.3" fill="#ffffff" opacity="0.92"/>
 </g>
</svg>
'''


def main():
    os.makedirs(FRONTEND_PUBLIC, exist_ok=True)

    # --- Windows icon ------------------------------------------------------
    frames = [make_icon(s) for s in ICON_SIZES]
    ico_path = os.path.join(HERE, 'pharms.ico')
    write_ico(ico_path, frames)
    print(f"wrote {ico_path}  ({len(frames)} sizes: {', '.join(str(s) for s in ICON_SIZES)})")

    # --- SVG (used by the UI and printable reports) ------------------------
    svg_path = os.path.join(FRONTEND_PUBLIC, 'logo.svg')
    with open(svg_path, 'w', encoding='utf-8') as handle:
        handle.write(LOGO_SVG)
    print(f"wrote {svg_path}")

    # --- PNGs --------------------------------------------------------------
    png_path = os.path.join(FRONTEND_PUBLIC, 'logo.png')
    make_icon(512).save(png_path, format='PNG')
    print(f"wrote {png_path}  (512x512)")

    small_path = os.path.join(FRONTEND_PUBLIC, 'logo192.png')
    make_icon(192).save(small_path, format='PNG')
    print(f"wrote {small_path}")

    favicon = os.path.join(FRONTEND_PUBLIC, 'favicon.ico')
    write_ico(favicon, [make_icon(s) for s in (16, 32, 48)])
    print(f"wrote {favicon}")


if __name__ == '__main__':
    main()
