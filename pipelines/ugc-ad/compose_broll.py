#!/usr/bin/env python3
"""Simple composite — no zoompan. Just concat + captions + music."""
import os, json, subprocess, sys
from pathlib import Path
from PIL import Image

ART = sorted(Path("/opt/data/artifacts/ugc").iterdir())[-1]
print(f"[pipe] {ART}")
heygen_mp4 = ART / "heygen.mp4"
voiceover_mp3 = ART / "voiceover.mp3"
brolls = sorted(ART.glob("broll_*.mp4"))
ass_path = ART / "captions.ass"
beat_wav = Path("/opt/data/artifacts/music/trap_fal.wav")
SPEED = 1.10

# autocrop
probe = json.loads(subprocess.run(
    ["ffprobe","-v","error","-select_streams","v","-show_entries","stream=width,height","-of","json",str(heygen_mp4)],
    capture_output=True, text=True, check=True).stdout)["streams"][0]
W, H = probe["width"], probe["height"]
subprocess.run(["ffmpeg","-y","-ss","3","-i",str(heygen_mp4),"-vframes","1",str(ART/"sample.jpg")],
               capture_output=True, check=True)
im = Image.open(ART/"sample.jpg").convert("RGB")
def row_avg(y):
    pix = list(im.crop((0,y,W,y+1)).getdata())
    return tuple(sum(c)/len(c) for c in zip(*pix))
top_y = next(y for y in range(0,H,2) if not all(c > 235 for c in row_avg(y)))
bot_y = next(y for y in range(H-1,-1,-2) if not all(c > 235 for c in row_avg(y)))
ch = (bot_y - top_y + 1) & ~1
cw = (int(round(ch * 9/16))) & ~1
cx = (W - cw) // 2
cy = top_y

voice_dur = float(subprocess.run(
    ["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(voiceover_mp3)],
    capture_output=True, text=True, check=True).stdout.strip())
final_dur = voice_dur / SPEED

slots = [(2.0, 5.0), (6.0, 9.0)]
slots = [(s, min(e, final_dur)) for s, e in slots if s < final_dur]

segs = []
t = 0.0
for i, (s, e) in enumerate(slots):
    if s > t: segs.append(("main", t, s))
    segs.append(("broll", i, s, e))
    t = e
if t < final_dur: segs.append(("main", t, final_dur))
print(f"[timeline] {len(segs)} segs")

inputs = ["-i", str(heygen_mp4)] + [x for p in brolls for x in ["-i", str(p)]] + ["-i", str(beat_wav)]
beat_idx = 1 + len(brolls)

parts = []
labels = []
for i, seg in enumerate(segs):
    lbl = f"s{i}"
    if seg[0] == "main":
        _, s, e = seg
        parts.append(
            f"[0:v]trim=start={s*SPEED}:end={e*SPEED},setpts=PTS-STARTPTS,"
            f"crop={cw}:{ch}:{cx}:{cy},scale=1080:1920:flags=lanczos,"
            f"setpts=PTS/{SPEED},setsar=1,fps=30[{lbl}]"
        )
    else:
        _, bi, s, e = seg
        dur = e - s
        src_idx = 1 + bi
        parts.append(
            f"[{src_idx}:v]trim=duration={dur},setpts=PTS-STARTPTS,"
            f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"setsar=1,fps=30[{lbl}]"
        )
    labels.append(f"[{lbl}]")

parts.append(f"{''.join(labels)}concat=n={len(segs)}:v=1:a=0[catv]")
parts.append(f"[catv]ass={ass_path}[outv]")
parts.append(f"[0:a]atempo={SPEED}[voice]")
parts.append(f"[{beat_idx}:a]volume=0.15,apad[music]")
parts.append(f"[voice][music]amix=inputs=2:duration=first:dropout_transition=0[outa]")

out_path = ART / "final.mp4"
cmd = ["ffmpeg","-y", *inputs,
       "-filter_complex", ";".join(parts),
       "-map","[outv]","-map","[outa]",
       "-c:v","libx264","-preset","fast","-crf","18",
       "-pix_fmt","yuv420p","-movflags","+faststart",
       "-c:a","aac","-b:a","192k","-shortest",
       str(out_path)]
print("[ffmpeg] composite...")
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print("STDERR:", r.stderr[-2000:]); sys.exit(1)
print(f"[done] {out_path} {out_path.stat().st_size//1024}KB")
