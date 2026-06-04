import requests
import os

BOT_TOKEN = "8277802627:AAEZs0Hc1rHR7RnU4O0NilZGmEc1X5X1aE4"
CHAT_ID = "-5229099102"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

posts = [
    {
        "image": "gbp_xxii_final/xxii_post1_pay.png",
        "caption": (
            "🌐 XXII Century — GBP Post 1\n\n"
            "*EARNING $2,100-$2,400 PER WEEK STARTS HERE*\n\n"
            "Tired of grinding miles for a paycheck that doesn't match the work? "
            "At 22 Century, company drivers earn 65 CPM — empty AND loaded — plus a 2 CPM fuel bonus from day one. "
            "That's $2,100 to $2,400 a week with raises every six months.\n\n"
            "👉 Press Call Now to start earning what you deserve. (773) 572-5012\n\n"
            "━━━━━━━━━━━━━━━\n"
            "📌 CTA: Press Call Now\n"
            "🏷 Brand: XXII Century"
        )
    },
    {
        "image": "gbp_xxii_final/xxii_post2_equipment.png",
        "caption": (
            "🌐 XXII Century — GBP Post 2\n\n"
            "*NEW VOLVOS & FREIGHTLINERS*\n\n"
            "Your truck is your home on the road. It should feel like one. "
            "22 Century puts you behind the wheel of new Volvos and Freightliners — "
            "equipped with a fridge, microwave, inverter, APU, and disc brakes. "
            "No more babysitting breakdowns.\n\n"
            "👉 Press Call Now to get behind the wheel. (773) 572-5012\n\n"
            "━━━━━━━━━━━━━━━\n"
            "📌 CTA: Press Call Now\n"
            "🏷 Brand: XXII Century"
        )
    },
    {
        "image": "gbp_xxii_final/xxii_post3_home_time.png",
        "caption": (
            "🌐 XXII Century — GBP Post 3\n\n"
            "*REAL HOME TIME. REAL SCHEDULE.*\n\n"
            "Home time shouldn't be a guessing game. At 22 Century, it's simple: "
            "2 weeks out = 2 days home. 3 weeks out = 3 days home. 4 weeks out = 4+ days home. "
            "Every extra week out earns you another day back. No begging. No surprises.\n\n"
            "👉 Press Call Now to get a schedule you can plan your life around. (773) 572-5012\n\n"
            "━━━━━━━━━━━━━━━\n"
            "📌 CTA: Press Call Now\n"
            "🏷 Brand: XXII Century"
        )
    },
    {
        "image": "gbp_xxii_final/xxii_post4_no_touch.png",
        "caption": (
            "🌐 XXII Century — GBP Post 4\n\n"
            "*DROP & HOOK. 100% NO-TOUCH*\n\n"
            "You're a CDL-A driver, not a warehouse worker. At 22 Century, it's 100% no-touch, "
            "dry van freight. 70-80% drop and hook. You drop the trailer, hook the next one, "
            "and keep rolling. Less waiting. More miles. More money.\n\n"
            "👉 Press Call Now and start driving — not loading. (773) 572-5012\n\n"
            "━━━━━━━━━━━━━━━\n"
            "📌 CTA: Press Call Now\n"
            "🏷 Brand: XXII Century"
        )
    },
    {
        "image": "gbp_xxii_final/xxii_post5_miles.png",
        "caption": (
            "🌐 XXII Century — GBP Post 5\n\n"
            "*3,000+ MILES EVERY WEEK*\n\n"
            "You can't build a life on inconsistent miles. 22 Century runs dedicated lanes "
            "across the Midwest, East, North, and South. 3,000+ miles a week. Steady freight. "
            "You know what you're making before the week even starts.\n\n"
            "👉 Press Call Now for miles you can count on. (773) 572-5012\n\n"
            "━━━━━━━━━━━━━━━\n"
            "📌 CTA: Press Call Now\n"
            "🏷 Brand: XXII Century"
        )
    },
    {
        "image": "gbp_xxii_final/xxii_post6_hiring.png",
        "caption": (
            "🌐 XXII Century — GBP Post 6\n\n"
            "*NOW HIRING CDL-A DRIVERS*\n\n"
            "22 Century is hiring CDL-A company drivers right now. 65 CPM empty and loaded. "
            "New trucks. Drop and hook. Real home time. Paid detentions, extra stops, and layovers. "
            "$1,500 referral bonus. 2 years experience, clean record required.\n\n"
            "👉 Press Call Now — your new truck is waiting. (773) 572-5012\n\n"
            "━━━━━━━━━━━━━━━\n"
            "📌 CTA: Press Call Now\n"
            "🏷 Brand: XXII Century"
        )
    },
]

for i, post in enumerate(posts):
    img_path = post["image"]
    if not os.path.exists(img_path):
        print(f"[{i+1}/6] Skipping — {img_path} not found")
        continue

    print(f"[{i+1}/6] Sending {img_path}...", end=" ", flush=True)
    with open(img_path, "rb") as f:
        r = requests.post(
            f"{BASE_URL}/sendPhoto",
            data={"chat_id": CHAT_ID, "caption": post["caption"], "parse_mode": "Markdown"},
            files={"photo": f}
        )
    if r.status_code == 200:
        print("Sent!")
    else:
        print(f"Error: {r.status_code} {r.text[:200]}")

print("\nDone!")
