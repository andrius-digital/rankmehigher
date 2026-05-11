#!/usr/bin/env python3
"""AZFS branding explainer — 9:16 25s video.

No avatar. AI b-roll (truck shots, Fal Kling) + AI music (Fal stable-audio)
+ ElevenLabs voiceover (Young Jamal) + scene-timed text overlays.

Output: pipelines/ugc-ad/output/azfs_<timestamp>/azfs_final.mp4

Env vars: FAL_KEY, ELEVENLABS_API_KEY (read from project root .env)
"""

from __future__ import annotations

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

ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = ROOT / ".env"
for line in ENV_FILE.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    os.environ.setdefault(k.strip(), v.strip())

FAL_KEY = os.environ["FAL_KEY"]
EL_KEY = os.environ["ELEVENLABS_API_KEY"]
VOICE_ID = "6OzrBCQf8cjERkYgzSg8"  # Young Jamal

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT = Path(__file__).resolve().parent / "output" / f"azfs_{STAMP}"
OUT.mkdir(parents=True, exist_ok=True)
print(f"[out] {OUT}", flush=True)

# ----------------------------------------------------------------------
# Script (SSML, ~25s with breaks)
# ----------------------------------------------------------------------
SSML = (
    'Tired of waiting weeks to get paid? <break time="400ms"/>'
    'Brokers running you 30, 60, even 90 days? <break time="500ms"/>'
    'AZFS pays you in 24 hours. <break time="300ms"/>'
    'Same-day funding on every load. <break time="300ms"/>'
    'Plus diesel discounts at the pump. <break time="500ms"/>'
    'Freight factoring and fuel cards, built for truckers. <break time="400ms"/>'
    'Fast cash. <break time="200ms"/>Fuel savings. <break time="500ms"/>'
    'A-Z-F-S dot com. <break time="200ms"/>Get started today.'
)

# ----------------------------------------------------------------------
# B-roll prompts — 5 × 5s clips, 9:16
# ----------------------------------------------------------------------
BROLL_PROMPTS = [
    # 0-5s: Hook
    "Cinematic shot of a red semi-truck driving on an empty American highway at golden hour, low angle near the tires, motion blur on the wheels, warm sunlight, dramatic clouds, vertical 9:16",
    # 5-10s: Pain — paperwork/frustration
    "Close-up of a male truck driver's tired hands holding paperwork inside a truck cab, sunlight through windshield, frustrated mood, vertical 9:16, cinematic",
    # 10-15s: Solution — fast cash
    "Macro shot of a smartphone screen showing a banking notification with a large positive dollar amount, held by hands of a man in a flannel shirt, vertical 9:16, cinematic warm lighting",
    # 15-20s: Fuel discounts
    "Wide cinematic shot of a semi-truck pulling into a fuel station at dusk, neon truck stop signs glowing, americana style, vertical 9:16, gritty",
    # 20-25s: CTA — hopeful
    "Aerial drone shot following a single red semi-truck driving down a long American highway toward a sunset horizon, cinematic, hopeful, vertical 9:16",
]

MUSIC_PROMPT = (
    "Uplifting motivational instrumental, mid-tempo, americana, country-rock fusion, "
    "no vocals, hopeful driving rhythm, light percussion build, cinematic, 30 seconds"
)

# Per-scene text overlays
SCENES = [
    (0.0,  5.0,  "TIRED OF WAITING\\NWEEKS TO GET PAID?"),
    (5.0,  10.0, "30, 60, 90 DAYS?"),
    (10.0, 15.0, "PAID IN 24 HOURS"),
    (15.0, 20.0, "+ DIESEL DISCOUNTS"),
    (20.0, 25.0, "AZFSLLC.COM"),
]


# ----------------------------------------------------------------------
# Fal queue helpers
# ----------------------------------------------------------------------
def _fal_request(method: str, url: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body else None,
        method=method,
        headers={
            "Authorization": f"Key {FAL_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Fal {method} {url} → {e.code}: {body}") from None


def _app_namespace(model_id: str) -> str:
    """Fal queue status/result endpoints use only the app namespace, not the
    full submission path. e.g. submission `fal-ai/kling-video/v2.5-turbo/pro/text-to-video`
    has status URL keyed on `fal-ai/kling-video`.
    """
    parts = model_id.split("/")
    return "/".join(parts[:2])


def fal_submit(model_id: str, body: dict) -> str:
    return _fal_request("POST", f"https://queue.fal.run/{model_id}", body)["request_id"]


def fal_poll(model_id: str, request_id: str, label: str, max_wait: int = 600) -> dict:
    ns = _app_namespace(model_id)
    status_url = f"https://queue.fal.run/{ns}/requests/{request_id}/status"
    result_url = f"https://queue.fal.run/{ns}/requests/{request_id}"
    t0 = time.time()
    while time.time() - t0 < max_wait:
        s = _fal_request("GET", status_url)
        st = s.get("status")
        elapsed = int(time.time() - t0)
        print(f"[{label}] {elapsed:>3}s  {st}", flush=True)
        if st == "COMPLETED":
            return _fal_request("GET", result_url)
        if st in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"[{label}] {st}: {s}")
        time.sleep(8)
    raise RuntimeError(f"[{label}] timeout after {max_wait}s")


def fal_video(idx: int, prompt: str) -> Path:
    label = f"broll{idx}"
    model = "fal-ai/kling-video/v2.5-turbo/pro/text-to-video"
    print(f"[{label}] submit: {prompt[:60]}...", flush=True)
    rid = fal_submit(model, {
        "prompt": prompt,
        "duration": "5",
        "aspect_ratio": "9:16",
    })
    r = fal_poll(model, rid, label)
    url = r["video"]["url"]
    p = OUT / f"broll_{idx}.mp4"
    urllib.request.urlretrieve(url, p)
    print(f"[{label}] saved: {p.name} ({p.stat().st_size:,} bytes)", flush=True)
    return p


def fal_music() -> Path:
    label = "music"
    model = "fal-ai/stable-audio-25/text-to-audio"
    print(f"[{label}] submit", flush=True)
    rid = fal_submit(model, {
        "prompt": MUSIC_PROMPT,
        "seconds_total": 30,
    })
    r = fal_poll(model, rid, label)
    url = r["audio_file"]["url"]
    p = OUT / "music.wav"
    urllib.request.urlretrieve(url, p)
    print(f"[{label}] saved: {p.name} ({p.stat().st_size:,} bytes)", flush=True)
    return p


def el_voice() -> Path:
    label = "voice"
    print(f"[{label}] generating with Young Jamal", flush=True)
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
        data=json.dumps({
            "text": SSML,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8,
                "style": 0.4,
                "use_speaker_boost": True,
            },
        }).encode(),
        headers={"xi-api-key": EL_KEY, "Content-Type": "application/json"},
    )
    p = OUT / "voiceover.mp3"
    try:
        with urllib.request.urlopen(req, timeout=120) as r, open(p, "wb") as f:
            f.write(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"ElevenLabs failed: {e.code} {e.read().decode()}")
    print(f"[{label}] saved: {p.name} ({p.stat().st_size:,} bytes)", flush=True)
    return p


# ----------------------------------------------------------------------
# Composite
# ----------------------------------------------------------------------
def ts(s: float) -> str:
    h = int(s // 3600)
    s -= h * 3600
    m = int(s // 60)
    s -= m * 60
    return f"{h}:{int(m):02d}:{s:05.2f}"


def write_captions(path: Path) -> None:
    # Two styles: white body text + a brand-red CTA
    ass = (
        "[Script Info]\n"
        "ScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        # White text, black outline + drop shadow, large
        "Style: Default,Arial Black,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,2,80,80,260,1\n"
        # Red brand text for CTA, slightly larger
        "Style: Brand,Arial Black,140,&H002626DC,&H002626DC,&H00FFFFFF,&H80000000,-1,0,0,0,100,100,0,0,1,7,2,2,80,80,360,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    for i, (s, e, text) in enumerate(SCENES):
        style = "Brand" if i == len(SCENES) - 1 else "Default"
        ass += f"Dialogue: 0,{ts(s)},{ts(e)},{style},,0,0,0,,{text}\n"
    path.write_text(ass)


def composite(brolls: list[Path], voice: Path, music: Path) -> Path:
    print("[composite] building captions", flush=True)
    ass_path = OUT / "captions.ass"
    write_captions(ass_path)

    final = OUT / "azfs_final.mp4"

    # filter_complex: trim each broll to 5s, scale+crop to 1080x1920, concat,
    # then burn captions; mix voice over music (music ducked to 12%).
    filter_parts: list[str] = []
    for i in range(len(brolls)):
        filter_parts.append(
            f"[{i}:v]trim=duration=5,setpts=PTS-STARTPTS,"
            f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"setsar=1,fps=30[v{i}]"
        )
    concat_inputs = "".join(f"[v{i}]" for i in range(len(brolls)))
    filter_parts.append(f"{concat_inputs}concat=n={len(brolls)}:v=1:a=0[catv]")
    filter_parts.append(f"[catv]ass={ass_path}[outv]")

    voice_idx = len(brolls)
    music_idx = voice_idx + 1
    filter_parts.append(f"[{voice_idx}:a]volume=1.0[av]")
    filter_parts.append(f"[{music_idx}:a]volume=0.13,apad[am]")
    filter_parts.append(f"[av][am]amix=inputs=2:duration=first:dropout_transition=0[outa]")

    cmd = ["ffmpeg", "-y"]
    for p in brolls:
        cmd += ["-i", str(p)]
    cmd += ["-i", str(voice), "-i", str(music)]
    cmd += [
        "-filter_complex", ";".join(filter_parts),
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-t", "25",
        "-movflags", "+faststart",
        str(final),
    ]
    print("[composite] running ffmpeg", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3000:], flush=True)
        raise RuntimeError("ffmpeg failed")
    return final


# ----------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------
def main() -> int:
    print("[main] dispatching all AI jobs in parallel...", flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=8) as ex:
        f_brolls = [ex.submit(fal_video, i + 1, p) for i, p in enumerate(BROLL_PROMPTS)]
        f_music = ex.submit(fal_music)
        f_voice = ex.submit(el_voice)
        try:
            brolls = [f.result() for f in f_brolls]
            music = f_music.result()
            voice = f_voice.result()
        except Exception as e:
            print(f"[main] FAIL: {e}", flush=True)
            return 1

    print(f"[main] all assets ready in {int(time.time()-t0)}s", flush=True)
    final = composite(brolls, voice, music)
    print(f"[done] {final}  ({final.stat().st_size:,} bytes)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
