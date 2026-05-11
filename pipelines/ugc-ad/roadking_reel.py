#!/usr/bin/env python3
"""Road King Express — flatbed driver hiring reel.

Same pipeline shape as cdl/azfs/mslines reels EXCEPT b-roll is REAL
client-supplied footage (12 iPhone 4K clips at 60fps) instead of
Fal/Kling generations. Voice = Young Jamal, music = Fal stable-audio,
captions = Arial Black 140pt with outline+shadow (legibility on bright
sunny truck-yard footage), avatar = OFF (real drivers in the b-roll
already serve as the spokesperson; an unbranded HeyGen overlay would
dilute the brand).

Usage:
    python3 roadking_reel.py --out-dir output/roadking_$(date +%Y%m%d_%H%M%S) \
        --broll-dir ~/Downloads/drive-download-20260506T211749Z-3-003

    # Skip telegram delivery while iterating:
    python3 roadking_reel.py --out-dir output/test --no-telegram

Required env: FAL_KEY, ELEVENLABS_API_KEY,
              TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID (only when sending)
              HEYGEN_API_KEY (only when --with-avatar)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Default macOS homebrew `ffmpeg` ships without libass — the `ass` filter is
# missing and caption rendering fails. `ffmpeg-full` (also via brew) is built
# with libass and lives at the keg-only path below. Override with FFMPEG_BIN
# env var if running on a system with a libass-enabled ffmpeg on PATH.
FFMPEG = os.environ.get("FFMPEG_BIN") or (
    "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
    if Path("/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg").exists()
    else "ffmpeg"
)
FFPROBE = os.environ.get("FFPROBE_BIN") or (
    "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"
    if Path("/opt/homebrew/opt/ffmpeg-full/bin/ffprobe").exists()
    else "ffprobe"
)

# ----------------------------------------------------------------------
# Brand config — Road King Express, flatbed driver hiring
# ----------------------------------------------------------------------
BRAND_NAME = "Road King Express"
VOICE_ID = "6OzrBCQf8cjERkYgzSg8"  # Young Jamal
SPEED = 1.0

# 4 angle-based script variants. Each variant ~30-40s of natural pace.
# Phonetic notes: CDLA stays as one token "CDLA" (overrides handle case),
#   "Oh Tee Are" → OTR, "Sapp" → SAP, "Dee You Eye" → DUI.
VARIANTS: dict[str, str] = {
    "guarantee": (
        'Attention Oh Tee Are flatbed drivers. <break time="500ms"/>'
        'Three thousand plus a week. <break time="200ms"/>Every week. <break time="200ms"/>'
        'That\'s the job. <break time="500ms"/>'
        'Road King Express pays seventy five cents per mile. <break time="300ms"/>'
        'All miles paid. <break time="500ms"/>'
        'Or take thirty percent of gross. <break time="300ms"/>'
        'When rates go up, your check goes up. <break time="500ms"/>'
        'Ten ninety nine position. <break time="300ms"/>You control your income. <break time="500ms"/>'
        'Three thousand plus miles every week. <break time="300ms"/>'
        'No games. <break time="200ms"/>No shortcuts. <break time="500ms"/>'
        'Refer a driver who gets hired — two thousand cash is yours. <break time="500ms"/>'
        'Two years See Dee El Ay Oh Tee Are experience. <break time="200ms"/>'
        'Clean record. <break time="200ms"/>No Dee You Eye. <break time="200ms"/>No Ess Ay Pee. <break time="500ms"/>'
        'Click the link below. <break time="200ms"/>Leave your info. <break time="200ms"/>'
        'A recruiter reaches out the same day.'
    ),
    "pain": (
        'Finishing the week under three thousand dollars? <break time="400ms"/>'
        'Your carrier is leaving money on the table. <break time="300ms"/>'
        'And so are you. <break time="500ms"/>'
        'Road King Express delivers three thousand plus miles every week. <break time="500ms"/>'
        'Three thousand plus in your pocket. <break time="300ms"/>Every week. <break time="200ms"/>'
        'Not sometimes — every week. <break time="500ms"/>'
        'Seventy five cents per mile on every mile. <break time="300ms"/>'
        'Or thirty percent of gross. <break time="200ms"/>You pick what works. <break time="500ms"/>'
        'Ten ninety nine position. Keep more of what you earn. <break time="500ms"/>'
        'Refer a driver who gets hired, get two thousand cash. <break time="500ms"/>'
        'Two years See Dee El Ay Oh Tee Are experience. <break time="200ms"/>'
        'No Dee You Eye. <break time="200ms"/>No Ess Ay Pee. <break time="200ms"/>Clean record. <break time="500ms"/>'
        'Click the link below and apply. <break time="300ms"/>'
        'We review every application and get back to serious drivers fast.'
    ),
    "social": (
        'I\'ve been driving flatbed Oh Tee Are for years. <break time="400ms"/>'
        'I wish I found Road King Express sooner. <break time="500ms"/>'
        'Freight is moving right now. <break time="200ms"/>Rates are up. <break time="300ms"/>'
        'This is the market where you should be making real money. <break time="500ms"/>'
        'At Road King Express I\'m pulling three thousand plus miles every week. <break time="300ms"/>'
        'Three thousand plus every week. <break time="200ms"/>Consistently. <break time="500ms"/>'
        'Seventy five cents a mile — every mile counts. <break time="300ms"/>'
        'Or thirty percent of gross — when the market is hot, your paycheck is hot. <break time="500ms"/>'
        'Ten ninety nine position. <break time="200ms"/>Running your own income. <break time="200ms"/>'
        'Keeping more of what you earn. <break time="500ms"/>'
        'I\'ve already referred two drivers. <break time="200ms"/>'
        'That\'s four thousand dollars in referral bonuses on top of my pay. <break time="500ms"/>'
        'Two years See Dee El Ay Oh Tee Are. <break time="200ms"/>Clean record. <break time="200ms"/>'
        'No Dee You Eye. <break time="200ms"/>No Ess Ay Pee. <break time="200ms"/>That\'s all they need. <break time="500ms"/>'
        'Link is below. <break time="300ms"/>Submit your info — recruiting walks you through next steps.'
    ),
    "elim": (
        'No short miles. <break time="200ms"/>No hidden cuts. <break time="200ms"/>No excuses. <break time="500ms"/>'
        'Road King Express is hiring flatbed Oh Tee Are drivers now. <break time="500ms"/>'
        'Three thousand plus miles every week. <break time="300ms"/>'
        'Three thousand plus pay every week. <break time="500ms"/>'
        'Seventy five cents per mile. <break time="300ms"/>Or thirty percent of gross. <break time="200ms"/>'
        'You choose. <break time="500ms"/>'
        'Ten ninety nine position. <break time="200ms"/>Your income, your rules. <break time="500ms"/>'
        'Refer a driver who gets hired — two thousand cash goes to you. <break time="500ms"/>'
        'Two years See Dee El Ay Oh Tee Are experience. <break time="200ms"/>'
        'Clean record. <break time="200ms"/>No Dee You Eye. <break time="200ms"/>No Ess Ay Pee. <break time="500ms"/>'
        'Click the link below and apply today. <break time="500ms"/>'
        'If you meet the requirements, we\'ll be in touch within twenty four hours.'
    ),
}
SSML = VARIANTS["guarantee"]  # default — overridden by --variant in main()

# Local b-roll selection — (filename, trim_duration, start_offset_in_clip).
# Sequenced to match script beats:
#   0-3s   wide white truck (hook: "running flatbed under 3K")
#   3-6s   FLATBED with tarped load (visual proof: "flatbed")
#   6-9s   ROAD KING EXPRESS logo close-up (brand reveal: "Road King Express pays")
#   9-12s  truck side w/ flatbed trailer ("75¢ a mile / 30%")
#   12-15s POV driving cockpit ("your choice / 1099")
#   15-18.5s driver climbing into cab ("refer / requirements")
#   18.5-22.5s side branded truck (CTA hold)
# Library of all available clips, keyed by short ID. Each variant picks a
# different sequence so the 4 reels feel visually distinct, not 4 copies.
CLIP_LIBRARY: dict[int, tuple[str, float, float]] = {
    1:  ("IMG_0415.MOV", 3.5, 1.0),  # wide white truck (hook visual)
    2:  ("IMG_1236.MOV", 3.5, 0.5),  # FLATBED with tarped load
    3:  ("IMG_0420.MOV", 3.5, 1.0),  # ROAD KING EXPRESS logo close-up
    4:  ("IMG_0489.MOV", 3.5, 1.5),  # truck side w/ flatbed trailer
    5:  ("IMG_0465.MOV", 3.5, 4.0),  # POV driving cockpit
    6:  ("IMG_0499.MOV", 4.0, 1.0),  # driver climbing into cab
    7:  ("IMG_0418.MOV", 4.0, 1.0),  # side branded truck
    8:  ("IMG_0462.MOV", 3.5, 1.0),
    9:  ("IMG_0468.MOV", 3.5, 1.0),
    10: ("IMG_0471.MOV", 3.5, 1.0),
    11: ("IMG_0473.MOV", 3.5, 1.0),
    12: ("IMG_0477.MOV", 3.5, 1.0),
}

# Per-variant clip order — each variant gets a different cinematic sequence so
# the 4 reels don't all look identical despite sharing the same source library.
# Order is chosen to match each variant's tone:
#   guarantee : confident open-road build (truck → flatbed → logo → action)
#   pain      : start in cab POV (frustrated mood) → action → logo reveal
#   social    : driver-first (climbing in, leaning) — testimonial framing
#   elim      : sharp logo cold-open → clean cuts of equipment + action
VARIANT_CLIP_ORDER: dict[str, list[int]] = {
    "guarantee": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    "pain":      [5, 6, 1, 4, 3, 8, 2, 9, 7, 11, 10, 12],
    "social":    [6, 7, 5, 4, 1, 3, 12, 8, 2, 9, 11, 10],
    "elim":      [3, 7, 1, 2, 4, 5, 6, 9, 11, 8, 12, 10],
}

# Backwards-compat alias — some callers still expect this name.
LOCAL_BROLL_CLIPS = [CLIP_LIBRARY[i] for i in VARIANT_CLIP_ORDER["guarantee"]]

MUSIC_PROMPT = (
    "Upbeat motivational country-rock instrumental for truckers, electric guitar "
    "riffs, driving 4/4 rhythm, mid-tempo americana with full drums, gritty hopeful "
    "rebellious energy, no vocals, 30 seconds"
)

# Caption style — Arial Black 140pt white with BLACK OUTLINE 6 + SHADOW 3.
# The b-roll is bright (sunny truck yard, blue sky, white trucks, daylight
# windshield POV) so plain white captions wash out without an outline.
# Per memory: BorderStyle=1 + Outline=6 + Shadow=3 is the new default for any
# UGC reel against bright footage.
ASS_STYLE = (
    "Style: Default,Arial Black,140,&H00FFFFFF,&H00FFFFFF,&H00000000,"
    "&HFF000000,-1,0,0,0,100,100,0,0,1,6,3,2,60,60,750,1"
)

# Single-word display overrides applied during caption rendering.
CAPTION_DISPLAY_OVERRIDES: dict[str, str] = {
    "sapp": "SAP",
    "cdla": "CDLA",
    # phonetic letters (in case OTR bundle gets split)
    "oh": "O",
    "tee": "T",
    "are": "R",
}

# Multi-word bundles → display swaps (longest match first inside merge_url_bundles).
URL_BUNDLES: list[tuple[tuple[str, ...], str]] = [
    (("seventy", "five", "cents", "per", "mile"), "75¢/MILE"),
    (("seventy", "five", "cents", "a", "mile"), "75¢/MILE"),
    (("three", "thousand", "plus", "every", "week"), "$3,000+/WEEK"),
    (("three", "thousand", "plus", "miles", "every", "week"), "3,000+ MILES/WK"),
    (("three", "thousand", "plus", "miles", "weekly"), "3,000+ MILES/WK"),
    (("three", "thousand", "plus", "in", "your", "pocket"), "$3,000+ IN POCKET"),
    (("three", "thousand", "plus", "pay", "every", "week"), "$3,000+ PAY/WK"),
    (("three", "thousand", "a", "week"), "$3,000/WEEK"),
    (("under", "three", "thousand", "dollars"), "UNDER $3K"),
    (("under", "three", "thousand", "a", "week"), "UNDER $3K/WK"),
    (("thirty", "percent", "of", "gross"), "30% OF GROSS"),
    (("two", "thousand", "cash"), "$2,000 CASH"),
    (("four", "thousand", "dollars"), "$4,000"),
    (("ten", "ninety", "nine"), "1099"),
    (("two", "years"), "2 YEARS"),
    (("see", "dee", "el", "ay"), "CDL-A"),
    (("ess", "ay", "pee"), "SAP"),
    (("oh", "tee", "are"), "OTR"),
    (("dee", "you", "eye"), "DUI"),
    (("twenty", "four", "hours"), "24 HRS"),
]

# Avatar OFF by default — real drivers in b-roll are the spokesperson.
# Set HEYGEN_ROADKING_AVATAR_ID + pass --with-avatar to enable.
AVATAR_ID = os.environ.get(
    "HEYGEN_ROADKING_AVATAR_ID",
    os.environ.get("HEYGEN_CDL_AVATAR_ID_UNBRANDED", "54b1e308527b4d56b2ef0824a12ce628"),
)
PIP_SIZE = 480
PIP_RADIUS = 40
PIP_MARGIN_X = 60
PIP_MARGIN_TOP = 200
PIP_GLOW_PAD = 60


# ----------------------------------------------------------------------
# HTTP helpers
# ----------------------------------------------------------------------
def env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"missing env var: {name}")
    return v


def http_json(method: str, url: str, headers: dict, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body else None,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {url} → {e.code}: {e.read().decode('utf-8','replace')}") from None


def fal_app_namespace(model_id: str) -> str:
    return "/".join(model_id.split("/")[:2])


def fal_run(model_id: str, body: dict, label: str, max_wait: int = 1500) -> dict:
    h = {"Authorization": f"Key {env('FAL_KEY')}", "Content-Type": "application/json"}
    submit = http_json("POST", f"https://queue.fal.run/{model_id}", h, body)
    rid = submit["request_id"]
    ns = fal_app_namespace(model_id)
    print(f"[{label}] queued {rid}", flush=True)
    t0 = time.time()
    while time.time() - t0 < max_wait:
        s = http_json("GET", f"https://queue.fal.run/{ns}/requests/{rid}/status", h)
        st = s.get("status")
        print(f"[{label}] {int(time.time()-t0):>3}s {st}", flush=True)
        if st == "COMPLETED":
            return http_json("GET", f"https://queue.fal.run/{ns}/requests/{rid}", h)
        if st in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"[{label}] {st}: {s}")
        time.sleep(8)
    raise RuntimeError(f"[{label}] timeout {max_wait}s")


# ----------------------------------------------------------------------
# Asset prep
# ----------------------------------------------------------------------
def prep_local_broll(idx: int, src: Path, trim_dur: float, start: float, out: Path) -> Path:
    """Trim a real b-roll clip to the desired window, normalize to 1080x1920 30fps,
    and apply a subtle 4% Ken Burns zoom. iPhone clips include rotation metadata
    which ffmpeg auto-honors; we strip it from the output via -map_metadata -1.
    """
    label = f"broll{idx}"
    p = out / f"broll_{idx}.mp4"
    if p.exists() and p.stat().st_size > 100_000:
        print(f"[{label}] reusing {p.name}", flush=True)
        return p
    print(f"[{label}] trim {src.name} @{start:.1f}s for {trim_dur:.1f}s", flush=True)
    vf = (
        f"scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,"
        f"scale='trunc(1080*(1+0.04*t/{trim_dur})/2)*2':'trunc(1920*(1+0.04*t/{trim_dur})/2)*2'"
        f":eval=frame:flags=lanczos,"
        f"crop=1080:1920:(iw-1080)/2:(ih-1920)/2,"
        f"fps=30,setsar=1"
    )
    cmd = [
        FFMPEG, "-y", "-ss", f"{start}", "-i", str(src),
        "-t", f"{trim_dur}",
        "-vf", vf,
        "-map_metadata", "-1",
        "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        str(p),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-2000:], flush=True)
        raise RuntimeError(f"[{label}] ffmpeg trim failed")
    print(f"[{label}] saved {p.name} ({p.stat().st_size:,} B)", flush=True)
    return p


def gen_music(out: Path) -> Path:
    p = out / "music.wav"
    if p.exists() and p.stat().st_size > 100_000:
        print(f"[music] reusing {p.name}", flush=True)
        return p
    r = fal_run(
        "fal-ai/stable-audio-25/text-to-audio",
        {"prompt": MUSIC_PROMPT, "seconds_total": 30},
        "music",
    )
    url = r.get("audio", r.get("audio_file", {})).get("url")
    if not url:
        raise RuntimeError(f"music: no URL in {r}")
    urllib.request.urlretrieve(url, p)
    print(f"[music] saved {p.name} ({p.stat().st_size:,} B)", flush=True)
    return p


def gen_voice(out: Path, ssml: str = SSML) -> tuple[Path, dict]:
    p = out / "voiceover.mp3"
    align_p = out / "alignment.json"
    if p.exists() and p.stat().st_size > 50_000 and align_p.exists():
        print(f"[voice] reusing {p.name} ({p.stat().st_size:,} B)", flush=True)
        return p, json.loads(align_p.read_text())
    print("[voice] generating Young Jamal with timestamps", flush=True)
    body = {
        "text": ssml,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.35,
            "similarity_boost": 0.8,
            "style": 0.6,
            "use_speaker_boost": True,
        },
    }
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/with-timestamps",
        data=json.dumps(body).encode(),
        headers={"xi-api-key": env("ELEVENLABS_API_KEY"), "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read())
    import base64

    p.write_bytes(base64.b64decode(data["audio_base64"]))
    align = data["alignment"]
    align_p.write_text(json.dumps(align, indent=2))
    print(f"[voice] saved {p.name} ({p.stat().st_size:,} B)", flush=True)
    return p, align


# ----------------------------------------------------------------------
# PiP avatar (optional)
# ----------------------------------------------------------------------
def gen_pip_assets(out: Path) -> tuple[Path, Path]:
    from PIL import Image, ImageChops, ImageDraw, ImageFilter

    mask = Image.new("L", (PIP_SIZE, PIP_SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, PIP_SIZE - 1, PIP_SIZE - 1), radius=PIP_RADIUS, fill=255,
    )
    mask_path = out / "pip_mask.png"
    mask.save(mask_path)

    halo_w = PIP_SIZE + 2 * PIP_GLOW_PAD
    glow = Image.new("RGBA", (halo_w, halo_w), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle(
        (PIP_GLOW_PAD - 6, PIP_GLOW_PAD - 6,
         PIP_GLOW_PAD + PIP_SIZE + 5, PIP_GLOW_PAD + PIP_SIZE + 5),
        radius=PIP_RADIUS + 8, fill=(255, 255, 255, 180),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=18))
    hole = Image.new("L", (halo_w, halo_w), 0)
    ImageDraw.Draw(hole).rounded_rectangle(
        (PIP_GLOW_PAD, PIP_GLOW_PAD,
         PIP_GLOW_PAD + PIP_SIZE - 1, PIP_GLOW_PAD + PIP_SIZE - 1),
        radius=PIP_RADIUS, fill=255,
    )
    inv_hole = Image.eval(hole, lambda v: 255 - v)
    _, _, _, glow_alpha = glow.split()
    glow.putalpha(ImageChops.multiply(glow_alpha, inv_hole))
    glow_path = out / "pip_glow.png"
    glow.save(glow_path)
    return mask_path, glow_path


def _upload_audio_to_heygen(file_path: Path) -> str:
    print(f"[upload] uploading {file_path.name} to HeyGen asset CDN", flush=True)
    r = subprocess.run([
        "curl", "-s", "-X", "POST", "https://upload.heygen.com/v1/asset",
        "-H", f"X-Api-Key: {env('HEYGEN_API_KEY')}",
        "-H", "Content-Type: audio/mpeg",
        "--data-binary", f"@{file_path}",
    ], capture_output=True, text=True, check=True)
    resp = json.loads(r.stdout)
    if resp.get("code") != 100 or "url" not in resp.get("data", {}):
        raise RuntimeError(f"heygen upload failed: {resp}")
    return resp["data"]["url"]


def gen_heygen(voice: Path, out: Path) -> Path:
    audio_url = _upload_audio_to_heygen(voice)
    print(f"[heygen] avatar={AVATAR_ID}", flush=True)
    body = {
        "video_inputs": [{
            "character": {
                "type": "talking_photo",
                "talking_photo_id": AVATAR_ID,
                "talking_photo_style": "square",
                "talking_style": "expressive",
                "expression": "happy",
            },
            "voice": {"type": "audio", "audio_url": audio_url},
        }],
        "dimension": {"width": 1440, "height": 2560},
    }
    r = http_json("POST", "https://api.heygen.com/v2/video/generate",
                  {"X-Api-Key": env("HEYGEN_API_KEY"), "Content-Type": "application/json"}, body)
    vid_id = r["data"]["video_id"]
    raw = out / "heygen_raw.mp4"
    t0 = time.time()
    while time.time() - t0 < 600:
        time.sleep(10)
        s = http_json("GET", f"https://api.heygen.com/v1/video_status.get?video_id={vid_id}",
                      {"X-Api-Key": env("HEYGEN_API_KEY")})["data"]
        st = s.get("status")
        print(f"[heygen] {int(time.time()-t0):>3}s {st}", flush=True)
        if st == "completed":
            urllib.request.urlretrieve(s["video_url"], raw)
            break
        if st == "failed":
            raise RuntimeError(f"[heygen] FAILED: {s.get('error')}")
    else:
        raise RuntimeError("[heygen] timeout")

    from PIL import Image
    sample = out / "heygen_sample.jpg"
    subprocess.run([FFMPEG, "-y", "-ss", "1.5", "-i", str(raw),
                    "-vframes", "1", str(sample)], capture_output=True, check=True)
    im = Image.open(sample).convert("RGB")
    W, H = im.size

    def row_avg(y: int) -> tuple[float, float, float]:
        pix = list(im.crop((0, y, W, y + 1)).getdata())
        return tuple(sum(c) / len(c) for c in zip(*pix))

    top_y = next((y for y in range(0, H, 2) if not all(c > 235 for c in row_avg(y))), 0)
    bot_y = next((y for y in range(H - 1, -1, -2) if not all(c > 235 for c in row_avg(y))), H - 1)
    ch = (bot_y - top_y + 1) & ~1
    cw = ch
    cx = (W - cw) // 2
    cy = top_y

    pip = out / "heygen_pip.mp4"
    subprocess.run([
        FFMPEG, "-y", "-i", str(raw),
        "-vf", f"crop={cw}:{ch}:{cx}:{cy},scale={PIP_SIZE}:{PIP_SIZE}:flags=lanczos,setsar=1",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-an", str(pip),
    ], capture_output=True, check=True)
    return pip


# ----------------------------------------------------------------------
# Captions
# ----------------------------------------------------------------------
def extract_words(align: dict) -> list[dict]:
    chars = align["characters"]
    starts = align["character_start_times_seconds"]
    ends = align["character_end_times_seconds"]
    words: list[dict] = []
    buf = ""
    wstart = 0.0
    in_tag = False
    for i, ch in enumerate(chars):
        if ch == "<":
            if buf.strip():
                words.append({"text": buf.strip(), "start": wstart, "end": ends[i - 1] if i > 0 else ends[i]})
            buf = ""
            in_tag = True
            continue
        if in_tag:
            if ch == ">":
                in_tag = False
            continue
        if buf == "":
            wstart = starts[i]
        if ch in (" ", "\n"):
            if buf.strip():
                words.append({"text": buf.strip(), "start": wstart, "end": ends[i - 1] if i > 0 else ends[i]})
            buf = ""
        else:
            buf += ch
    if buf.strip():
        words.append({"text": buf.strip(), "start": wstart, "end": ends[-1]})
    for i in range(len(words) - 1):
        words[i]["end"] = min(words[i + 1]["start"], words[i]["end"] + 0.40)
    return words


def merge_url_bundles(words: list[dict]) -> list[dict]:
    patterns = sorted(URL_BUNDLES, key=lambda p: -len(p[0]))
    out: list[dict] = []
    i = 0
    while i < len(words):
        matched = False
        for pattern, display_text in patterns:
            n = len(pattern)
            if i + n > len(words):
                continue
            seq = tuple(words[k]["text"].lower().rstrip(".,!?") for k in range(i, i + n))
            if seq == pattern:
                out.append({"text": display_text, "start": words[i]["start"], "end": words[i + n - 1]["end"]})
                i += n
                matched = True
                break
        if not matched:
            out.append(words[i])
            i += 1
    return out


def display(text: str) -> str:
    t = text.rstrip(".,!?")
    o = CAPTION_DISPLAY_OVERRIDES.get(t.lower())
    if o:
        return o
    return t.upper() if t else text.upper()


def write_ass(words: list[dict], path: Path) -> None:
    def ts(sec: float) -> str:
        s = sec / SPEED
        h = int(s // 3600); s -= h * 3600
        m = int(s // 60); s -= m * 60
        return f"{h}:{int(m):02d}:{s:05.2f}"

    def fit_size(text: str) -> int:
        n = len(text)
        if n <= 10:
            return 0
        return max(80, 140 - (n - 10) * 8)

    body = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "WrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"{ASS_STYLE}\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    for w in words:
        text = display(w["text"])
        size = fit_size(text)
        prefix = f"{{\\fs{size}}}" if size else ""
        body += f"Dialogue: 0,{ts(w['start'])},{ts(w['end'])},Default,,0,0,0,,{prefix}{text}\n"
    path.write_text(body)


# ----------------------------------------------------------------------
# Composite
# ----------------------------------------------------------------------
def composite(brolls: list[Path], voice: Path, music: Path, ass: Path,
              avatar: Path | None, mask: Path | None, glow: Path | None,
              clip_durs: list[float], out: Path) -> Path:
    final = out / "roadking_reel_final.mp4"
    voice_raw = float(subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(voice)],
        capture_output=True, text=True, check=True).stdout.strip())
    final_dur = round(voice_raw / SPEED + 0.30, 2)
    print(f"[ffmpeg] voice {voice_raw:.2f}s → final {final_dur:.2f}s", flush=True)

    parts = []
    for i, dur in enumerate(clip_durs):
        parts.append(
            f"[{i}:v]trim=duration={dur},setpts=PTS-STARTPTS,fps=30,setsar=1[v{i}]"
        )
    parts.append("".join(f"[v{i}]" for i in range(len(brolls))) + f"concat=n={len(brolls)}:v=1:a=0[catv]")
    # Trim concat to final voice length so video doesn't run past audio.
    parts.append(f"[catv]trim=duration={final_dur},setpts=PTS-STARTPTS[trimv]")
    # ffmpeg's filter parser chokes on paths with spaces ("Agency Dashboard"
    # in this repo's path). Workaround: stage the ass file to /tmp where the
    # path has no spaces, and reference it by absolute path.
    ass_staged = Path(f"/tmp/roadking_captions_{os.getpid()}.ass")
    shutil.copy(ass, ass_staged)

    voice_idx = len(brolls)
    music_idx = voice_idx + 1

    if avatar is not None and mask is not None and glow is not None:
        # Captions feed into avatar overlay.
        parts.append(f"[trimv]ass={ass_staged}[capv]")
        avatar_idx = music_idx + 1
        mask_idx = avatar_idx + 1
        glow_idx = mask_idx + 1
        parts.append(
            f"[{avatar_idx}:v]trim=duration={final_dur},setpts=PTS-STARTPTS,"
            f"scale={PIP_SIZE}:{PIP_SIZE}:flags=lanczos,format=yuva420p[av_s]"
        )
        parts.append(f"[{mask_idx}:v]format=gray[mk]")
        parts.append(f"[av_s][mk]alphamerge[av_rounded]")
        avatar_x = PIP_MARGIN_X
        avatar_y = PIP_MARGIN_TOP
        glow_x = PIP_MARGIN_X - PIP_GLOW_PAD
        glow_y = PIP_MARGIN_TOP - PIP_GLOW_PAD
        parts.append(f"[capv][{glow_idx}:v]overlay=W-w-({glow_x}):{glow_y}[main_glow]")
        parts.append(f"[main_glow][av_rounded]overlay=W-w-{avatar_x}:{avatar_y}[outv]")
    else:
        # No avatar — caption filter outputs directly to [outv].
        parts.append(f"[trimv]ass={ass_staged}[outv]")

    from audio_master import broadcast_ad_chain
    master_parts, _ = broadcast_ad_chain(voice_idx, music_idx)
    parts.extend(master_parts)

    cmd = [FFMPEG, "-y"]
    for p in brolls:
        cmd += ["-i", str(p)]
    cmd += ["-i", str(voice), "-i", str(music)]
    if avatar is not None and mask is not None and glow is not None:
        cmd += ["-i", str(avatar), "-i", str(mask), "-i", str(glow)]
    cmd += [
        "-filter_complex", ";".join(parts),
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-t", str(final_dur),
        "-movflags", "+faststart",
        str(final),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3500:], flush=True)
        raise RuntimeError("ffmpeg composite failed")
    print(f"[ffmpeg] done: {final.name} ({final.stat().st_size:,} B)", flush=True)
    return final


# ----------------------------------------------------------------------
# Telegram
# ----------------------------------------------------------------------
def telegram_send(video: Path, caption: str = "") -> None:
    print(f"[telegram] uploading {video.name} ({video.stat().st_size:,} B)", flush=True)
    cmd = [
        "curl", "-s", "-F", f"chat_id={env('TELEGRAM_USER_ID')}",
        "-F", f"video=@{video}",
        "-F", f"caption={caption}",
        "-F", "supports_streaming=true",
        f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}/sendVideo",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    resp = json.loads(r.stdout) if r.stdout else {}
    if not resp.get("ok"):
        raise RuntimeError(f"telegram failed: {r.stdout} / {r.stderr}")
    print("[telegram] sent", flush=True)


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--variant", default="guarantee", choices=list(VARIANTS),
                    help="Which angle/script variant to render")
    ap.add_argument("--shared-dir", default=None,
                    help="Shared dir for cached brolls + music (default: --out-dir, but pass a parent dir to share across variants)")
    ap.add_argument("--broll-dir", default=str(Path.home() / "Downloads/drive-download-20260506T211749Z-3-003"),
                    help="Directory containing the local b-roll .MOV files")
    ap.add_argument("--no-telegram", action="store_true")
    ap.add_argument("--with-avatar", action="store_true",
                    help="Overlay HeyGen avatar PiP (default OFF — real drivers in b-roll already serve as spokesperson)")
    a = ap.parse_args()

    out = Path(a.out_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    shared = Path(a.shared_dir).expanduser() if a.shared_dir else out
    shared.mkdir(parents=True, exist_ok=True)
    broll_dir = Path(a.broll_dir).expanduser()
    if not broll_dir.exists():
        sys.exit(f"missing broll dir: {broll_dir}")

    ssml = VARIANTS[a.variant]
    print(f"[main] variant={a.variant}", flush=True)
    print(f"[out] {out}", flush=True)
    print(f"[shared] {shared}", flush=True)
    print(f"[broll] {broll_dir}", flush=True)

    # Build the per-variant clip sequence from CLIP_LIBRARY + VARIANT_CLIP_ORDER.
    # Each variant has its own ordering so the 4 reels look visually distinct.
    variant_clips = [CLIP_LIBRARY[i] for i in VARIANT_CLIP_ORDER[a.variant]]

    # Verify source clips exist
    missing = [name for name, _, _ in variant_clips if not (broll_dir / name).exists()]
    if missing:
        sys.exit(f"missing b-roll files in {broll_dir}: {missing}")

    print(f"[main] dispatching {len(variant_clips)} broll trims + voice + music in parallel "
          f"(variant order: {VARIANT_CLIP_ORDER[a.variant]})", flush=True)
    # Trimmed brolls go into VARIANT out dir (so each variant has its own
    # broll_1.mp4..broll_N.mp4 sequence — different orderings per variant).
    # Music stays in shared (always the same).
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=10) as ex:
        f_brolls = [
            ex.submit(prep_local_broll, i + 1, broll_dir / name, dur, start, out)
            for i, (name, dur, start) in enumerate(variant_clips)
        ]
        f_music = ex.submit(gen_music, shared)
        # Voice is variant-specific, lives in OUT dir
        f_voice = ex.submit(gen_voice, out, ssml)
        brolls = [f.result() for f in f_brolls]
        voice_path, alignment = f_voice.result()
        music_path = f_music.result()
    print(f"[main] phase 1 done in {int(time.time()-t0)}s", flush=True)

    avatar_path: Path | None = None
    mask_path: Path | None = None
    glow_path: Path | None = None
    if a.with_avatar:
        try:
            avatar_path = gen_heygen(voice_path, out)
            mask_path, glow_path = gen_pip_assets(out)
        except Exception as e:
            print(f"[heygen] FAILED — continuing without avatar: {e}", flush=True)
            avatar_path = mask_path = glow_path = None

    words = extract_words(alignment)
    words = merge_url_bundles(words)
    print(f"[caps] {len(words)} caption tokens (after URL merge)", flush=True)
    ass_path = out / "captions.ass"
    write_ass(words, ass_path)

    clip_durs = [d for _, d, _ in variant_clips]
    final = composite(brolls, voice_path, music_path, ass_path,
                      avatar_path, mask_path, glow_path, clip_durs, out)

    if not a.no_telegram:
        telegram_send(final, caption=f"{BRAND_NAME} — '{a.variant}' variant. 9:16, real b-roll.")

    print(f"[done] {final}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
