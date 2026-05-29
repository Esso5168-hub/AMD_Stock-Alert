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
