#!/usr/bin/env python3
"""
v10 — add natural sentence pauses via SSML <break> tags + regen HeyGen to match.
Reuses v9 b-rolls (Kling v2.5 clips from latest artifacts).
"""
import os, sys, time, json, base64, subprocess, urllib.request
from pathlib import Path
from PIL import Image
import requests, fal_client

# SSML with <break> tags — eleven_multilingual_v2 supports these.
# Pause lengths vary by emotional beat instead of being uniform, so the
# cadence reads as human rather than metronomic: short punchy opener,
# long after the hook so it lands, quick pivot into the offer, medium
# breath after the qualifications list, longest pause right before the
# CTA to build anticipation.
SCRIPT_RAW = (
    "Looking for a CDLA job that actually pays? <break time=\"450ms\"/>"
    "We're hiring CDLA drivers right now. <break time=\"300ms\"/>"
    "2 years experience, <break time=\"80ms\"/>"
    "clean record, <break time=\"80ms\"/>"
    "no DUI, <break time=\"80ms\"/>"
    "no SAP. <break time=\"800ms\"/>"
    "Paid weekly, <break time=\"220ms\"/>"
    "real home time. <break time=\"500ms\"/>"
    "CDLA drivers — click the link below to get hired fast."
)

# Trucking acronyms that TTS should pronounce as WORDS (not spelled letter-by-letter).
# Writer keeps them uppercase in the script for readability; we lowercase them
# right before sending to TTS so ElevenLabs treats them as regular words.
# Captions re-uppercase via display() so viewers still see "SAP" etc.
#
# NOTE: earlier we tried SSML `<sub alias="sap">SAP</sub>` but eleven_multilingual_v2
# does NOT honor <sub> — it spelled the word out anyway. Direct lowercase
# substitution works reliably.
#
# Add more as needed: OTR, DOT, BOL stay uppercase (drivers spell those).
# SAP saga — tried <sub alias>, lowercase, <phoneme alphabet="ipa">. All failed
# for Young Jamal voice. This voice aggressively acronymizes. Final approach:
# DECOUPLE what TTS sees from what captions display.
#   - TTS text: "Saap" (phonetic spelling, forces word pronunciation)
#   - Captions: map back to "SAP" via DISPLAY_OVERRIDES on the caption side
#
# ACRONYM_TTS_SPELLING maps the display word (keep uppercase in scripts)
# to its phonetic TTS form. CAPTION_DISPLAY_OVERRIDES maps what the
# caption generator sees (lowercased TTS characters) back to the display form.
ACRONYM_TTS_SPELLING = {
    # "Sapp" is a common English surname (Warren Sapp) — models parse it
    # reliably as one syllable. Earlier "Saap" worked in V15 but regressed
    # to "sa-ip" sound in V16 due to model variance. "Sapp" is more stable.
    "SAP": "Sapp",
}
CAPTION_DISPLAY_OVERRIDES = {
    "sapp": "SAP",       # caption parser sees "sapp", display "SAP"
    "cdla": "CDL A",     # TTS says "CDLA" (one connected acronym), caption shows "CDL A"
}

def _normalize_trucking_acronyms(text):
    import re
    # "CDL A" → "CDLA" so trucker says it as one connected acronym (no gap
    # between "CDL" and "A"). Applies to CDL-A, CDL-B, etc.
    text = re.sub(r"\bCDL\s+([AB])\b", r"CDL\1", text)
    # SAP → Saap (word pronunciation, then caption override puts "SAP" back)
    for acr, tts_spelling in ACRONYM_TTS_SPELLING.items():
        text = re.sub(rf"\b{acr}\b", tts_spelling, text)
    return text

SCRIPT_SSML = _normalize_trucking_acronyms(SCRIPT_RAW)
# PLAIN version (for captions, after stripping SSML)
import re
SCRIPT_PLAIN = re.sub(r"<[^>]+>", "", SCRIPT_SSML).strip()

# Read voice + avatar from env so mobile .env edits propagate without code changes.
# Fallback to known-good IDs if env isn't set.
VOICE_ID  = os.environ.get("ELEVENLABS_CDL_VOICE_ID", "6OzrBCQf8cjERkYgzSg8")  # default: Young Jamal
AVATAR_ID = os.environ.get("HEYGEN_CDL_AVATAR_ID",    "4e1f282e54274850919da8f558a73190")  # default: branded CDL
EL_KEY = os.environ["ELEVENLABS_API_KEY"]
HG_KEY = os.environ["HEYGEN_API_KEY"]
SPEED = 1.10

# reuse b-rolls from v9 (latest artifacts before we create our own)
v9_dir = sorted(Path("/opt/data/artifacts/ugc").iterdir())[-1]
print(f"[reuse] b-rolls from {v9_dir}")
brolls_src = sorted(v9_dir.glob("broll_*.mp4"))
assert len(brolls_src) >= 2, "need 2 b-rolls from v9"
beat_wav = Path("/opt/data/artifacts/music/trap_fal.wav")

TS = time.strftime("%Y%m%d-%H%M%S")
OUT = Path(f"/opt/data/artifacts/ugc/{TS}")
OUT.mkdir(parents=True, exist_ok=True)
# link brolls into new out dir
for i, p in enumerate(brolls_src[:2], 1):
    dst = OUT / f"broll_{i}.mp4"
    dst.symlink_to(p) if not dst.exists() else None
brolls = sorted(OUT.glob("broll_*.mp4"))

# ─── 1. TTS with SSML ───────────────────────────────────────────────────
print(f"[tts] multilingual_v2  SSML w/ breaks")
t0 = time.time()
r = requests.post(
    f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/with-timestamps",
    headers={"xi-api-key": EL_KEY, "Content-Type": "application/json"},
    json={
        "text": SCRIPT_SSML,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "style": 0.4, "use_speaker_boost": True},
        "apply_text_normalization": "off",
    },
    timeout=60,
)
r.raise_for_status()
d = r.json()
(OUT / "voiceover.mp3").write_bytes(base64.b64decode(d["audio_base64"]))
(OUT / "alignment.json").write_text(json.dumps(d["alignment"]))
print(f"[tts]  ✓ {time.time()-t0:.1f}s  (MP3 {(OUT/'voiceover.mp3').stat().st_size//1024}KB)")

# ─── 2. HeyGen regen (match new audio) ──────────────────────────────────
audio_url = fal_client.upload_file(str(OUT / "voiceover.mp3"))
r = requests.post(
    "https://api.heygen.com/v2/video/generate",
    headers={"X-Api-Key": HG_KEY, "Content-Type": "application/json"},
    json={
        "video_inputs": [{
            "character": {"type": "talking_photo", "talking_photo_id": AVATAR_ID,
                          "talking_photo_style": "square", "talking_style": "expressive",
                          "expression": "happy"},
            "voice": {"type": "audio", "audio_url": audio_url},
        }],
        "dimension": {"width": 1440, "height": 2560},
    }, timeout=60,
)
vid_id = r.json()["data"]["video_id"]
print(f"[heygen] id={vid_id}")
t0 = time.time()
while True:
    time.sleep(10)
    s = requests.get(f"https://api.heygen.com/v1/video_status.get?video_id={vid_id}",
                     headers={"X-Api-Key": HG_KEY}, timeout=30).json()["data"]
    st = s.get("status")
    print(f"[heygen] {time.time()-t0:4.0f}s  {st}")
    if st == "completed":
        urllib.request.urlretrieve(s["video_url"], OUT / "heygen.mp4")
        break
    if st == "failed":
        print(f"[heygen] FAILED: {s.get('error')}"); sys.exit(1)

# ─── 3. Captions (one word at a time, plain white) ──────────────────────
# Skip characters that belong to SSML tags (<break ... />) — otherwise
# ElevenLabs' per-character alignment leaks them into captions as fake "words"
# like TIME="400MS"/>TIRED.
alignment = json.loads((OUT / "alignment.json").read_text())
chars = alignment["characters"]; starts = alignment["character_start_times_seconds"]; ends = alignment["character_end_times_seconds"]
words = []; buf = ""; wstart = 0; in_tag = False
for i, ch in enumerate(chars):
    if ch == "<":
        if buf.strip():
            words.append({"text": buf.strip(), "start": wstart, "end": ends[i-1] if i>0 else ends[i]})
        buf = ""
        in_tag = True
        continue
    if in_tag:
        if ch == ">":
            in_tag = False
        continue
    if buf == "": wstart = starts[i]
    if ch in (" ", "\n"):
        if buf.strip():
            words.append({"text": buf.strip(), "start": wstart, "end": ends[i-1] if i>0 else ends[i]})
        buf = ""
    else:
        buf += ch
if buf.strip():
    words.append({"text": buf.strip(), "start": wstart, "end": ends[-1]})

# Hold each word until the next one starts — eliminates the dark gap
# between words that reads as a fade-out. Cap lingering at 0.4s so long
# SSML breaks don't leave the last word hanging on screen.
for i in range(len(words) - 1):
    words[i]["end"] = min(words[i+1]["start"], words[i]["end"] + 0.40)

def display(w):
    t = w.rstrip(".,!?")
    # map phonetic/TTS spellings back to brand-consistent caption form
    # e.g. TTS said "Saap" (so TTS pronounced it as word), caption displays "SAP"
    override = CAPTION_DISPLAY_OVERRIDES.get(t.lower())
    if override:
        return override
    return t.upper() if t else w.upper()

def ts(sec):
    s = sec / SPEED
    h = int(s // 3600); s -= h*3600
    m = int(s // 60); s -= m*60
    return f"{h}:{int(m):02d}:{s:05.2f}"

ass = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,140,&H00FFFFFF,&H00FFFFFF,&H00FFFFFF,&HFF000000,-1,0,0,0,100,100,0,0,3,0,0,2,60,60,750,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
for w in words:
    ass += f"Dialogue: 0,{ts(w['start'])},{ts(w['end'])},Default,,0,0,0,,{display(w['text'])}\n"
(OUT / "captions.ass").write_text(ass)
print(f"[subs] {len(words)} words")

# ─── 4. Autocrop + composite (no zoompan — simple) ──────────────────────
probe = json.loads(subprocess.run(
    ["ffprobe","-v","error","-select_streams","v","-show_entries","stream=width,height","-of","json",str(OUT/"heygen.mp4")],
    capture_output=True, text=True, check=True).stdout)["streams"][0]
W, H = probe["width"], probe["height"]
subprocess.run(["ffmpeg","-y","-ss","3","-i",str(OUT/"heygen.mp4"),"-vframes","1",str(OUT/"sample.jpg")],
               capture_output=True, check=True)
im = Image.open(OUT/"sample.jpg").convert("RGB")
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
    ["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(OUT/"voiceover.mp3")],
    capture_output=True, text=True, check=True).stdout.strip())
final_dur = voice_dur / SPEED
print(f"[timing] voice={voice_dur:.2f}s  final={final_dur:.2f}s")

BROLL_DUR = 3.0
slots = [(2.0, 2.0+BROLL_DUR), (6.5, 6.5+BROLL_DUR)]
slots = [(s, min(e, final_dur)) for s, e in slots if s < final_dur]

segs = []
t = 0.0
for i, (s, e) in enumerate(slots):
    if s > t: segs.append(("main", t, s))
    segs.append(("broll", i, s, e))
    t = e
if t < final_dur: segs.append(("main", t, final_dur))

inputs = ["-i", str(OUT/"heygen.mp4")] + [x for p in brolls for x in ["-i", str(p)]] + ["-i", str(beat_wav)]
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
parts.append(f"[catv]ass={OUT}/captions.ass[outv]")
parts.append(f"[0:a]atempo={SPEED}[voice]")
parts.append(f"[{beat_idx}:a]volume=0.22,apad[music]")
parts.append(f"[voice][music]amix=inputs=2:duration=first:dropout_transition=0[outa]")

out_path = OUT / "final.mp4"
cmd = ["ffmpeg","-y", *inputs,
       "-filter_complex", ";".join(parts),
       "-map","[outv]","-map","[outa]",
       "-c:v","libx264","-preset","fast","-crf","18",
       "-pix_fmt","yuv420p","-movflags","+faststart",
       "-c:a","aac","-b:a","192k","-shortest",
       str(out_path)]
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print("STDERR:", r.stderr[-2000:]); sys.exit(1)
print(f"[done] {out_path} {out_path.stat().st_size//1024}KB")
