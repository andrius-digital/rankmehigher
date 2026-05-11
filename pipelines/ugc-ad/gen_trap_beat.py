#!/usr/bin/env python3
"""Generate instrumental trap beat via Fal.ai stable-audio."""
import os, time, urllib.request
from pathlib import Path
import fal_client

OUT = Path("/opt/data/artifacts/music"); OUT.mkdir(parents=True, exist_ok=True)

# Try a few model endpoints in priority order
models_to_try = [
    ("fal-ai/stable-audio-25/text-to-audio", {
        "prompt": "hard-hitting trap beat, booming 808 sub bass, punchy kick drum, crisp snares, rolling hi-hats, high energy aggressive cinematic trucking ad, instrumental, no vocals, powerful confident",
        "seconds_total": 20,
    }),
    ("fal-ai/stable-audio", {
        "prompt": "dark trap beat, hard 808 bass, tight hi-hats, cinematic instrumental, no vocals, moody confident",
        "seconds_total": 20,
    }),
    ("fal-ai/minimax-music", {
        "prompt": "dark trap beat, hard 808 bass, tight hi-hats, instrumental, moody",
    }),
]

for model, args in models_to_try:
    print(f"\n[fal] trying {model}")
    t0 = time.time()
    try:
        result = fal_client.run(model, arguments=args)
        print(f"[fal] ✓ {model} in {time.time()-t0:.1f}s")
        print(f"[fal] keys: {list(result.keys())}")
        # find audio url
        audio_url = None
        for k in ("audio_file", "audio", "url"):
            v = result.get(k)
            if isinstance(v, dict) and v.get("url"):
                audio_url = v["url"]; break
            elif isinstance(v, str) and v.startswith("http"):
                audio_url = v; break
        if not audio_url:
            print(f"[fal] no audio url in result: {result}")
            continue
        print(f"[fal] audio_url: {audio_url[:100]}")
        ext = "wav" if audio_url.endswith(".wav") else "mp3"
        out = OUT / f"trap_fal.{ext}"
        urllib.request.urlretrieve(audio_url, out)
        print(f"[fal] downloaded {out.stat().st_size//1024}KB → {out}")
        (OUT / "latest.txt").write_text(str(out))
        break
    except Exception as e:
        print(f"[fal] ✗ {model}: {e}")
        continue
