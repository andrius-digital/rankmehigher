#!/usr/bin/env python3
"""Inspect a video file for white/content borders at start, mid, end frames."""
import subprocess, sys
from pathlib import Path
try:
    from PIL import Image
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "pillow"], check=True)
    from PIL import Image

vid = sys.argv[1]
OUT = Path("/tmp/inspect_frames"); OUT.mkdir(exist_ok=True)

# extract 3 frames
for t in (0, 8, 16):
    outp = OUT / f"t{t}.jpg"
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(t), "-i", vid, "-vframes", "1", str(outp)
    ], capture_output=True, check=True)

# ffprobe
p = subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "v",
     "-show_entries", "stream=width,height,pix_fmt",
     "-of", "default=noprint_wrappers=1", vid],
    capture_output=True, text=True,
)
print("=== video specs ===")
print(p.stdout.strip())
print()

# analyze borders
for t in (0, 8, 16):
    im = Image.open(OUT / f"t{t}.jpg").convert("RGB")
    w, h = im.size
    # sample top 10 rows, bottom 10 rows, left 10 cols, right 10 cols
    top = im.crop((0, 0, w, 10))
    bot = im.crop((0, h-10, w, h))
    lft = im.crop((0, 0, 10, h))
    rgt = im.crop((w-10, 0, w, h))

    def avg(region):
        pix = list(region.getdata())
        r = sum(p[0] for p in pix) / len(pix)
        g = sum(p[1] for p in pix) / len(pix)
        b = sum(p[2] for p in pix) / len(pix)
        return (int(r), int(g), int(b))

    print(f"t={t}s  {w}x{h}")
    print(f"  top 10 rows avg: {avg(top)}")
    print(f"  bot 10 rows avg: {avg(bot)}")
    print(f"  lft 10 cols avg: {avg(lft)}")
    print(f"  rgt 10 cols avg: {avg(rgt)}")
    # scan down from top to find first non-white row
    for y in range(0, h, 5):
        row = im.crop((0, y, w, y+1))
        r,g,b = avg(row)
        if r < 240 or g < 240 or b < 240:
            print(f"  first non-white-ish row from top: y={y}  rgb=({r},{g},{b})")
            break
    # scan up from bottom
    for y in range(h-1, -1, -5):
        row = im.crop((0, y, w, y+1))
        r,g,b = avg(row)
        if r < 240 or g < 240 or b < 240:
            print(f"  last non-white-ish row from bot: y={y}  rgb=({r},{g},{b})")
            break
