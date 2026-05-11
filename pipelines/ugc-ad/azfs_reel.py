#!/usr/bin/env python3
"""AZFS branding reel — CDL-Agency-style word-by-word captions.

Reuses pre-generated truck b-rolls (Fal Kling). Generates fresh:
- ElevenLabs voiceover (Young Jamal) WITH per-character alignment
- Fal stable-audio music (country/pop-rock for truckers)

Composites with the same caption flow as ugc_pipeline.py (Arial Black 140pt
white, word-timed, lower third). Burns subtitles via libass (`ass=` filter)
— so this script is intended to run inside the Hermes gateway container,
which has libass-enabled ffmpeg. It will also work on any host with libass
(e.g. ffmpeg installed via the official static builds).

Required env vars: FAL_KEY, ELEVENLABS_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID
Inputs: 5× broll_*.mp4 (1080x1920 or close) in --brolls-dir
Output: <out_dir>/azfs_reel_final.mp4 + auto-uploaded to Telegram

Usage:
    python3 azfs_reel.py --brolls-dir /opt/data/artifacts/azfs --out-dir /opt/data/artifacts/azfs/run
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------
VOICE_ID = "6OzrBCQf8cjERkYgzSg8"  # Young Jamal (CDL Agency house voice)
# SPEED = 1.0 — DO NOT speed up the audio. The HeyGen avatar is lip-synced
# to the original-pace voice; any atempo desync the lips. Also the user
# preferred slower-paced reels for AZFS.
SPEED = 1.0

SSML = (
    'Diesel prices killing your profits? <break time="400ms"/>'
    'AZFS gives you up to two dollars off every gallon. <break time="500ms"/>'
    'Save thousands per truck, every year. <break time="400ms"/>'
    'Three thousand truck stops, nationwide. <break time="400ms"/>'
    'No card. <break time="200ms"/>No fees. <break time="200ms"/>No catch. <break time="500ms"/>'
    'Discount hits automatically when you fuel up. <break time="500ms"/>'
    'Visit A Zee Eff Ess El El See dot com.'
)

MUSIC_PROMPT = (
    "Upbeat country-rock instrumental for truckers, electric guitar riffs, "
    "driving 4/4 rhythm, mid-tempo americana, gritty hopeful energy, "
    "no vocals, full kit drums, 30 seconds"
)

# ASS caption style — MATCHES the reference CDL reel (cdl_v20.mp4) exactly.
# Arial Black 140pt, pure white, NO outline, NO shadow. Bold=-1 (true).
# Position: Alignment=2 (bottom-center) with MarginV=750 in a 1920-tall frame
# = text appears mid-screen at ~y=1170. Word-per-caption, ALL CAPS via display().
#
# This is the canonical UGC-reel style. DO NOT add outline/shadow even if the
# text washes out on bright shots — the clean look is the brand. If a shot is
# truly unreadable, regenerate the b-roll, don't change the caption style.
ASS_STYLE = (
    "Style: Default,Arial Black,140,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,"
    "&HFF000000,-1,0,0,0,100,100,0,0,3,0,0,2,60,60,750,1"
)

CAPTION_DISPLAY_OVERRIDES = {
    "azfs": "AZFS",
    "azfsllc.com": "AZFSLLC.COM",
    "a-z-f-s": "AZFS",
    # Phonetic spellings used in SSML so ElevenLabs pronounces letters
    # correctly. On screen we want each to read as the actual letter.
    "zee": "Z",
    "eff": "F",
    "ess": "S",
    "el": "L",
    "see": "C",
}

# URL/domain bundles: when these consecutive token sequences appear in the
# transcribed words, merge them into ONE caption that displays on screen for
# the full duration spanning all those tokens. Avoids ugly letter-per-frame
# spelling like A → Z → F → S → L → L → C → DOT → COM.
# Sequences are lowercase tokens (after rstrip ".,!?"). Order matters when
# multiple patterns could match — longest is tried first.
URL_BUNDLES: list[tuple[tuple[str, ...], str]] = [
    # AZFS LLC website
    (("a", "zee", "eff", "ess", "el", "el", "see", "dot", "com"), "AZFSLLC.COM"),
    # CDL Agency website (in case it ever shows up in a script)
    (("see", "dee", "el", "agency", "dot", "com"), "CDLAGENCY.COM"),
    (("see", "dee", "el", "dot", "com"), "CDL.COM"),
]

# HeyGen avatar — picture-in-picture, Loom-style square in bottom-right
# corner. Use the UNBRANDED CDL Agency avatar so the CDL polo emblem doesn't
# appear in AZFS-branded content.
AVATAR_ID = os.environ.get(
    "HEYGEN_AZFS_AVATAR_ID",  # allow per-brand override
    os.environ.get("HEYGEN_CDL_AVATAR_ID_UNBRANDED", "54b1e308527b4d56b2ef0824a12ce628"),
)
PIP_SIZE = 360  # avatar overlay size in px (square, before scale)
PIP_RADIUS = 32  # rounded-corner radius (Loom-ish vibe)
PIP_MARGIN = 60  # offset from bottom-right corner (room for glow halo)
PIP_GLOW_PAD = 60  # halo extends this many px around the avatar on each side


# ----------------------------------------------------------------------
# Helpers
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
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {url} → {e.code}: {e.read().decode('utf-8', 'replace')}") from None


# ----------------------------------------------------------------------
# Fal queue
# ----------------------------------------------------------------------
def fal_app_namespace(model_id: str) -> str:
    return "/".join(model_id.split("/")[:2])


def fal_run(model_id: str, body: dict, label: str, max_wait: int = 600) -> dict:
    fal_key = env("FAL_KEY")
    h = {"Authorization": f"Key {fal_key}", "Content-Type": "application/json"}
    submit = http_json("POST", f"https://queue.fal.run/{model_id}", h, body)
    rid = submit["request_id"]
    ns = fal_app_namespace(model_id)
    print(f"[{label}] submitted: {rid}", flush=True)
    t0 = time.time()
    while time.time() - t0 < max_wait:
        s = http_json("GET", f"https://queue.fal.run/{ns}/requests/{rid}/status", h)
        st = s.get("status")
        print(f"[{label}] {int(time.time()-t0):>3}s  {st}", flush=True)
        if st == "COMPLETED":
            return http_json("GET", f"https://queue.fal.run/{ns}/requests/{rid}", h)
        if st in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"[{label}] {st}: {s}")
        time.sleep(8)
    raise RuntimeError(f"[{label}] timeout {max_wait}s")


def gen_music(out: Path) -> Path:
    p = out / "music.wav"
    if p.exists() and p.stat().st_size > 100_000:
        print(f"[music] reusing existing {p.name} ({p.stat().st_size:,} B)", flush=True)
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


# ----------------------------------------------------------------------
# ElevenLabs voice + alignment
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# PiP mask + glow assets (generated once per run)
# ----------------------------------------------------------------------
def gen_pip_assets(out: Path) -> tuple[Path, Path]:
    """Generate two PNGs used to make the avatar PiP look like a glowing
    rounded-corner Loom card:
      - pip_mask.png : grayscale rounded-square mask for alphamerge with avatar
      - pip_glow.png : RGBA soft white halo painted around the rounded shape
    """
    from PIL import Image, ImageDraw, ImageFilter

    # Mask — grayscale, white interior with rounded corners, black outside.
    mask = Image.new("L", (PIP_SIZE, PIP_SIZE), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, PIP_SIZE - 1, PIP_SIZE - 1),
                         radius=PIP_RADIUS, fill=255)
    mask_path = out / "pip_mask.png"
    mask.save(mask_path)

    # Glow — RGBA halo, transparent except for a soft white blur ring.
    halo_w = PIP_SIZE + 2 * PIP_GLOW_PAD
    glow = Image.new("RGBA", (halo_w, halo_w), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    # Slightly larger rounded rectangle, soft white at moderate alpha
    gd.rounded_rectangle(
        (PIP_GLOW_PAD - 6, PIP_GLOW_PAD - 6,
         PIP_GLOW_PAD + PIP_SIZE + 5, PIP_GLOW_PAD + PIP_SIZE + 5),
        radius=PIP_RADIUS + 8, fill=(255, 255, 255, 180),
    )
    # Heavy blur — that's the glow
    glow = glow.filter(ImageFilter.GaussianBlur(radius=18))
    # Punch a hole where the avatar will sit so the glow reads as a halo
    # rather than a solid card behind the avatar.
    hole = Image.new("L", (halo_w, halo_w), 0)
    ImageDraw.Draw(hole).rounded_rectangle(
        (PIP_GLOW_PAD, PIP_GLOW_PAD,
         PIP_GLOW_PAD + PIP_SIZE - 1, PIP_GLOW_PAD + PIP_SIZE - 1),
        radius=PIP_RADIUS, fill=255,
    )
    from PIL import ImageChops
    inv_hole = Image.eval(hole, lambda v: 255 - v)
    _, _, _, glow_alpha = glow.split()
    glow.putalpha(ImageChops.multiply(glow_alpha, inv_hole))

    glow_path = out / "pip_glow.png"
    glow.save(glow_path)
    print(f"[pip] mask + glow assets ready ({PIP_SIZE}px, glow {halo_w}px)", flush=True)
    return mask_path, glow_path


# ----------------------------------------------------------------------
# HeyGen talking-photo avatar
# ----------------------------------------------------------------------
def gen_heygen(voice_path: Path, out: Path) -> Path:
    """Generate a HeyGen talking-photo video lip-syncing the voiceover.

    Returns the path to the auto-cropped square (1:1) clip ready for PiP overlay.
    """
    import fal_client  # local import — only needed for HeyGen step

    hg_key = env("HEYGEN_API_KEY")
    print(f"[heygen] uploading voice to fal for public URL", flush=True)
    audio_url = fal_client.upload_file(str(voice_path))
    print(f"[heygen] audio_url ready", flush=True)

    print(f"[heygen] generating avatar (id={AVATAR_ID})", flush=True)
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
                  {"X-Api-Key": hg_key, "Content-Type": "application/json"}, body)
    vid_id = r["data"]["video_id"]
    print(f"[heygen] video_id={vid_id}, polling...", flush=True)
    t0 = time.time()
    raw_path = out / "heygen_raw.mp4"
    while time.time() - t0 < 600:
        time.sleep(10)
        s = http_json("GET", f"https://api.heygen.com/v1/video_status.get?video_id={vid_id}",
                      {"X-Api-Key": hg_key})["data"]
        st = s.get("status")
        print(f"[heygen] {int(time.time()-t0):>3}s  {st}", flush=True)
        if st == "completed":
            urllib.request.urlretrieve(s["video_url"], raw_path)
            print(f"[heygen] saved raw {raw_path.name} ({raw_path.stat().st_size:,} B)", flush=True)
            break
        if st == "failed":
            raise RuntimeError(f"[heygen] FAILED: {s.get('error')}")
    else:
        raise RuntimeError("[heygen] timeout")

    # Auto-crop white letterbox to find content bounds, then scale to PIP_SIZE.
    # Same pixel-scan logic as compose_broll.py / postprocess_ugc.py.
    from PIL import Image
    sample = out / "heygen_sample.jpg"
    subprocess.run(
        ["ffmpeg", "-y", "-ss", "1.5", "-i", str(raw_path), "-vframes", "1", str(sample)],
        capture_output=True, check=True,
    )
    im = Image.open(sample).convert("RGB")
    W, H = im.size

    def row_avg(y: int) -> tuple[float, float, float]:
        pix = list(im.crop((0, y, W, y + 1)).getdata())
        return tuple(sum(c) / len(c) for c in zip(*pix))

    # Find first non-white row from top + bottom (>235 = "white-ish letterbox")
    top_y = next((y for y in range(0, H, 2) if not all(c > 235 for c in row_avg(y))), 0)
    bot_y = next((y for y in range(H - 1, -1, -2) if not all(c > 235 for c in row_avg(y))), H - 1)
    ch = (bot_y - top_y + 1) & ~1  # even
    cw = ch  # square 1:1 for PiP
    cx = (W - cw) // 2
    cy = top_y
    print(f"[heygen] content bounds: top={top_y} bot={bot_y} → crop {cw}x{ch} @ ({cx},{cy})", flush=True)

    cropped = out / "heygen_pip.mp4"
    # Crop content + scale to PiP size + ensure even dims
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw_path),
        "-vf", f"crop={cw}:{ch}:{cx}:{cy},scale={PIP_SIZE}:{PIP_SIZE}:flags=lanczos,setsar=1",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-an",  # drop audio — voice comes from main mix
        str(cropped),
    ], capture_output=True, check=True)
    print(f"[heygen] PiP {cropped.name} ({cropped.stat().st_size:,} B)", flush=True)
    return cropped


def gen_voice(out: Path) -> tuple[Path, dict]:
    el_key = env("ELEVENLABS_API_KEY")
    print("[voice] generating Young Jamal with timestamps", flush=True)
    body = {
        "text": SSML,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.4,
            "use_speaker_boost": True,
        },
    }
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/with-timestamps",
        data=json.dumps(body).encode(),
        headers={"xi-api-key": el_key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read())
    import base64

    mp3 = base64.b64decode(data["audio_base64"])
    p = out / "voiceover.mp3"
    p.write_bytes(mp3)
    align = data["alignment"]
    (out / "alignment.json").write_text(json.dumps(align, indent=2))
    print(f"[voice] saved {p.name} ({p.stat().st_size:,} B)", flush=True)
    return p, align


# ----------------------------------------------------------------------
# Word extraction from char-level alignment (matches ugc_pipeline.py)
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
    # Hold each word until the next starts (eliminates dark gap), cap 0.4s
    for i in range(len(words) - 1):
        words[i]["end"] = min(words[i + 1]["start"], words[i]["end"] + 0.40)
    return words


def display(text: str) -> str:
    t = text.rstrip(".,!?")
    o = CAPTION_DISPLAY_OVERRIDES.get(t.lower())
    if o:
        return o
    return t.upper() if t else text.upper()


def merge_url_bundles(words: list[dict]) -> list[dict]:
    """Collapse consecutive single-letter / phonetic-letter words that spell a
    domain (defined in URL_BUNDLES) into ONE caption. Prevents ugly letter-
    per-frame display of URLs like A → Z → F → S → L → L → C → DOT → COM.
    Tries the longest pattern first."""
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
                out.append({
                    "text": display_text,
                    "start": words[i]["start"],
                    "end": words[i + n - 1]["end"],
                })
                i += n
                matched = True
                break
        if not matched:
            out.append(words[i])
            i += 1
    return out


def write_ass(words: list[dict], path: Path) -> None:
    def ts(sec: float) -> str:
        s = sec / SPEED  # display time scales with audio speed
        h = int(s // 3600)
        s -= h * 3600
        m = int(s // 60)
        s -= m * 60
        return f"{h}:{int(m):02d}:{s:05.2f}"

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
        body += f"Dialogue: 0,{ts(w['start'])},{ts(w['end'])},Default,,0,0,0,,{display(w['text'])}\n"
    path.write_text(body)


# ----------------------------------------------------------------------
# Composite
# ----------------------------------------------------------------------
def composite(brolls: list[Path], voice: Path, music: Path, ass: Path,
              avatar: Path | None, mask: Path | None, glow: Path | None,
              out: Path) -> Path:
    final = out / "azfs_reel_final.mp4"
    # Probe voice duration so we can end the video exactly when the voice ends.
    voice_raw = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(voice)],
        capture_output=True, text=True, check=True).stdout.strip())
    final_dur = round(voice_raw / SPEED + 0.30, 2)
    print(f"[ffmpeg] voice {voice_raw:.2f}s → final video {final_dur:.2f}s "
          f"(SPEED={SPEED})", flush=True)

    parts = []
    # Each broll: trim 5s → fit 9:16 → SLOW ZOOM (1.0 → 1.04 over 5s) → crop.
    for i in range(len(brolls)):
        parts.append(
            f"[{i}:v]trim=duration=5,setpts=PTS-STARTPTS,"
            f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"scale='trunc(1080*(1+0.04*t/5)/2)*2':'trunc(1920*(1+0.04*t/5)/2)*2':eval=frame:flags=lanczos,"
            f"crop=1080:1920:(iw-1080)/2:(ih-1920)/2,"
            f"setsar=1,fps=30[v{i}]"
        )
    parts.append("".join(f"[v{i}]" for i in range(len(brolls))) + f"concat=n={len(brolls)}:v=1:a=0[catv]")
    parts.append(f"[catv]ass={ass}[capv]")

    voice_idx = len(brolls)
    music_idx = voice_idx + 1

    if avatar is not None and mask is not None and glow is not None:
        avatar_idx = music_idx + 1
        mask_idx = avatar_idx + 1
        glow_idx = mask_idx + 1
        # Avatar pipeline:
        # 1. Trim to final duration, scale to PIP_SIZE square, give it an alpha channel.
        # 2. Combine with mask via alphamerge → rounded corners (transparent outside).
        parts.append(
            f"[{avatar_idx}:v]trim=duration={final_dur},setpts=PTS-STARTPTS,"
            f"scale={PIP_SIZE}:{PIP_SIZE}:flags=lanczos,format=yuva420p[av_s]"
        )
        # Mask is loaded as image — feed alphamerge the gray channel
        parts.append(f"[{mask_idx}:v]format=gray[mk]")
        parts.append(f"[av_s][mk]alphamerge[av_rounded]")

        # Glow goes UNDER the avatar. Position so the halo is centered around
        # the avatar (the glow image is PIP_GLOW_PAD wider on each side).
        glow_x_off = PIP_MARGIN - PIP_GLOW_PAD
        glow_y_off = PIP_MARGIN - PIP_GLOW_PAD
        parts.append(
            f"[capv][{glow_idx}:v]overlay="
            f"W-w-({glow_x_off}):H-h-({glow_y_off})[main_glow]"
        )
        # Avatar on top, at the original PIP position
        parts.append(
            f"[main_glow][av_rounded]overlay="
            f"W-w-{PIP_MARGIN}:H-h-{PIP_MARGIN}[outv]"
        )
    else:
        parts.append("[capv]copy[outv]")

    # Broadcast-ad mastering: vocal forward + sidechain-ducked music + -14 LUFS.
    # Shared preset in audio_master.py so all reels use the same chain.
    from audio_master import broadcast_ad_chain
    master_parts, _ = broadcast_ad_chain(voice_idx, music_idx)
    parts.extend(master_parts)

    cmd = ["ffmpeg", "-y"]
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
    print("[ffmpeg] running...", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3500:], flush=True)
        raise RuntimeError("ffmpeg failed")
    print(f"[ffmpeg] done: {final}  {final.stat().st_size:,} B", flush=True)
    return final


# ----------------------------------------------------------------------
# Telegram
# ----------------------------------------------------------------------
def telegram_send(video: Path, caption: str = "") -> None:
    tok = env("TELEGRAM_BOT_TOKEN")
    chat = env("TELEGRAM_USER_ID")
    print(f"[telegram] uploading {video.name} ({video.stat().st_size:,} B)", flush=True)
    cmd = [
        "curl", "-s", "-F", f"chat_id={chat}",
        "-F", f"video=@{video}",
        "-F", f"caption={caption}",
        "-F", "supports_streaming=true",
        f"https://api.telegram.org/bot{tok}/sendVideo",
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
    ap.add_argument("--brolls-dir", required=True, help="dir with broll_1.mp4..broll_5.mp4")
    ap.add_argument("--out-dir", help="output dir (default: <brolls-dir>/run_<stamp>)")
    ap.add_argument("--no-telegram", action="store_true")
    ap.add_argument("--no-avatar", action="store_true", help="skip HeyGen PiP overlay")
    a = ap.parse_args()

    brolls_dir = Path(a.brolls_dir)
    brolls = [brolls_dir / f"broll_{i}.mp4" for i in range(1, 6)]
    missing = [str(p) for p in brolls if not p.exists()]
    if missing:
        sys.exit(f"missing brolls: {missing}")

    out = Path(a.out_dir or brolls_dir / f"run_{datetime.now():%Y%m%d_%H%M%S}")
    out.mkdir(parents=True, exist_ok=True)
    print(f"[out] {out}", flush=True)

    # Generate voice + music in parallel (HeyGen needs voice, runs after).
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_voice = ex.submit(gen_voice, out)
        f_music = ex.submit(gen_music, out)
        voice_path, alignment = f_voice.result()
        music_path = f_music.result()

    # HeyGen avatar (uses the voice we just generated). Skip via flag if
    # something goes wrong — we still want a deliverable reel.
    avatar_path: Path | None = None
    mask_path: Path | None = None
    glow_path: Path | None = None
    if not a.no_avatar:
        try:
            avatar_path = gen_heygen(voice_path, out)
            mask_path, glow_path = gen_pip_assets(out)
        except Exception as e:
            print(f"[heygen] FAILED — continuing without avatar: {e}", flush=True)
            avatar_path = mask_path = glow_path = None

    # Word-timed captions, then merge any URL letter-runs into single tokens
    words = extract_words(alignment)
    words = merge_url_bundles(words)
    print(f"[caps] {len(words)} caption tokens (after URL merge)", flush=True)
    ass_path = out / "captions.ass"
    write_ass(words, ass_path)

    # Composite (with rounded + glowing PiP avatar in bottom-right corner)
    final = composite(brolls, voice_path, music_path, ass_path,
                      avatar_path, mask_path, glow_path, out)

    # Deliver
    if not a.no_telegram:
        telegram_send(final, caption="AZFS reel — CDL-style captions, country-rock soundtrack. 25s, 9:16.")

    print(f"[done] {final}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
