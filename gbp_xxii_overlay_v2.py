from PIL import Image, ImageDraw, ImageFont
import os, sys, requests

PHONE = "630-948-0501"
EMAIL = "hr@goxxii.com"
ADDRESS_L1 = "7501 Lemont Rd Ste 200,"
ADDRESS_L2 = "Woodridge, IL 60517"
NAVY = (30, 40, 62)
ICON_COLOR = (70, 190, 170)
LOGO_PATH = "/Users/markaslevinas/Downloads/XXII Final Logo v2.png"

BOT_TOKEN = "8277802627:AAEZs0Hc1rHR7RnU4O0NilZGmEc1X5X1aE4"
CHAT_ID = "-5229099102"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def find_font(bold=False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def draw_circle(draw, cx, cy, r, color):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)

def draw_phone_icon(draw, cx, cy, r):
    draw_circle(draw, cx, cy, r, ICON_COLOR)
    s = int(r * 0.5)
    draw.rounded_rectangle([cx - s + 2, cy - s, cx + s - 2, cy + s], radius=3, fill="white")

def draw_email_icon(draw, cx, cy, r):
    draw_circle(draw, cx, cy, r, ICON_COLOR)
    ew, eh = int(r * 0.55), int(r * 0.38)
    draw.rectangle([cx - ew, cy - eh, cx + ew, cy + eh], outline="white", width=2)
    draw.line([(cx - ew, cy - eh), (cx, cy + 2), (cx + ew, cy - eh)], fill="white", width=2)

def draw_pin_icon(draw, cx, cy, r):
    draw_circle(draw, cx, cy, r, ICON_COLOR)
    pr = int(r * 0.28)
    draw.ellipse([cx - pr, cy - pr - 3, cx + pr, cy + pr - 3], outline="white", width=2)
    draw.polygon([(cx - pr, cy + 2), (cx, cy + int(r * 0.6)), (cx + pr, cy + 2)], fill="white")

def overlay_and_send(image_path, headline, caption):
    if not os.path.exists(image_path):
        print(f"Image not found: {image_path}")
        return False

    img = Image.open(image_path).convert("RGB")
    target_w = 1300
    img_h = int(target_w * img.size[1] / img.size[0])
    img = img.resize((target_w, img_h), Image.LANCZOS)

    bar_height = int(target_w * 0.18)
    canvas = Image.new("RGB", (target_w, img_h + bar_height), NAVY)
    canvas.paste(img, (0, 0))

    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo_h = int(img_h * 0.12)
    logo_w = int(logo.size[0] * logo_h / logo.size[1])
    logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
    logo_x = target_w - logo_w - int(target_w * 0.03)
    logo_y = int(img_h * 0.03)
    canvas.paste(logo, (logo_x, logo_y), logo)

    draw = ImageDraw.Draw(canvas)
    bold_path = find_font(bold=True)
    reg_path = find_font(bold=False)

    headline_size = int(bar_height * 0.34)
    contact_size = int(bar_height * 0.15)
    small_size = int(bar_height * 0.13)

    headline_font = ImageFont.truetype(bold_path, headline_size) if bold_path else ImageFont.load_default()
    contact_font = ImageFont.truetype(reg_path, contact_size) if reg_path else ImageFont.load_default()
    small_font = ImageFont.truetype(reg_path, small_size) if reg_path else ImageFont.load_default()

    bar_top = img_h
    pad_left = int(target_w * 0.035)
    hl_y = bar_top + int(bar_height * 0.12)
    draw.multiline_text((pad_left, hl_y), headline, fill="white", font=headline_font, spacing=int(headline_size * 0.1))

    icon_r = int(bar_height * 0.09)
    right_start = int(target_w * 0.62)
    icon_x = right_start
    text_x = icon_x + icon_r * 2 + 12
    row_h = int(bar_height * 0.30)

    ry1 = bar_top + int(bar_height * 0.10)
    draw_phone_icon(draw, icon_x + icon_r, ry1 + icon_r, icon_r)
    draw.text((text_x, ry1 + 2), PHONE, fill="white", font=contact_font)

    ry2 = ry1 + row_h
    draw_email_icon(draw, icon_x + icon_r, ry2 + icon_r, icon_r)
    draw.text((text_x, ry2 + 2), EMAIL, fill="white", font=contact_font)

    ry3 = ry2 + row_h
    draw_pin_icon(draw, icon_x + icon_r, ry3 + icon_r, icon_r)
    draw.text((text_x, ry3), ADDRESS_L1, fill="white", font=small_font)
    draw.text((text_x, ry3 + small_size + 2), ADDRESS_L2, fill="white", font=small_font)

    os.makedirs("gbp_xxii_final_v2", exist_ok=True)
    out_path = f"gbp_xxii_final_v2/{os.path.basename(image_path)}"
    canvas.save(out_path, quality=95)
    print(f"Overlay saved: {out_path}")

    with open(out_path, "rb") as f:
        r = requests.post(
            f"{BASE_URL}/sendPhoto",
            data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "Markdown"},
            files={"photo": f}
        )
    if r.status_code == 200:
        print(f"Sent to Telegram!")
        return True
    else:
        print(f"Telegram error: {r.status_code} {r.text[:300]}")
        return False

if __name__ == "__main__":
    idx = int(sys.argv[1])
    posts = [
        {
            "image": "gbp_xxii_images_v2/xxii_v2_post1_pay.png",
            "headline": "EARNING $2,100-$2,400\nPER WEEK STARTS HERE",
            "caption": "🌐 XXII Century — GBP Post 1\n\n*EARNING $2,100-$2,400 PER WEEK STARTS HERE*\n\nTired of grinding miles for a paycheck that doesn't match the work? At 22 Century, company drivers earn 65 CPM — empty AND loaded — plus a 2 CPM fuel bonus from day one. That's $2,100 to $2,400 a week with raises every six months.\n\n👉 Press Call Now to start earning what you deserve. (773) 572-5012\n\n━━━━━━━━━━━━━━━\n📌 CTA: Press Call Now\n🏷 Brand: XXII Century"
        },
        {
            "image": "gbp_xxii_images_v2/xxii_v2_post2_equipment.png",
            "headline": "NEW VOLVOS &\nFREIGHTLINERS",
            "caption": "🌐 XXII Century — GBP Post 2\n\n*NEW VOLVOS & FREIGHTLINERS*\n\nYour truck is your home on the road. It should feel like one. 22 Century puts you behind the wheel of new Volvos and Freightliners — equipped with a fridge, microwave, inverter, APU, and disc brakes. No more babysitting breakdowns.\n\n👉 Press Call Now to get behind the wheel. (773) 572-5012\n\n━━━━━━━━━━━━━━━\n📌 CTA: Press Call Now\n🏷 Brand: XXII Century"
        },
        {
            "image": "gbp_xxii_images_v2/xxii_v2_post3_home_time.png",
            "headline": "REAL HOME TIME.\nREAL SCHEDULE.",
            "caption": "🌐 XXII Century — GBP Post 3\n\n*REAL HOME TIME. REAL SCHEDULE.*\n\nHome time shouldn't be a guessing game. At 22 Century, it's simple: 2 weeks out = 2 days home. 3 weeks out = 3 days home. 4 weeks out = 4+ days home. Every extra week out earns you another day back. No begging. No surprises.\n\n👉 Press Call Now to get a schedule you can plan your life around. (773) 572-5012\n\n━━━━━━━━━━━━━━━\n📌 CTA: Press Call Now\n🏷 Brand: XXII Century"
        },
        {
            "image": "gbp_xxii_images_v2/xxii_v2_post4_no_touch.png",
            "headline": "DROP & HOOK.\n100% NO-TOUCH",
            "caption": "🌐 XXII Century — GBP Post 4\n\n*DROP & HOOK. 100% NO-TOUCH*\n\nYou're a CDL-A driver, not a warehouse worker. At 22 Century, it's 100% no-touch, dry van freight. 70-80% drop and hook. You drop the trailer, hook the next one, and keep rolling. Less waiting. More miles. More money.\n\n👉 Press Call Now and start driving — not loading. (773) 572-5012\n\n━━━━━━━━━━━━━━━\n📌 CTA: Press Call Now\n🏷 Brand: XXII Century"
        },
        {
            "image": "gbp_xxii_images_v2/xxii_v2_post5_miles.png",
            "headline": "3,000+ MILES\nEVERY WEEK",
            "caption": "🌐 XXII Century — GBP Post 5\n\n*3,000+ MILES EVERY WEEK*\n\nYou can't build a life on inconsistent miles. 22 Century runs dedicated lanes across the Midwest, East, North, and South. 3,000+ miles a week. Steady freight. You know what you're making before the week even starts.\n\n👉 Press Call Now for miles you can count on. (773) 572-5012\n\n━━━━━━━━━━━━━━━\n📌 CTA: Press Call Now\n🏷 Brand: XXII Century"
        },
        {
            "image": "gbp_xxii_images_v2/xxii_v2_post6_hiring.png",
            "headline": "NOW HIRING\nCDL-A DRIVERS",
            "caption": "🌐 XXII Century — GBP Post 6\n\n*NOW HIRING CDL-A DRIVERS*\n\n22 Century is hiring CDL-A company drivers right now. 65 CPM empty and loaded. New trucks. Drop and hook. Real home time. Paid detentions, extra stops, and layovers. $1,500 referral bonus. 2 years experience, clean record required.\n\n👉 Press Call Now — your new truck is waiting. (773) 572-5012\n\n━━━━━━━━━━━━━━━\n📌 CTA: Press Call Now\n🏷 Brand: XXII Century"
        },
    ]
    p = posts[idx]
    overlay_and_send(p["image"], p["headline"], p["caption"])
