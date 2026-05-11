#!/usr/bin/env python3
"""
Final UGC render: take HeyGen HD source, auto-crop to 9:16, scale to 1080×1920,
speed up voice to 1.05x (NOT music), mix trap beat at 15% volume, export.

Usage: mix_video_beat.py <heygen.mp4> <beat.mp3> <output.mp4>
"""
import os, sys, subprocess, json
from pathlib import Path
from PIL import Image

vid_in, beat_in, out_path = map(Path, sys.argv[1:4])
MUSIC_VOL = 0.15
VOICE_SPEED = 1.05

# probe + detect content bounds
probe = json.loads(subprocess.run(
    ["ffprobe","-v","error","-select_streams","v",
     "-show_entries","stream=width,height","-of","json",str(vid_in)],
    capture_output=True, text=True, check=True,
).stdout)["streams"][0]
W, H = probe["width"], probe["height"]

frame_jpg = Path("/tmp/mix_frame.jpg")
subprocess.run(["ffmpeg","-y","-ss","3","-i",str(vid_in),"-vframes","1",str(frame_jpg)],
               capture_output=True, check=True)
im = Image.open(frame_jpg).convert("RGB")
def row_avg(y):
    pix = list(im.crop((0,y,W,y+1)).getdata())
    return tuple(sum(c)/len(c) for c in zip(*pix))

top_y = next(y for y in range(0,H,2) if not all(c > 235 for c in row_avg(y)))
bot_y = next(y for y in range(H-1,-1,-2) if not all(c > 235 for c in row_avg(y)))
content_h = bot_y - top_y + 1
target_ar = 9/16
crop_w = int(round(content_h * target_ar)) & ~1
crop_h = content_h & ~1
crop_x = (W - crop_w) // 2
crop_y = top_y
print(f"[scan] content {top_y}..{bot_y}  crop {crop_w}×{crop_h} @ ({crop_x},{crop_y})")

# ffmpeg: crop+scale+speedup video, 1.05x voice audio, mix with beat at 15%
cmd = [
    "ffmpeg", "-y",
    "-i", str(vid_in),
    "-i", str(beat_in),
    "-filter_complex",
    f"[0:v]crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale=1080:1920:flags=lanczos,setpts=PTS/{VOICE_SPEED}[v];"
    f"[0:a]atempo={VOICE_SPEED},volume=1.0[voice];"
    f"[1:a]volume={MUSIC_VOL},apad[music];"
    f"[voice][music]amix=inputs=2:duration=first:dropout_transition=0[a]",
    "-map", "[v]", "-map", "[a]",
    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    "-c:a", "aac", "-b:a", "192k",
    "-shortest",
    str(out_path),
]
print(f"[ffmpeg] → {out_path}")
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print("STDERR:", r.stderr[-2000:])
    sys.exit(1)

probe2 = subprocess.run(
    ["ffprobe","-v","error","-show_entries","stream=width,height",
     "-show_entries","format=duration,size","-of","default=noprint_wrappers=1",str(out_path)],
    capture_output=True, text=True,
)
print(probe2.stdout)
print(f"[done] {out_path.stat().st_size//1024}KB")
