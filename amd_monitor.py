"""
╔══════════════════════════════════════════════════════════════╗
║         ALPHA OS — Multi-Stock Price Alert Monitor           ║
║         AMD + NVDA | Telegram | Railway.app                  ║
╚══════════════════════════════════════════════════════════════╝

ALERT LEVELS:
  AMD  — Entry Zone B ($505), Stop ($491), TP1 ($527), TP2 ($550)
  NVDA — Zone C Entry ($207–209), GEX Put Wall ($207.50),
          Stop ($202.50), TP1 ($219), TP2 ($228)
"""

import os
import json
import time
from datetime import datetime

import pytz
import yfinance as yf
import requests

# ──────────────────────────────────────────────
# CONFIG — ใส่ค่าตรงนี้ หรือตั้งเป็น ENV variable บน Railway
# ──────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_TOKEN_HERE")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID",   "YOUR_CHAT_ID_HERE")

CHECK_INTERVAL_SECONDS = 300   # เช็คทุก 5 นาที
STATE_FILE             = "alert_state.json"
THAI_TZ                = pytz.timezone("Asia/Bangkok")
ET_TZ                  = pytz.timezone("America/New_York")

# ──────────────────────────────────────────────
# ALERT LEVELS — AMD
# ──────────────────────────────────────────────
AMD_ALERT_LEVELS = {
    "👀 AMD ใกล้ Entry Zone":      {"price": 510.00, "direction": "below", "fired": False},
    "🎯 AMD Entry Zone B":         {"price": 505.00, "direction": "below", "fired": False},
    "⚠️ AMD ใกล้ Stop Loss":       {"price": 494.00, "direction": "below", "fired": False},
    "🚨 AMD Stop Loss":            {"price": 491.00, "direction": "below", "fired": False},
    "📈 AMD TP1":                  {"price": 527.00, "direction": "above", "fired": False},
    "🚀 AMD TP2":                  {"price": 550.00, "direction": "above", "fired": False},
}

# ──────────────────────────────────────────────
# ALERT LEVELS — NVDA Zone C
# ──────────────────────────────────────────────
NVDA_ALERT_LEVELS = {
    "👀 NVDA Pullback มา Zone":    {"price": 212.00, "direction": "below", "fired": False},
    "📍 NVDA Zone C เริ่ม":        {"price": 209.00, "direction": "below", "fired": False},
    "🎯 NVDA Best Entry (GEX Wall)":{"price": 207.50, "direction": "below", "fired": False},
    "⚠️ NVDA ใกล้ Stop Loss":      {"price": 204.00, "direction": "below", "fired": False},
    "🚨 NVDA Stop Loss":           {"price": 202.50, "direction": "below", "fired": False},
    "📈 NVDA TP1":                 {"price": 219.00, "direction": "above", "fired": False},
    "🚀 NVDA TP2":                 {"price": 228.00, "direction": "above", "fired": False},
    "💥 NVDA ATH Zone":            {"price": 232.00, "direction": "above", "fired": False},
}

# ──────────────────────────────────────────────
# ALERT CONTEXT MESSAGES
# ──────────────────────────────────────────────
AMD_CONTEXT = {
    "👀 AMD ใกล้ Entry Zone": (
        "📍 <b>AMD กำลัง pullback มา Entry Zone</b>\n"
        "├ Target entry: $505 (Friday low support)\n"
        "└ เปิดจอ TradingView เช็ค CVD + VWAP"
    ),
    "🎯 AMD Entry Zone B": (
        "🎯 <b>AMD แตะ Entry Zone B $505</b>\n"
        "├ Friday low = key support thesis ✅\n"
        "├ Stop: $491 (ห่าง ~2.8%)\n"
        "├ TP1: $527 (+4.4%) | TP2: $550 (+8.9%)\n"
        "├ R:R = 2.4:1 ✅\n"
        "└ ⚡ รอ CVD บวก + hold VWAP ก่อน entry"
    ),
    "⚠️ AMD ใกล้ Stop Loss": (
        "⚠️ <b>AMD ใกล้ Stop $491</b>\n"
        "├ Monitor closely\n"
        "└ เตรียม exit ถ้าแตะ $491"
    ),
    "🚨 AMD Stop Loss": (
        "🚨 <b>AMD แตะ Hard Stop $491</b>\n"
        "├ ออกทันที — ไม่ negotiate\n"
        "└ Thesis invalidated | Preserve capital"
    ),
    "📈 AMD TP1": (
        "📈 <b>AMD แตะ TP1 $527</b>\n"
        "├ ขาย 1/3 ล็อคกำไร\n"
        "├ ย้าย stop → $510 (breakeven+)\n"
        "└ Runner ไป TP2 $550"
    ),
    "🚀 AMD TP2": (
        "🚀 <b>AMD แตะ TP2 $550!</b>\n"
        "├ ขายอีก 1/3 หรือทั้งหมด\n"
        "└ Trail stop runner ถ้าจะถือต่อ"
    ),
}

NVDA_CONTEXT = {
    "👀 NVDA Pullback มา Zone": (
        "👀 <b>NVDA กำลัง pullback มา Zone C</b>\n"
        "├ ยังไม่ถึง entry ($207–209)\n"
        "├ เริ่มเฝ้าดู price action\n"
        "└ เตรียม order ใกล้ $209"
    ),
    "📍 NVDA Zone C เริ่ม": (
        "📍 <b>NVDA เข้า Zone C Entry Range $207–209</b>\n"
        "├ ยังไม่ถึง best entry ($207.50)\n"
        "├ เปิดจอ TradingView เช็ค VWAP + CVD\n"
        "└ รอ confirmation — อย่ารีบ"
    ),
    "🎯 NVDA Best Entry (GEX Wall)": (
        "🎯 <b>NVDA แตะ GEX Put Wall $207.50 — BEST ENTRY</b>\n"
        "├ Stop: $202.50 (ห่าง ~2.5%)\n"
        "├ TP1: $219 (+5.3%) | TP2: $228 (+9.4%)\n"
        "├ R:R = 3.2:1 ✅✅\n"
        "└ ⚡ รอ reversal candle + CVD กลับบวก"
    ),
    "⚠️ NVDA ใกล้ Stop Loss": (
        "⚠️ <b>NVDA ใกล้ Stop $202.50</b>\n"
        "├ Monitor closely\n"
        "└ เตรียม exit ถ้าแตะ $202.50"
    ),
    "🚨 NVDA Stop Loss": (
        "🚨 <b>NVDA แตะ Hard Stop $202.50</b>\n"
        "├ ออกทันที — ไม่ negotiate\n"
        "└ Thesis invalidated | Preserve capital"
    ),
    "📈 NVDA TP1": (
        "📈 <b>NVDA แตะ TP1 $219</b>\n"
        "├ ขาย 1/3 ล็อคกำไร\n"
        "├ ย้าย stop → breakeven\n"
        "└ Runner ไป TP2 $228"
    ),
    "🚀 NVDA TP2": (
        "🚀 <b>NVDA แตะ TP2 $228!</b>\n"
        "├ ขายอีก 1/3 หรือทั้งหมด\n"
        "└ Trail stop runner ไป $232+"
    ),
    "💥 NVDA ATH Zone": (
        "💥 <b>NVDA $232 — ATH Zone Retest!</b>\n"
        "├ All-Time High = $235.74\n"
        "├ Momentum สูงมาก\n"
        "└ Hold runner หรือขายหมดตามแผน"
    ),
}

# ──────────────────────────────────────────────
# TELEGRAM
# ──────────────────────────────────────────────
def send_telegram(message: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       message,
        "parse_mode": "HTML",
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"[Telegram] Error: {e}")
        return False

# ──────────────────────────────────────────────
# PRICE FETCH
# ──────────────────────────────────────────────
def get_price(ticker: str) -> float | None:
    try:
        data = yf.Ticker(ticker).history(period="1d", interval="1m")
        if not data.empty:
            return round(float(data["Close"].iloc[-1]), 2)
    except Exception as e:
        print(f"[{ticker}] Error ดึงราคา: {e}")
    return None

# ──────────────────────────────────────────────
# MARKET HOURS CHECK
# ──────────────────────────────────────────────
def is_market_open() -> bool:
    now_et = datetime.now(ET_TZ)
    if now_et.weekday() >= 5:           # เสาร์-อาทิตย์
        return False
    market_open  = now_et.replace(hour=9,  minute=30, second=0, microsecond=0)
    market_close = now_et.replace(hour=16, minute=0,  second=0, microsecond=0)
    return market_open <= now_et <= market_close

# ──────────────────────────────────────────────
# STATE (persist fired alerts ข้ามรอบ)
# ──────────────────────────────────────────────
def load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# ──────────────────────────────────────────────
# ALERT ENGINE (generic — ใช้ได้ทั้ง AMD และ NVDA)
# ──────────────────────────────────────────────
def check_alerts(ticker: str, price: float, levels: dict, context_map: dict, state: dict) -> dict:
    key = f"{ticker}_alerts"
    alerts = state.get(key, {name: {"fired": False} for name in levels})

    for name, cfg in levels.items():
        if alerts.get(name, {}).get("fired", False):
            continue

        triggered = (
            (cfg["direction"] == "below" and price <= cfg["price"]) or
            (cfg["direction"] == "above" and price >= cfg["price"])
        )
        if not triggered:
            continue

        direction_text = (
            f"⬇ ลงถึง ${cfg['price']}" if cfg["direction"] == "below"
            else f"⬆ ขึ้นถึง ${cfg['price']}"
        )
        context = context_map.get(name, "")
        thai_time = datetime.now(THAI_TZ).strftime("%H:%M")

        message = (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{name}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>{ticker}</b> ราคา <b>${price}</b>\n"
            f"{direction_text}\n\n"
            f"{context}\n\n"
            f"🕐 {thai_time} เวลาไทย"
        )
        send_telegram(message)
        alerts[name] = {"fired": True}
        print(f"[{ticker} ALERT] {name} fired at ${price}")

    state[key] = alerts
    return state

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  ALPHA OS — Multi-Stock Monitor")
    print("  AMD + NVDA | Telegram Alerts")
    print("=" * 55)

    # Startup message
    amd_lines  = "\n".join(
        f"  {'⬇' if c['direction']=='below' else '⬆'} ${c['price']} — {n}"
        for n, c in AMD_ALERT_LEVELS.items()
    )
    nvda_lines = "\n".join(
        f"  {'⬇' if c['direction']=='below' else '⬆'} ${c['price']} — {n}"
        for n, c in NVDA_ALERT_LEVELS.items()
    )
    send_telegram(
        f"🤖 <b>Alpha Monitor เริ่มทำงานแล้ว</b>\n\n"
        f"<b>📈 AMD Levels:</b>\n{amd_lines}\n\n"
        f"<b>📊 NVDA Levels (Zone C):</b>\n{nvda_lines}\n\n"
        f"⏰ เช็คทุก 5 นาที ระหว่างตลาดเปิด\n"
        f"🌏 US Market = 21:30–04:00 เวลาไทย"
    )

    state = load_state()

    while True:
        thai_time = datetime.now(THAI_TZ).strftime("%H:%M")

        if is_market_open():
            # ── AMD ──
            amd_price = get_price("AMD")
            if amd_price:
                print(f"[{thai_time}] AMD  = ${amd_price}")
                state = check_alerts("AMD", amd_price, AMD_ALERT_LEVELS, AMD_CONTEXT, state)
            else:
                print(f"[{thai_time}] AMD  — ดึงราคาไม่ได้")

            # ── NVDA ──
            nvda_price = get_price("NVDA")
            if nvda_price:
                print(f"[{thai_time}] NVDA = ${nvda_price}")
                state = check_alerts("NVDA", nvda_price, NVDA_ALERT_LEVELS, NVDA_CONTEXT, state)
            else:
                print(f"[{thai_time}] NVDA — ดึงราคาไม่ได้")

            save_state(state)

        else:
            print(f"[{thai_time}] ตลาดปิดอยู่ — sleeping...")

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
