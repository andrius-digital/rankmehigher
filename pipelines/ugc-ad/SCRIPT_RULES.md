# UGC Script Writing Rules — Read Before Drafting Any Trucking Reel

This file captures every TTS, pacing, and delivery lesson learned across V1-V16 of the CDL Agency UGC pipeline. Future scripts (for CDL Agency, future brands, or one-off reels) MUST follow these rules or they'll fail in ways that take 15+ re-renders to debug.

The voice we use (`ZthjuvLPty3kTMaNKVKb` = Peter, or `6OzrBCQf8cjERkYgzSg8` = Young Jamal) running in `eleven_multilingual_v2` is the reference. Other voices/models may behave differently.

---

## 1. Acronym pronunciation

| Acronym | Want pronounced as | In the script, write: | Why |
|---|---|---|---|
| CDL | `C-D-L` (spelled) | `CDL` (uppercase) | TTS spells uppercase acronyms correctly by default |
| CDL Class A | `C-D-L-A` (one connected block, NO gap) | `CDLA` (no space) | "CDL A" with space causes TTS to pause between CDL and A, which sounds wrong to truckers. Pipeline auto-converts `CDL A` → `CDLA` via `_normalize_trucking_acronyms`. |
| DUI | `D-U-I` (spelled) | `DUI` | Default spelling works |
| SAP | `"sap"` (word — Substance Abuse Program) | `SAP` in script; pipeline auto-maps to TTS spelling `Sapp` + caption override `SAP` | Voice aggressively acronymizes `SAP`. SSML `<sub>`, `<phoneme>`, `<say-as>`, and lowercase substitution ALL FAILED. `"Saap"` worked intermittently but regressed. `"Sapp"` (surname spelling) is the most stable phonetic form. |
| OTR | `O-T-R` (spelled) | `OTR` | Default works |
| DOT | `D-O-T` (spelled) | `DOT` | Default works |

**How the pipeline handles it:** `_normalize_trucking_acronyms()` in `ugc_pipeline.py` applies two automatic transforms:
- `CDL\s+([AB])` → `CDL\1` (joins CDL-A and CDL-B)
- Each entry in `ACRONYM_TTS_SPELLING` dict (e.g. `SAP → Saap`) gets substituted for TTS
- Each entry in `CAPTION_DISPLAY_OVERRIDES` (e.g. `saap → SAP`) gets used by the caption generator

**If you add a new trucking acronym** and it reads wrong, add an entry to both dicts in `ugc_pipeline.py` — don't add per-script workarounds.

## 2. TTS request settings

```python
{
  "text": SCRIPT_SSML,
  "model_id": "eleven_multilingual_v2",      # supports <break>, limited other SSML
  "voice_settings": {
    "stability": 0.5,
    "similarity_boost": 0.8,
    "style": 0.4,
    "use_speaker_boost": True
  },
  "apply_text_normalization": "off"          # CRITICAL — "on" re-acronymizes input
}
```

**NEVER set `apply_text_normalization` to `"on"`.** It second-guesses the input and re-acronymizes words we've painstakingly phoneticized.

**SSML support in multilingual_v2:**
- ✅ `<break time="Xms"/>` — works reliably
- ❌ `<sub alias="...">X</sub>` — ignored for acronym re-pronunciation
- ❌ `<phoneme alphabet="ipa" ph="...">X</phoneme>` — also ignored for this voice
- ❌ `<say-as interpret-as="word">X</say-as>` — unreliable

**Workaround for the ignored tags:** decouple TTS pronunciation from display. Write phonetic spelling for TTS ("Saap"), map back to canonical uppercase for captions ("SAP") via `CAPTION_DISPLAY_OVERRIDES`.

## 3. Sentence structure — one clause per sentence

**DON'T** chain multiple short clauses with commas:
```
Paid weekly, real home time, good benefits.  ❌  mumbles across the phrase
```

**DO** split into separate sentences with short breaks:
```
Paid weekly. <break time="180ms"/>Real home time. <break time="180ms"/>Good benefits.  ✅
```

TTS gives each full sentence a cleaner delivery than comma-joined clauses. Comma-joined phrases often slur/mumble — especially 2-3 word phrases like "real home time" at the tail of a breath.

## 4. Break timings — the reference tempo

**These are the pacing defaults that landed after V1→V16 iteration.** Don't invent new ones without reason.

| Position | Break (ms) | Why |
|---|---|---|
| After hook (opening question/statement) | 350-450 | Let the hook land |
| After rhetorical question | 450 | Gives the "huh?" moment |
| Pivot into offer/body | 250-300 | Quick engagement |
| Between items in a list | 80-100 | Micro-pause, reads as checklist, not rushed |
| After list conclusion | 400 | Transition |
| Pre-CTA hold | 500 | Build anticipation |
| Between CTA parts | 0 or 180 | Usually flow through |

**Playback speed:** `1.10` (the compose step). Faster than 1.15 sounds rushed; slower than 1.05 sounds monotonous.

## 5. Script structure — HOOK / BODY / CTA only

Every script MUST have three clearly delineated sections:

```
HOOK (1-2 lines)       — what grabs in the first 2 seconds
BODY (3-6 lines)       — the offer, credentials, value, or tips
CTA (1-2 lines)        — the ask
```

**One complete thought per line.** Don't write paragraphs — write beats.

**Bad** (monolithic):
```
We're hiring CDLA drivers with 2 years experience, clean record, no DUI, no SAP, paid weekly with real home time, click the link below to get hired fast.
```

**Good** (beats):
```
We're hiring CDLA drivers right now.
2 years experience, clean record, no DUI, no SAP.
Paid weekly. Real home time.
Click the link below to get hired fast.
```

## 6. NEVER fabricate numbers

Any rate, ratio, or market stat in a script MUST come from a trusted source. Rule of thumb:

- **Flatbed rate:** ~$3.45/mile (current as of 2026-04-23 — user-confirmed). Update in `MARKET_DATA` constants when it shifts.
- **Reefer load-to-truck ratio:** ~26:1 (from `knowledge/scripts/viral_scripts.md`).
- **Any other stat:** cite a source the user has confirmed, or ask before using.

Truckers and owner-operators will spot fake numbers instantly and it kills credibility. Do not round up for drama.

## 7. Length target

**15-25 seconds** spoken, `~1.10x` playback → final video **13-22 seconds**.

Count syllables/words during drafting. 45-60 words spoken = ~15s at a natural trucker-friendly pace. If a script is running >30s, cut a body line.

## 8. Tone — Bobby Loads / Alex Hormozi

- Short punchy sentences.
- Confident, direct, value-first.
- No corporate fluff ("Our team is committed to providing...").
- No AI-isms ("In the realm of modern trucking...").
- Specificity over generalization ("$3.45/mile" beats "great rates").

## 9. Writer → pipeline handoff

When handing a finalized script to the pipeline:
1. Write the script as a single string in `SCRIPT_RAW` inside `ugc_pipeline.py` OR as a variant in `brands/cdl-agency.json` `scripts.<key>`.
2. Include SSML `<break time="...">` tags inline for pacing.
3. Keep trucking acronyms UPPERCASE — pipeline normalizer handles them.
4. Do NOT include `<sub>`, `<phoneme>`, `<say-as>` — they're ignored and waste tokens.

If you follow all of the above, a new script should nail it on V1, not V16.
