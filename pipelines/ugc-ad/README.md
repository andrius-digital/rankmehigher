# UGC Ad Pipeline

AI-generated 9:16 UGC reels for short-form platforms (TikTok / Reels / YouTube Shorts). Built for the Hermes stack running on Hostinger VPS.

## Current best pipeline — `ugc_pipeline.py`

End-to-end flow that produces a finished reel:

```
ElevenLabs TTS (voice + SSML breaks + timestamps)
     │
     ├─► HeyGen HD render (1440×2560 talking-photo, happy + expressive)
     │         │
     │         └─► auto-crop to 9:16 content bounds
     │
     ├─► Fal.ai text-to-video × N  (Kling v2.5 → Hailuo → LTX fallback chain)
     │
     ├─► Fal.ai stable-audio  (generate trap beat once, reuse via BEAT_PATH env)
     │
     └─► ffmpeg composite
            ├─ speed up voice track (atempo, pitch preserved)
            ├─ concat main-video + b-roll inserts
            ├─ burn word-timed captions (ASS subtitles, plain white)
            ├─ mix beat at 15% volume under voice
            └─ output 1080×1920 H.264 + AAC
```

## Brand configs

Per-brand tuning lives in [`brands/`](brands/). Each JSON file specifies voice, avatar, script, b-roll prompts, caption style, music style. Adding a new brand = writing a new JSON.

- [`brands/cdl-agency.json`](brands/cdl-agency.json) — CDL Agency driver recruiting

## Running on the VPS

```bash
# SSH to VPS
ssh -i ~/.ssh/hostinger_vps root@srv1604937.hstgr.cloud

# Run the v10 pipeline (reads env for voice/avatar IDs, writes to /opt/data/artifacts/ugc/<timestamp>/)
docker exec hermes-agent-dhxt-hermes-gateway-1 /opt/hermes/.venv/bin/python \
  /opt/data/hermesagent/pipelines/ugc-ad/ugc_pipeline.py
```

Required env vars (already set in `/docker/hermes-agent-dhxt/data/.env`):
- `ELEVENLABS_API_KEY`
- `ELEVENLABS_CDL_VOICE_ID` (`6OzrBCQf8cjERkYgzSg8` = Young Jamal)
- `HEYGEN_API_KEY`
- `HEYGEN_CDL_AVATAR_ID` (`54b1e308527b4d56b2ef0824a12ce628`)
- `FAL_KEY`
- (optional) `BEAT_PATH` to reuse an existing beat

## Editing workflow (mobile-friendly)

1. Edit on Claude Code mobile (or any editor) — change prompts, tweaks, script text, SSML breaks, caption style, timings, etc.
2. Commit + push to `main`
3. VPS auto-pulls every 30s via cron, or you can trigger immediate pull via `/sync` Telegram command (planned)
4. Run the pipeline via SSH (or Telegram trigger when wired)

## Iteration history (what each version fixed)

| Version | Fix |
|---|---|
| v1 | First smoke test: still portrait + Ken Burns + captions + CTA |
| v2 | Added sync-lipsync via Fal.ai ffmpeg-loop-portrait trick |
| v3 | Swapped to HeyGen (broadcast quality) with wrong avatar |
| v4 | Fixed: content-bound crop (no white bars), used avatar #02 (CDL trucker) |
| v5 | HD 1440×2560 source + happy/expressive expression + 1.1x speed |
| v6 | Trap beat at 15% (Fal stable-audio; Suno was stuck) |
| v7 | Young Jamal voice |
| v8 | First b-roll composite (3 clips, white captions with shadow) |
| v9 | Kling v2.5 turbo pro b-rolls (2 clips × 3s), one-word white captions no shadow, higher position near chin |
| v10 | SSML `<break>` tags for natural sentence pauses (multilingual_v2 model) |

## Known gotchas

- `zoompan` filter is painfully slow on CPU — avoid in concat chains. Use `scale` + `crop` with expressions instead if you need zoom.
- HeyGen talking_photo renders source photo with white letterbox when source aspect ≠ output aspect. Auto-crop (via pixel-scan in `postprocess_ugc.py`) fixes this.
- Fal.ai `sync-lipsync` requires video input not image. Use ffmpeg to loop a still image into MP4 first.
- Suno via sunoapi.org was stuck in PENDING for 5+ minutes during testing — Fal Stable Audio is faster and more reliable for instrumentals.
- Don't stretch landscape avatars into 9:16 output — results in "horizontal in vertical frame" feel. Use `dimension: {width: 1920, height: 1080}` for 16:9 output or use native portrait avatars for 9:16.

## Costs per reel (at API rates)

- HeyGen: ~17 credits (~$2-3 at API rates, much less in bulk)
- ElevenLabs: ~100-200 char-credits (fractions of a cent)
- Fal.ai Kling × 2: ~$0.40 total
- Fal.ai Stable Audio (music): ~$0.05, often reusable
- VPS compute: $0 marginal

**Total: ~$2-3 per 15-sec reel at retail API pricing.**
