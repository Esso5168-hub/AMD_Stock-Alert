"""
AMD Price Alert Bot — Alpha OS
ส่งแจ้งเตือนผ่าน Telegram เมื่อ AMD แตะ alert levels
"""

import yfinance as yf
import requests
import json
import os
import time
from datetime import datetime
import pytz

# ============================================================
# ⚙️  CONFIG — แก้ไขตรงนี้ก่อนรัน
# ============================================================
import os
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]   # จาก @BotFather
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]   # จาก @userinfobot

# Alert Levels — ปรับได้ตามต้องการ
ALERT_LEVELS = {
    "🎯 Entry Zone เริ่มต้น": {
        "price": 424,
        "direction": "below",   # แจ้งเมื่อราคา <= price
        "message": (
            "AMD แตะ <b>$424</b> — Entry Zone เริ่มต้น\n"
            "✅ เช็ค CVD + Volume ก่อนเข้า\n"
            "🛑 Stop: $404  |  🎯 Target: $457"
        ),
    },
    "💎 Entry Zone ดีที่สุด": {
        "price": 410,
        "direction": "below",
        "message": (
            "AMD แตะ <b>$410</b> — Gap Fill Zone!\n"
            "นี่คือ entry ที่ดีที่สุด R:R กว้างที่สุด\n"
            "🛑 Stop: $390  |  🎯 T1: $457  |  🚀 T2: $480"
        ),
    },
    "⚠️ ใกล้ Stop Loss": {
        "price": 406,
        "direction": "below",
        "message": (
            "AMD ใกล้ Stop Loss — ราคา <b>$406</b>\n"
            "เตรียมพร้อมออก position\n"
            "🛑 Hard stop อยู่ที่ $404 (daily close)"
        ),
    },
    "🚨 Stop Loss Hit": {
        "price": 404,
        "direction": "below",
        "message": (
            "🚨 AMD แตก <b>$404</b>!\n"
            "<b>STOP LOSS — ออก position ทันที</b>\n"
            "❌ อย่า average down\n"
            "รอ structure ใหม่ก่อนกลับเข้า"
        ),
    },
    "📈 Target 1 Hit": {
        "price": 457,
        "direction": "above",  # แจ้งเมื่อราคา >= price
        "message": (
            "🎉 AMD แตะ <b>$457</b> — Target 1!\n"
            "→ ขายออก 50% ของ position\n"
            "→ ขยับ stop ขึ้นมาที่ $430\n"
            "→ ปล่อย 50% วิ่งไป Target 2: $480"
        ),
    },
    "🚀 Target 2 Hit": {
        "price": 480,
        "direction": "above",
        "message": (
            "🚀 AMD แตะ <b>$480</b> — Target 2!\n"
            "→ ขายที่เหลือทั้งหมด\n"
            "→ หรือ trail stop ที่ $460 ถ้าต้องการถือต่อ\n"
            "→ บันทึก trade ลง Excel Journal ทันที"
        ),
    },
}

CHECK_INTERVAL_SECONDS = 300   # เช็คทุก 5 นาที
ALERT_COOLDOWN_SECONDS = 3600  # ไม่ส่งซ้ำภายใน 1 ชั่วโมง
STATE_FILE = "alert_state.json"

THAI_TZ = pytz.timezone("Asia/Bangkok")
ET_TZ   = pytz.timezone("America/New_York")
# ============================================================


def send_telegram(message: str) -> bool:
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
    try:
        ticker = yf.Ticker("AMD")
        price = ticker.fast_info.last_price
        return round(float(price), 2)
    except Exception as e:
        print(f"[Price Error] {e}")
        return None


def is_market_open() -> bool:
    now = datetime.now(ET_TZ)
    if now.weekday() >= 5:
        return False
    open_time  = now.replace(hour=9,  minute=30, second=0, microsecond=0)
    close_time = now.replace(hour=16, minute=0,  second=0, microsecond=0)
    return open_time <= now <= close_time


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def check_and_fire_alerts(price: float, state: dict) -> dict:
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


def main():
    print("=" * 50)
    print("  AMD Price Monitor — Alpha OS")
    print("=" * 50)

    # ส่งข้อความยืนยันการเริ่มต้น
    levels_text = "\n".join(
        f"  {'⬇' if c['direction']=='below' else '⬆'} ${c['price']} — {n}"
        for n, c in ALERT_LEVELS.items()
    )
    send_telegram(
        f"🤖 <b>AMD Monitor เริ่มทำงานแล้ว</b>\n\n"
        f"<b>Alert Levels:</b>\n{levels_text}\n\n"
        f"⏰ เช็คทุก 5 นาที ระหว่างตลาดเปิด\n"
        f"🌏 US Market = 21:30–04:00 เวลาไทย"
    )

    state = load_state()

    while True:
        thai_time = datetime.now(THAI_TZ).strftime("%H:%M")

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
