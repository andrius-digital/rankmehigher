#!/usr/bin/env python3
"""MS Lines Corp — Owner Operator hiring reel (AI-generated).

Same pipeline as CDL/AZFS reels: 6 truck b-rolls (Fal Kling) + Young Jamal
voice + Fal stable-audio music + HeyGen PiP avatar (unbranded — there's no
MS-Lines-branded HeyGen avatar in the account) + canonical caption style +
broadcast-ad master chain.

Usage:
    python3 mslines_reel.py --out-dir /opt/data/artifacts/mslines-owner-op
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
# Brand config — MS Lines Corp, owner-op hiring
# ----------------------------------------------------------------------
BRAND_NAME = "MS Lines Corp"
VOICE_ID = "6OzrBCQf8cjERkYgzSg8"  # Young Jamal
SPEED = 1.0

# Offer terms come from user-provided spec (overrides any website mismatch):
#   78% gross · 0 deductions · 0 escrow · no hold on paycheck ·
#   remote orientation · fuel discounts · trailer included
SSML = (
    'Owner operators! <break time="500ms"/>'
    'Tired of working for less than you\'re worth? <break time="400ms"/>'
    'MS Lines is hiring. <break time="500ms"/>'
    'Seventy eight percent gross. <break time="400ms"/>'
    'Everything included. <break time="300ms"/>'
    'You pay zero from your pocket. <break time="500ms"/>'
    'Plus our fuel discount. <break time="500ms"/>'
    'Zero deductions. <break time="200ms"/>Zero escrow. <break time="200ms"/>'
    'No hold on your paycheck. <break time="500ms"/>'
    'You need two years Oh Tee Are experience '
    'and a clean driving record. <break time="500ms"/>'
    'Orientation done remote. <break time="300ms"/>Get rolling fast. <break time="500ms"/>'
    'Call or apply today at Em Ess Lines Corp dot com.'
)

# 6 b-roll prompts × 5s = 30s coverage
BROLL_PROMPTS = [
    # 0-5s — Hook: powerful 18-wheeler driving
    "Cinematic low-angle shot of a black semi-truck driving on an empty American highway at sunset, motion blur on tires, dramatic dust trail, vertical 9:16, americana, powerful",
    # 5-10s — Pain: empty wallet / frustrated owner-op
    "Cinematic close-up of a male owner-operator's hands holding an almost empty wallet inside a truck cab, frustrated mood, dim warm cab lighting, vertical 9:16, no readable text",
    # 10-15s — Solution: 78% / paycheck moment
    "Macro cinematic shot of male trucker hands counting a thick stack of US dollar bills on a wood table, warm dramatic lighting, motion blur on the bills, vertical 9:16, no readable text",
    # 15-20s — Trailer included / fuel
    "Cinematic shot of a clean modern semi-truck with a sleek matching trailer parked at a fuel station at golden hour, dramatic lighting, americana, vertical 9:16",
    # 20-25s — Remote orientation: phone signing
    "Cinematic close-up of a male trucker's hand signing a digital document on a smartphone inside a sunlit truck cab, warm light, focused, vertical 9:16, no readable UI text",
    # 25-30s — Get rolling
    "Aerial drone shot of a black semi-truck rolling fast down an open American interstate toward sunset horizon, cinematic, hopeful, vertical 9:16",
]

MUSIC_PROMPT = (
    "Upbeat motivational country-rock instrumental for truckers, electric guitar "
    "riffs, driving 4/4 rhythm, mid-tempo americana with full drums, gritty hopeful "
    "rebellious energy, no vocals, 30 seconds"
)

# Canonical UGC reel caption style (no outline, no shadow, mid-screen, Arial Black)
ASS_STYLE = (
    "Style: Default,Arial Black,140,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,"
    "&HFF000000,-1,0,0,0,100,100,0,0,3,0,0,2,60,60,750,1"
)

CAPTION_DISPLAY_OVERRIDES: dict[str, str] = {
    "ms": "MS",
    "mslinescorp.com": "MSLINESCORP.COM",
    # Phonetic spellings → letter display
    "em": "M",
    "ess": "S",
    "zee": "Z",
    "eff": "F",
    "el": "L",
    "see": "C",
}

URL_BUNDLES: list[tuple[tuple[str, ...], str]] = [
    # MS Lines URL: "Em Ess Lines Corp dot com" → "MSLINESCORP.COM"
    (("em", "ess", "lines", "corp", "dot", "com"), "MSLINESCORP.COM"),
    # Pretty number: "Seventy eight percent" → "78%"
    (("seventy", "eight", "percent"), "78%"),
    # Industry acronym: "Oh Tee Are" → "OTR"
    (("oh", "tee", "are"), "OTR"),
]

# Avatar — UNBRANDED CDL avatar (no MS-Lines-specific avatar exists in HeyGen).
# Avoids cross-brand emblem mismatch.
AVATAR_ID = os.environ.get(
    "HEYGEN_MSLINES_AVATAR_ID",
    os.environ.get(
        "HEYGEN_CDL_AVATAR_ID_UNBRANDED",
        "54b1e308527b4d56b2ef0824a12ce628",
    ),
)

# PiP placement — moved from bottom-right (covered by social-media UI overlays
# like Like/Comment buttons) to TOP-RIGHT, larger size, well inside the safe
# zone. Avatar now reads as a visible spokesperson, not a corner sticker.
PIP_SIZE = 480
PIP_RADIUS = 40
PIP_MARGIN_X = 60       # distance from right edge
PIP_MARGIN_TOP = 200    # distance from top (clears phone status bar / app chrome)
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
        with urllib.request.urlopen(req, timeout=120) as r:
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
# Asset generators
# ----------------------------------------------------------------------
def gen_broll(idx: int, prompt: str, out: Path) -> Path:
    label = f"broll{idx}"
    p = out / f"broll_{idx}.mp4"
    if p.exists() and p.stat().st_size > 100_000:
        print(f"[{label}] reusing {p.name}", flush=True)
        return p
    print(f"[{label}] submit: {prompt[:65]}...", flush=True)
    r = fal_run(
        "fal-ai/kling-video/v2.5-turbo/pro/text-to-video",
        {"prompt": prompt, "duration": "5", "aspect_ratio": "9:16"},
        label,
    )
    urllib.request.urlretrieve(r["video"]["url"], p)
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


def gen_voice(out: Path) -> tuple[Path, dict]:
    p = out / "voiceover.mp3"
    align_p = out / "alignment.json"
    if p.exists() and p.stat().st_size > 50_000 and align_p.exists():
        print(f"[voice] reusing {p.name} ({p.stat().st_size:,} B)", flush=True)
        return p, json.loads(align_p.read_text())
    print("[voice] generating Young Jamal with timestamps", flush=True)
    body = {
        "text": SSML,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            # Lower stability + higher style = more natural inflection, less
            # robotic monotone. Slightly less consistent take-to-take but
            # sounds like a real person, not TTS.
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

    p = out / "voiceover.mp3"
    p.write_bytes(base64.b64decode(data["audio_base64"]))
    align = data["alignment"]
    (out / "alignment.json").write_text(json.dumps(align, indent=2))
    print(f"[voice] saved {p.name} ({p.stat().st_size:,} B)", flush=True)
    return p, align


# ----------------------------------------------------------------------
# PiP mask + glow
# ----------------------------------------------------------------------
def gen_pip_assets(out: Path) -> tuple[Path, Path]:
    from PIL import Image, ImageDraw, ImageFilter, ImageChops

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
    print(f"[pip] mask + glow ready ({PIP_SIZE}px, glow {halo_w}px)", flush=True)
    return mask_path, glow_path


# ----------------------------------------------------------------------
# HeyGen avatar
# ----------------------------------------------------------------------
def _upload_audio_to_heygen(file_path: Path) -> str:
    print(f"[upload] uploading {file_path.name} to HeyGen asset CDN", flush=True)
    r = subprocess.run([
        "curl", "-s", "-X", "POST", "https://upload.heygen.com/v1/asset",
        "-H", f"X-Api-Key: {env('HEYGEN_API_KEY')}",
        "-H", "Content-Type: audio/mpeg",
        "--data-binary", f"@{file_path}",
    ], capture_output=True, text=True, check=True)
    try:
        resp = json.loads(r.stdout)
    except Exception:
        raise RuntimeError(f"heygen upload bad response: {r.stdout[:300]!r}")
    if resp.get("code") != 100 or "url" not in resp.get("data", {}):
        raise RuntimeError(f"heygen upload failed: {resp}")
    url = resp["data"]["url"]
    print(f"[upload] heygen asset URL: {url}", flush=True)
    return url


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
    print(f"[heygen] vid={vid_id}", flush=True)
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

    # Auto-crop white letterbox → square for PiP
    from PIL import Image
    sample = out / "heygen_sample.jpg"
    subprocess.run(["ffmpeg", "-y", "-ss", "1.5", "-i", str(raw),
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
    print(f"[heygen] content {cw}x{ch} @ ({cx},{cy})", flush=True)

    pip = out / "heygen_pip.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw),
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
        """Auto-shrink for long captions so they fit on a 1080-wide frame.
        Default style is Arial Black 140pt; a 10-char word is roughly the
        width limit. Each extra char shrinks the size by 8pt down to 90pt."""
        n = len(text)
        if n <= 10:
            return 0  # 0 means "use default style size"
        return max(90, 140 - (n - 10) * 8)

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
              out: Path) -> Path:
    final = out / "mslines_reel_final.mp4"
    voice_raw = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(voice)],
        capture_output=True, text=True, check=True).stdout.strip())
    final_dur = round(voice_raw / SPEED + 0.30, 2)
    print(f"[ffmpeg] voice {voice_raw:.2f}s → final {final_dur:.2f}s", flush=True)

    # Each clip: trim + fit-crop + slow zoom (8% over 5s — more visible than
    # the earlier 4%) + final crop. Then chain them with xfade cross-dissolves
    # instead of hard concat for a more cinematic feel.
    parts = []
    CLIP_DUR = 5.0
    XFADE_DUR = 0.5
    ZOOM_AMOUNT = 0.08
    for i in range(len(brolls)):
        parts.append(
            f"[{i}:v]trim=duration={CLIP_DUR},setpts=PTS-STARTPTS,"
            f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"scale='trunc(1080*(1+{ZOOM_AMOUNT}*t/{CLIP_DUR})/2)*2':'trunc(1920*(1+{ZOOM_AMOUNT}*t/{CLIP_DUR})/2)*2':eval=frame:flags=lanczos,"
            f"crop=1080:1920:(iw-1080)/2:(ih-1920)/2,"
            f"setsar=1,fps=30[v{i}]"
        )
    # xfade chain: each xfade overlaps the prior cumulative stream with the
    # next clip for XFADE_DUR seconds. Final stream label is `catv`.
    prev = "v0"
    for i in range(1, len(brolls)):
        offset = i * (CLIP_DUR - XFADE_DUR)  # when this transition starts
        out_label = "catv" if i == len(brolls) - 1 else f"c{i}"
        parts.append(
            f"[{prev}][v{i}]xfade=transition=fade:duration={XFADE_DUR}:offset={offset}[{out_label}]"
        )
        prev = out_label
    parts.append(f"[catv]ass={ass}[capv]")

    voice_idx = len(brolls)
    music_idx = voice_idx + 1

    if avatar is not None and mask is not None and glow is not None:
        avatar_idx = music_idx + 1
        mask_idx = avatar_idx + 1
        glow_idx = mask_idx + 1
        parts.append(
            f"[{avatar_idx}:v]trim=duration={final_dur},setpts=PTS-STARTPTS,"
            f"scale={PIP_SIZE}:{PIP_SIZE}:flags=lanczos,format=yuva420p[av_s]"
        )
        parts.append(f"[{mask_idx}:v]format=gray[mk]")
        parts.append(f"[av_s][mk]alphamerge[av_rounded]")
        # Top-right placement (was bottom-right; bottom is covered by Reels/TikTok UI).
        # Glow is wider than avatar by PIP_GLOW_PAD on each side, so its top-left
        # is shifted up + left by PIP_GLOW_PAD relative to the avatar.
        avatar_x_from_right = PIP_MARGIN_X
        avatar_y_from_top = PIP_MARGIN_TOP
        glow_x_from_right = PIP_MARGIN_X - PIP_GLOW_PAD
        glow_y_from_top = PIP_MARGIN_TOP - PIP_GLOW_PAD
        parts.append(f"[capv][{glow_idx}:v]overlay=W-w-({glow_x_from_right}):{glow_y_from_top}[main_glow]")
        parts.append(f"[main_glow][av_rounded]overlay=W-w-{avatar_x_from_right}:{avatar_y_from_top}[outv]")
    else:
        parts.append("[capv]copy[outv]")

    # Broadcast-ad master chain (vocal-forward, sidechain-ducked music, -14 LUFS)
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
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3500:], flush=True)
        raise RuntimeError("ffmpeg failed")
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
    ap.add_argument("--no-telegram", action="store_true")
    ap.add_argument("--no-avatar", action="store_true")
    a = ap.parse_args()

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    print(f"[out] {out}", flush=True)

    print(f"[main] dispatching {len(BROLL_PROMPTS)} brolls + voice + music in parallel", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=10) as ex:
        f_brolls = [ex.submit(gen_broll, i + 1, p, out) for i, p in enumerate(BROLL_PROMPTS)]
        f_voice = ex.submit(gen_voice, out)
        f_music = ex.submit(gen_music, out)
        brolls = [f.result() for f in f_brolls]
        voice_path, alignment = f_voice.result()
        music_path = f_music.result()
    print(f"[main] phase 1 done in {int(time.time()-t0)}s", flush=True)

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

    words = extract_words(alignment)
    words = merge_url_bundles(words)
    print(f"[caps] {len(words)} caption tokens (after URL merge)", flush=True)
    ass_path = out / "captions.ass"
    write_ass(words, ass_path)

    final = composite(brolls, voice_path, music_path, ass_path,
                      avatar_path, mask_path, glow_path, out)

    if not a.no_telegram:
        telegram_send(final, caption=f"{BRAND_NAME} — Owner Operator hiring reel. 9:16, AI-generated.")

    print(f"[done] {final}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
