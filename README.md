# rankmehigher

UGC video AI generation toolkit — the prompts, fonts, captioning rules, voice settings, and reel scripts we've iterated on. Shared so the team can run/extend the same pipeline.

## What's inside

```
.env                        # API keys (Fal, ElevenLabs, Suno, HeyGen, etc.) — gitignored
pipelines/ugc-ad/           # The full video generation pipeline
  ├── SCRIPT_RULES.md       # Hard-won lessons from V1–V20 (captions, pacing, voice)
  ├── README.md             # Pipeline overview
  ├── *_reel.py             # Per-brand reel scripts (cdl, azfs, mslines, roadking)
  ├── azfs_explainer.py     # Long-form explainer variant
  ├── audio_master.py       # Voice + beat mixing
  ├── gen_trap_beat.py      # Suno beat generation
  ├── compose_broll.py      # B-roll assembly
  ├── postprocess_ugc.py    # Final pass
  ├── ugc_pipeline.py       # Orchestrator
  ├── brands/               # Brand config JSON (palette, voice, persona)
  ├── remotion/             # Remotion captioning project
  └── scripts/              # Helper scripts (VPS autopull)
knowledge/scripts/          # Script library (UGC, viral, VSL) by vertical
AZFS_explainer.mp4          # Sample output
```

## Setup

1. Copy `.env` values into your shell or a fresh `.env` (the file is already here but gitignored).
2. Install Python deps for the reel scripts you want to run (each file declares what it needs at the top).
3. For Remotion captioning:
   ```bash
   cd pipelines/ugc-ad/remotion
   npm install
   ```

## API keys used

- **FAL_KEY** — image, video, lipsync (https://fal.ai/dashboard/keys)
- **ELEVENLABS_API_KEY** — voice TTS / cloning
- **SUNO_API_KEY** — beat generation (sunoapi.org)
- **HEYGEN_API_KEY** — avatar/lipsync backup

## Where to start

Read `pipelines/ugc-ad/SCRIPT_RULES.md` first — it captures every learning about captioning fonts, voice pacing, hook timing, and what looks good on bright shots.
