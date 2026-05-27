# AI Avatar Video Creation Guide

## Quick Start — What Claude Code Needs From You

Before generating an AI video, provide:

1. **Company name** — e.g. "Rogue Carrier"
2. **Company logo** — attach the image file or save to Desktop
3. **What's the offer?** — e.g. "Hiring OTR company drivers, $1800-$2200/week, modern trucks"
4. **Script/talking points** — what should the avatar say? (or let AI write it)
5. **Avatar preference** — use existing avatar or create new one?

---

## Full Process

### Step 1: Create the Avatar (One-Time Setup)

**Option A — From a real person's video:**
1. Get a video of the person (2-3 min, looking straight at camera, good lighting, no cuts)
2. Upload to HeyGen API:
   - Digital twin (full motion, any angle): needs clean training video
   - Photo avatar (talking head from still): works from any video/photo
3. If digital twin fails (face tracking issues), HeyGen auto-generates photo avatar looks

**Option B — AI-generated person:**
1. Use HeyGen prompt-based avatar:
```
POST https://api.heygen.com/v3/avatars
{
  "type": "prompt",
  "name": "Avatar Name",
  "prompt": "Description of person, clothing, setting, camera angle"
}
```
2. Each prompt generates a NEW random face — to keep same face across angles, use Step 2

### Step 2: Lock the Face + Generate Multiple Angles

1. Pick the avatar look you like best
2. Download its preview image from HeyGen
3. Use Fal AI PuLID to generate the same face in different settings:
```
POST https://queue.fal.run/fal-ai/pulid
{
  "prompt": "Same person in different setting/angle",
  "reference_images": [{"image_url": "URL of the locked face"}],
  "image_size": {"width": 1024, "height": 1024}
}
```
4. Upload each generated image back to HeyGen as a photo avatar:
```
POST https://api.heygen.com/v3/assets   → upload image
POST https://api.heygen.com/v3/avatars  → create avatar from asset
{
  "type": "photo",
  "name": "Avatar - Setting Name",
  "file": {"type": "asset_id", "asset_id": "..."}
}
```

### Step 3: Pick a Voice

List available voices:
```
GET https://api.heygen.com/v2/voices
```

Tested masculine voices:
- **Tough Timothy** `8f8f8978a6454b03bebc6afa6b78c97b` — tough, no-nonsense
- **Gritty George** `b46d51ae7bbc4da68bb222b8a3452dad` — rough, rugged
- **Deepened Dave** `29874ab8894047e98b5bfb601c2605a0` — deep, smooth
- **Michael C. Vincent** `a52a040ef4424aa5af1dafac61512239` — confident, expressive

### Step 4: Generate the Video

```
POST https://api.heygen.com/v3/videos
{
  "type": "avatar",
  "avatar_id": "look_id",
  "voice_id": "voice_id",
  "script": "Your script text",
  "aspect_ratio": "9:16"
}
```
- Poll status: `GET https://api.heygen.com/v3/videos/{video_id}`
- When `status: "completed"`, download from `video_url`

### Step 5: Overlay Logo (via VPS ffmpeg)

```bash
scp video.mp4 logo.png root@2.24.92.100:/tmp/

ssh root@2.24.92.100 "ffmpeg -y -i /tmp/video.mp4 -i /tmp/logo.png \
  -filter_complex '[1:v]scale=200:-1[logo];[0:v][logo]overlay=20:20' \
  -c:a copy /tmp/video_logo.mp4"

scp root@2.24.92.100:/tmp/video_logo.mp4 ./
```

### Step 6: Send to Telegram

```bash
curl -X POST "https://api.telegram.org/bot{TOKEN}/sendVideo" \
  -F "chat_id={CHAT_ID}" \
  -F "video=@video_logo.mp4" \
  -F "caption=Caption text"
```

---

## API Keys Required
- **HeyGen** `HEYGEN_API_KEY` — avatar + video generation
- **Fal AI** `FAL_KEY` — face-consistent multi-angle generation (PuLID)
- **Telegram Bot** — for sending to groups
- **VPS SSH** `~/.ssh/rankmehigher_vps` → `root@2.24.92.100` — ffmpeg processing

## Existing Avatars

### Rogue Carrier — Guysas
- Config: `pipelines/ugc-ad/brands/rogue-carrier-avatars.json`
- Face reference asset: `50c4a241d7574069b7cf119bc00ba3fd`
- Voice: Tough Timothy `8f8f8978a6454b03bebc6afa6b78c97b`
- Logo asset: `1b8b568618f5440a9983b1f3442299b8`
- Looks: podcast studio, truck cab, truck yard, office, JRE style
