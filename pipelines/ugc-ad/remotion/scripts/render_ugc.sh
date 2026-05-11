#!/bin/bash
set -e
ART="$1"
if [ -z "$ART" ] || [ ! -d "$ART" ]; then
  echo "usage: $0 <artifacts-dir>"
  exit 1
fi
PROJ=/opt/data/remotion/ugc-videos
PUBLIC="$PROJ/public"
mkdir -p "$PUBLIC"

cp -f "$ART/portrait.jpg" "$PUBLIC/portrait.jpg"
cp -f "$ART/voiceover.mp3" "$PUBLIC/voiceover.mp3"
HAS_LIPSYNC=0
if [ -f "$ART/lipsync.mp4" ]; then
  cp -f "$ART/lipsync.mp4" "$PUBLIC/lipsync.mp4"
  HAS_LIPSYNC=1
fi

ALIGN="$ART/voiceover_timestamps.json"
AUDIO_DUR=$(python3 -c "import json; d=json.load(open('$ALIGN')); print(d['character_end_times_seconds'][-1])")
TOTAL_DUR=$(python3 -c "print(float('$AUDIO_DUR') + 3.0)")
FRAMES=$(python3 -c "print(int(float('$TOTAL_DUR') * 30))")
echo "audio=${AUDIO_DUR}s total=${TOTAL_DUR}s frames=$FRAMES lipsync=$HAS_LIPSYNC"

PROPS_FILE="$ART/remotion_props.json"
python3 -c "
import json, sys
alignment = json.load(open('$ALIGN'))
props = {
  'alignment': alignment,
  'script': 'CDL Agency recruiting',
  'brand': 'CDL AGENCY',
  'cta': 'cdlagency.com',
}
if $HAS_LIPSYNC == 1:
  props['lipsync'] = 'lipsync.mp4'  # relative to public/
open('$PROPS_FILE', 'w').write(json.dumps(props))
"

OUT="$ART/final.mp4"
cd "$PROJ"
echo "[render] → $OUT"
npx remotion render UgcAd "$OUT" \
  --codec=h264 --concurrency=1 \
  --frames="0-$((FRAMES-1))" \
  --props="$PROPS_FILE" 2>&1 | tail -15

ls -la "$OUT"
