import os, requests, time

FAL_KEY = "1d465c82-337d-4c01-89eb-a100bb5659e4:943c2d1d4edea33c72e78fd57ac99c97"
HEADERS = {"Authorization": f"Key {FAL_KEY}", "Content-Type": "application/json"}
BASE = "https://queue.fal.run/fal-ai/nano-banana-pro"

prompts = [
    {
        "name": "xxii_v2_post1_pay",
        "prompt": "Close-up photograph of a truck driver's hands holding a thick stack of hundred dollar bills inside a modern semi truck cab. Dashboard with glowing screens visible in background. Warm interior lighting. American trucker lifestyle. Shallow depth of field. Professional commercial photography. Photorealistic. No text no watermarks."
    },
    {
        "name": "xxii_v2_post2_equipment",
        "prompt": "Interior photograph of a luxury semi truck sleeper cab. Brand new pristine condition. Mini fridge open showing drinks, microwave mounted on wall, flat screen TV, comfortable bed with clean sheets, LED ambient lighting. Modern Volvo truck dashboard visible. Cozy and high-end feel. Interior design photography style. Photorealistic. No text no watermarks."
    },
    {
        "name": "xxii_v2_post3_home_time",
        "prompt": "Photograph of a smiling truck driver in casual clothes hugging his young daughter on the front porch of a cozy American suburban home. Green lawn, white picket fence, warm porch light. His work boots by the door. Evening golden hour glow. Emotional heartwarming family moment. Lifestyle portrait photography. Shallow depth of field. Photorealistic. No text no watermarks."
    },
    {
        "name": "xxii_v2_post4_no_touch",
        "prompt": "Wide angle photograph looking down a long row of identical white dry van trailers perfectly lined up at an American logistics terminal. One semi truck cab backing into position to hook a trailer. Clean concrete yard with bright yellow painted lines. Symmetrical composition. Industrial minimalist photography. Bright overcast daylight. Photorealistic. No text no watermarks."
    },
    {
        "name": "xxii_v2_post5_miles",
        "prompt": "Dramatic photograph taken from inside a semi truck cab looking out through the windshield at a perfectly straight American highway stretching endlessly into the horizon. Sunset painting the sky orange and pink. Dashboard gauges and steering wheel framing the shot. Open plains on both sides. Driver POV perspective. Cinematic mood. Shot on wide angle lens. Photorealistic. No text no watermarks."
    },
    {
        "name": "xxii_v2_post6_hiring",
        "prompt": "Professional photograph of a confident male CDL truck driver in a clean uniform standing with arms crossed in front of a brand new dark blue Volvo VNL 860 semi truck. American truck yard setting. The driver looks proud and professional. Morning light with lens flare. Low angle hero shot making both driver and truck look powerful. Portrait photography. Photorealistic. No text no watermarks."
    }
]

os.makedirs("gbp_xxii_images_v2", exist_ok=True)

for i, p in enumerate(prompts):
    print(f"[{i+1}/6] Submitting: {p['name']}...", flush=True)

    r = requests.post(BASE, headers=HEADERS, json={
        "prompt": p["prompt"],
        "num_images": 1,
        "aspect_ratio": "4:3",
        "output_format": "png",
        "resolution": "1K",
        "safety_tolerance": "5"
    })

    if r.status_code not in (200, 201, 202):
        print(f"  ERROR submitting: {r.status_code} {r.text[:200]}", flush=True)
        continue

    data = r.json()
    request_id = data.get("request_id")
    status_url = data.get("status_url") or f"{BASE}/requests/{request_id}/status"
    result_url = data.get("response_url") or f"{BASE}/requests/{request_id}"

    print(f"  Queued: {request_id}", flush=True)

    for attempt in range(90):
        time.sleep(3)
        sr = requests.get(status_url, headers=HEADERS)
        if sr.status_code == 200:
            sdata = sr.json()
            status = sdata.get("status", "")
            if status == "COMPLETED":
                rr = requests.get(result_url, headers=HEADERS)
                result = rr.json()
                images = result.get("images", [])
                if images:
                    img_url = images[0].get("url", "")
                    img_data = requests.get(img_url).content
                    path = f"gbp_xxii_images_v2/{p['name']}.png"
                    with open(path, "wb") as f:
                        f.write(img_data)
                    print(f"  Saved: {path} ({len(img_data):,} bytes)", flush=True)
                break
            elif status in ("FAILED", "ERROR"):
                print(f"  FAILED: {sdata}", flush=True)
                break
    else:
        print(f"  Timed out waiting for {p['name']}", flush=True)

print("\nDone!", flush=True)
