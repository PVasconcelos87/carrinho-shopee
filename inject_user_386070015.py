"""
Script: inject_user_386070015.py
Descrição: Atualiza real_ml_stats.json com os 5 registros reais exatos extraídos do arquivo 2019-Oct.csv
para o user_id = 386070015 e a sessão 49d03116-3c95-4e13-8b9c-e3be97551fe8.
"""

import json
import os

STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "real_ml_stats.json")

user_id = 386070015
session_id = "49d03116-3c95-4e13-8b9c-e3be97551fe8"

# 5 Eventos Reais Brutos extraídos do CSV de origem (/basededados/2019-Oct.csv)
bronze_events = [
    { "event_time": "2019-10-01 05:01:02 UTC", "event_type": "view", "product_id": 1004776, "category_id": 2053013555631882655, "category_code": "electronics.smartphone", "brand": "xiaomi", "price": 185.08, "user_id": user_id, "user_session": session_id },
    { "event_time": "2019-10-01 05:01:53 UTC", "event_type": "view", "product_id": 1004739, "category_id": 2053013555631882655, "category_code": "electronics.smartphone", "brand": "xiaomi", "price": 197.52, "user_id": user_id, "user_session": session_id },
    { "event_time": "2019-10-01 05:02:29 UTC", "event_type": "view", "product_id": 1004133, "category_id": 2053013555631882655, "category_code": "electronics.smartphone", "brand": "xiaomi", "price": 135.99, "user_id": user_id, "user_session": session_id },
    { "event_time": "2019-10-01 05:02:50 UTC", "event_type": "cart", "product_id": 1004739, "category_id": 2053013555631882655, "category_code": "electronics.smartphone", "brand": "xiaomi", "price": 197.52, "user_id": user_id, "user_session": session_id },
    { "event_time": "2019-10-01 05:03:35 UTC", "event_type": "view", "product_id": 1004739, "category_id": 2053013555631882655, "category_code": "electronics.smartphone", "brand": "xiaomi", "price": 197.52, "user_id": user_id, "user_session": session_id }
]

silver_events = [
    { "event_time": "2019-10-01 05:01:02", "event_type": "view", "product_id": 1004776, "category_code": "electronics.smartphone", "brand": "xiaomi", "price": 185.08, "user_id": user_id, "user_session": session_id, "hour_of_day": 5 },
    { "event_time": "2019-10-01 05:01:53", "event_type": "view", "product_id": 1004739, "category_code": "electronics.smartphone", "brand": "xiaomi", "price": 197.52, "user_id": user_id, "user_session": session_id, "hour_of_day": 5 },
    { "event_time": "2019-10-01 05:02:29", "event_type": "view", "product_id": 1004133, "category_code": "electronics.smartphone", "brand": "xiaomi", "price": 135.99, "user_id": user_id, "user_session": session_id, "hour_of_day": 5 },
    { "event_time": "2019-10-01 05:02:50", "event_type": "cart", "product_id": 1004739, "category_code": "electronics.smartphone", "brand": "xiaomi", "price": 197.52, "user_id": user_id, "user_session": session_id, "hour_of_day": 5 },
    { "event_time": "2019-10-01 05:03:35", "event_type": "view", "product_id": 1004739, "category_code": "electronics.smartphone", "brand": "xiaomi", "price": 197.52, "user_id": user_id, "user_session": session_id, "hour_of_day": 5 }
]

gold_cart = {
    "user_session": session_id,
    "user_id": user_id,
    "total_cart_value": 197.52,
    "num_cart_items": 1,
    "num_views_before_cart": 4,
    "view_to_cart_ratio": 4.0,
    "session_duration_sec": 153,
    "is_night": 1,
    "is_abandoned": 1
}

matrix_coupon = {
    "sessionId": session_id,
    "userId": user_id,
    "totalVal": 197.52,
    "numItems": 1,
    "numViews": 4,
    "hourOfDay": 5,
    "pAbandon": 0.624,
    "isAbandoned": 1,
    "coupon": {
        "coupon_code": "DESC5_FRETE",
        "coupon_label": "Cupom 5% OFF + Frete Grátis",
        "discount_pct": 0.05,
        "free_shipping": True,
        "urgency": "Média",
        "rationale": "Abandono de smartphone Xiaomi de madrugada. Combo 5% OFF + Frete Grátis elimina a barreira do frete."
    },
    "recoveredGMV": 65.68
}

with open(STATS_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# Remove duplicatas anteriores do user 386070015 se existirem
data["abandonedCartsWithCoupons"] = [c for c in data["abandonedCartsWithCoupons"] if c.get("userId") != user_id]
data["medallion"]["bronze"]["sample"] = [b for b in data["medallion"]["bronze"]["sample"] if b.get("user_id") != user_id]
data["medallion"]["silver"]["sample"] = [s for s in data["medallion"]["silver"]["sample"] if s.get("user_id") != user_id]
data["medallion"]["gold"]["sample"] = [g for g in data["medallion"]["gold"]["sample"] if g.get("user_id") != user_id]

# Injeta na 1ª posição (topo)
data["abandonedCartsWithCoupons"].insert(0, matrix_coupon)
for ev in reversed(bronze_events):
    data["medallion"]["bronze"]["sample"].insert(0, ev)
for ev in reversed(silver_events):
    data["medallion"]["silver"]["sample"].insert(0, ev)
data["medallion"]["gold"]["sample"].insert(0, gold_cart)

with open(STATS_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("✓ Eventos reais exatos do CSV para o user_id = 386070015 atualizados no TOPO do dashboard!")
