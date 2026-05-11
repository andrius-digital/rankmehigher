#!/usr/bin/env python3
"""
Post-process a HeyGen UGC render:
  1. Auto-detect content bounds (ignore white/light borders)
  2. Crop to 9:16 slice filling the vertical frame
  3. Scale down to 1080×1920 if source is higher-res (lanczos)
  4. Speed up 1.1x (atempo preserves pitch)

Usage: postprocess_ugc.py <input.mp4> [output.mp4]
"""
import os, sys, subprocess, json
from pathlib import Path
from PIL import Image

in_path = Path(sys.argv[1])
out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else in_path.with_stem(in_path.stem + "_final")

# 1. probe dimensions
probe = subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "v",
     "-show_entries", "stream=width,height", "-of", "json", str(in_path)],
    capture_output=True, text=True, check=True,
)
info = json.loads(probe.stdout)["streams"][0]
W, H = info["width"], info["height"]
print(f"[probe] source {W}×{H}")

# 2. extract a mid-video frame for bound detection
mid_t = 3
frame = Path("/tmp/pp_frame.jpg")
subprocess.run(
    ["ffmpeg", "-y", "-ss", str(mid_t), "-i", str(in_path), "-vframes", "1", str(frame)],
    capture_output=True, check=True,
)

# 3. find content bounds (first non-near-white row from top, last from bottom)
im = Image.open(frame).convert("RGB")
def row_avg(y):
    r = im.crop((0, y, W, y+1))
    pix = list(r.getdata())
    return tuple(sum(c)/len(c) for c in zip(*pix))

top_y = 0
for y in range(0, H, 2):
    r, g, b = row_avg(y)
    # "white/near-white" = all channels above 235
    if not (r > 235 and g > 235 and b > 235):
        top_y = y
        break
bot_y = H-1
for y in range(H-1, -1, -2):
    r, g, b = row_avg(y)
    if not (r > 235 and g > 235 and b > 235):
        bot_y = y
        break
content_h = bot_y - top_y + 1
print(f"[scan] content rows {top_y}..{bot_y}  (h={content_h})")

# 4. compute 9:16 crop (vertical slice of the content band)
target_ar = 9 / 16  # width/height
crop_h = content_h
crop_w = int(round(crop_h * target_ar))
# ensure even
if crop_w % 2: crop_w -= 1
if crop_h % 2: crop_h -= 1
crop_x = (W - crop_w) // 2
crop_y = top_y
print(f"[crop] {crop_w}×{crop_h} @ ({crop_x},{crop_y})")

# 5. apply crop + scale to 1080×1920 + 1.1x speed
out_path.parent.mkdir(parents=True, exist_ok=True)
cmd = [
    "ffmpeg", "-y", "-i", str(in_path),
    "-filter_complex",
    f"[0:v]crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale=1080:1920:flags=lanczos,setpts=PTS/1.1[v];"
    f"[0:a]atempo=1.1[a]",
    "-map", "[v]", "-map", "[a]",
    "-c:v", "libx264", "-preset", "fast", "-crf", "18",  # higher quality (was 20)
    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    "-c:a", "aac", "-b:a", "192k",
    str(out_path),
]
print(f"[ffmpeg] rendering {out_path.name}...")
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print("STDERR:", r.stderr[-1500:])
    sys.exit(1)

# stats
probe2 = subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "stream=width,height",
     "-show_entries", "format=duration,size", "-of", "default=noprint_wrappers=1", str(out_path)],
    capture_output=True, text=True,
)
print(probe2.stdout)
print(f"[done] {out_path} ({out_path.stat().st_size//1024}KB)")
