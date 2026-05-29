"""
AMD Price Alert Bot — Alpha OS v2
- ส่งแจ้งเตือนผ่าน Telegram เมื่อ AMD แตะ alert levels
- Daily heartbeat ทุกเช้า 9:00 ไทย เพื่อยืนยันว่า bot ยังทำงาน
- ใช้ Finnhub API (เสถียรกว่า yfinance บน cloud)
"""

import requests
import json
import os
import time
from datetime import datetime
import pytz

# ============================================================
# ⚙️  CONFIG — อ่านจาก Railway Environment Variables
# ============================================================
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
FINNHUB_API_KEY    = os.environ["FINNHUB_API_KEY"]

# Alert Levels — อัพเดทตามราคาปัจจุบัน (AMD ~$518, ATH zone)
ALERT_LEVELS = {
    "🚀 ATH Breakout Confirm": {
        "price": 530,
        "direction": "above",
        "message": (
            "AMD แตะ <b>$530</b> — ATH Breakout Zone!\n"
            "⚠️ รอ <b>ปิดเหนือ $530</b> + volume ก่อนเข้า\n"
            "❌ แตะแล้วลง = fake breakout อย่าเข้า\n"
            "🛑 Stop: $510  |  🎯 Target: $560–580"
        ),
    },
    "📈 Take Profit 1": {
        "price": 550,
        "direction": "above",
        "message": (
            "🎉 AMD แตะ <b>$550</b> — TP1!\n"
            "→ ขาย 1/3 ของ position\n"
            "→ Trail stop ขยับขึ้นมา $525"
        ),
    },
    "🚀 Take Profit 2": {
        "price": 580,
        "direction": "above",
        "message": (
            "🚀 AMD แตะ <b>$580</b> — TP2!\n"
            "→ ขายอีก 1/3\n"
            "→ Runner ที่เหลือ trail $560"
        ),
    },
    "🎯 Pullback Entry": {
        "price": 510,
        "direction": "below",
        "message": (
            "AMD ย่อลง <b>$510</b> — Pullback Entry Zone\n"
            "✅ Former resistance flip support\n"
            "🛑 Stop: $493  |  🎯 Target: $530–550"
        ),
    },
    "💎 Best Entry": {
        "price": 505,
        "direction": "below",
        "message": (
            "AMD แตะ <b>$505</b> — Strong Support / Best Entry\n"
            "R:R กว้างที่สุด\n"
            "🛑 Stop: $493  |  🎯 T1: $530  |  🚀 T2: $550"
        ),
    },
    "⚠️ Trail Stop Warning": {
        "price": 500,
        "direction": "below",
        "message": (
            "AMD ใกล้ Trail Stop — ราคา <b>$500</b>\n"
            "→ ถ้ามี position ตั้งแต่ $510+ → เตรียมพร้อม\n"
            "→ Hard stop อยู่ที่ $493"
        ),
    },
    "🚨 Stop Loss": {
        "price": 493,
        "direction": "below",
        "message": (
            "🚨 AMD หลุด <b>$493</b>!\n"
            "<b>STOP — ออก position ทันที</b>\n"
            "❌ Trend อาจกำลัง break\n"
            "รอ structure ใหม่ก่อนกลับเข้า"
        ),
    },
}

CHECK_INTERVAL_SECONDS = 900   # เช็คทุก 15 นาที
ALERT_COOLDOWN_SECONDS = 3600  # ไม่ส่ง alert ซ้ำภายใน 1 ชั่วโมง
HEARTBEAT_HOUR_THAI    = 9     # ส่ง daily heartbeat ทุกเช้า 9:00 ไทย
STATE_FILE             = "alert_state.json"

THAI_TZ = pytz.timezone("Asia/Bangkok")
ET_TZ   = pytz.timezone("America/New_York")
# ============================================================


def send_telegram(message: str) -> bool:
    """ส่งข้อความผ่าน Telegram Bot"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
        return r.status_code == 200
    except Exception as e:
        print(f"[Telegram Error] {e}")
        return False


def get_amd_price() -> float | None:
    """ดึงราคา AMD ปัจจุบันจาก Finnhub"""
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol=AMD&token={FINNHUB_API_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()
        price = data.get("c")  # c = current price
        if price and price > 0:
            return round(float(price), 2)
        return None
    except Exception as e:
        print(f"[Price Error] {e}")
        return None


def is_market_open() -> bool:
    """เช็คว่าตลาด US เปิดอยู่ไหม (Mon-Fri 9:30-16:00 ET)"""
    now = datetime.now(ET_TZ)
    if now.weekday() >= 5:  # Saturday, Sunday
        return False
    open_time  = now.replace(hour=9,  minute=30, second=0, microsecond=0)
    close_time = now.replace(hour=16, minute=0,  second=0, microsecond=0)
    return open_time <= now <= close_time


def load_state() -> dict:
    """โหลด state (alert cooldown, heartbeat tracking)"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    """บันทึก state ลงไฟล์"""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def check_and_fire_alerts(price: float, state: dict) -> dict:
    """เช็คทุก alert level และส่ง Telegram ถ้าถึงเงื่อนไข"""
    now = time.time()
    for name, cfg in ALERT_LEVELS.items():
        hit = (
            (cfg["direction"] == "below" and price <= cfg["price"]) or
            (cfg["direction"] == "above" and price >= cfg["price"])
        )
        if hit:
            last_sent = state.get(name, 0)
            if now - last_sent >= ALERT_COOLDOWN_SECONDS:
                thai_time = datetime.now(THAI_TZ).strftime("%H:%M")
                msg = (
                    f"⚡ <b>{name}</b>\n"
                    f"💰 AMD: <b>${price}</b>\n"
                    f"🕐 {thai_time} (เวลาไทย)\n\n"
                    f"{cfg['message']}"
                )
                if send_telegram(msg):
                    state[name] = now
                    print(f"  ✅ Alert sent: {name} @ ${price}")
    return state


def send_heartbeat(state: dict) -> dict:
    """ส่ง daily heartbeat ทุกเช้า 9:00 ไทย เพื่อยืนยันว่า bot ทำงาน"""
    now_thai = datetime.now(THAI_TZ)
    today_key = f"heartbeat_{now_thai.strftime('%Y-%m-%d')}"

    # ส่งแล้ววันนี้ → skip
    if state.get(today_key):
        return state

    # ยังไม่ถึงเวลา 9:00 → skip
    if now_thai.hour < HEARTBEAT_HOUR_THAI:
        return state

    # ดึงราคาล่าสุด (Finnhub ใช้ได้แม้ตลาดปิด - คืน last close)
    price = get_amd_price()
    price_str = f"${price}" if price else "N/A"
    market_status = "🟢 ตลาดเปิด" if is_market_open() else "🔴 ตลาดปิด"

    msg = (
        f"🤖 <b>AMD Monitor Daily Check</b>\n\n"
        f"💰 ราคาล่าสุด: <b>{price_str}</b>\n"
        f"📊 Bot: ทำงานปกติ ✅\n"
        f"{market_status}\n"
        f"🕐 {now_thai.strftime('%H:%M')} (Thai)\n"
        f"📅 {now_thai.strftime('%a, %d %b %Y')}"
    )

    if send_telegram(msg):
        state[today_key] = True
        print(f"  ✅ Heartbeat sent at {now_thai.strftime('%H:%M')}")

    return state


def main():
    print("=" * 50)
    print("  AMD Price Monitor — Alpha OS v2")
    print("=" * 50)

    # ส่งข้อความยืนยันการเริ่มต้น
    levels_text = "\n".join(
        f"  {'⬇' if c['direction']=='below' else '⬆'} ${c['price']} — {n}"
        for n, c in ALERT_LEVELS.items()
    )
    send_telegram(
        f"🤖 <b>AMD Monitor v2 เริ่มทำงาน</b>\n\n"
        f"<b>Alert Levels ใหม่:</b>\n{levels_text}\n\n"
        f"⏰ เช็คทุก 15 นาที ระหว่างตลาดเปิด\n"
        f"🌏 US Market = 21:30–04:00 เวลาไทย\n"
        f"💌 Daily Heartbeat: ทุกเช้า 09:00 (Thai)"
    )

    state = load_state()

    while True:
        thai_time = datetime.now(THAI_TZ).strftime("%H:%M")

        # ส่ง daily heartbeat (เช็คทุกรอบ แต่ส่งครั้งเดียวต่อวันที่ 9:00)
        state = send_heartbeat(state)
        save_state(state)

        # เช็คราคาเฉพาะตอนตลาดเปิด
        if is_market_open():
            price = get_amd_price()
            if price:
                print(f"[{thai_time}] AMD = ${price}")
                state = check_and_fire_alerts(price, state)
                save_state(state)
            else:
                print(f"[{thai_time}] ดึงราคาไม่ได้ — รอรอบถัดไป")
        else:
            print(f"[{thai_time}] ตลาดปิดอยู่ — sleeping...")

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
