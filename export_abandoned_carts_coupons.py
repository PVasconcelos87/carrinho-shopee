"""
Script: export_abandoned_carts_coupons.py
Descrição: Processa o dataset real de /basededados, filtra EXCLUSIVAMENTE os carrinhos abandonados (is_abandoned == 1),
aplica a pipeline de ML e o motor de cupons, e exporta a lista completa de carrinhos elegíveis para oferta de desconto.
"""

import os
import json
import pandas as pd
import numpy as np

from src.data_loader import load_basededados_dataset
from src.feature_engineering import build_cart_features
from src.model_pipeline import train_and_evaluate_models
from src.coupon_recommender import CouponRecommender


def process_and_export_abandoned_coupons():
    print("==========================================================================")
    print("  APLICANDO ML: PROCESSAMENTO DE CARRINHOS ABANDONADOS E OFERTA DE CUPONS")
    print("==========================================================================")
    
    # 1. Carrega amostragem representativa do dataset real (300.000 eventos)
    df_events = load_basededados_dataset(sample_n=300000)
    
    # 2. Constrói a Camada Gold (Carrinhos)
    df_gold = build_cart_features(df_events)
    print(f" -> Total de carrinhos reconstruídos: {len(df_gold):,}")
    
    # 3. Treina a pipeline de Machine Learning no dataset completo
    ml_res = train_and_evaluate_models(df_gold, test_size=0.20, random_state=42)
    best_pipe = ml_res["best_pipeline"]
    best_name = ml_res["best_model_name"]
    res_best = ml_res["results"][best_name]
    
    recommender = CouponRecommender(best_pipe)
    
    # 4. FILTRA EXCLUSIVAMENTE OS CARRINHOS ABANDONADOS (is_abandoned == 1)
    df_abandoned = df_gold[df_gold["is_abandoned"] == 1].copy()
    print(f" -> Total de carrinhos verdadeiramente abandonados (target=1): {len(df_abandoned):,}")
    
    # Aplica o modelo de ML e o motor de cupons
    df_abandoned_rec = recommender.process_cart_batch(df_abandoned)
    
    # Filtra apenas os que recebem cupom (coupon_code != 'NENHUM')
    df_coupons_active = df_abandoned_rec[df_abandoned_rec["coupon_code"] != "NENHUM"].copy()
    print(f" -> Carrinhos abandonados elegíveis para Cupom de Desconto: {len(df_coupons_active):,}")
    
    # 5. Monta a lista completa para o index.html
    abandoned_carts_list = []
    for idx, row in df_coupons_active.iterrows():
        abandoned_carts_list.append({
            "sessionId": str(row["user_session"]),
            "userId": int(row["user_id"]),
            "totalVal": float(row["total_cart_value"]),
            "numItems": int(row["num_cart_items"]),
            "numViews": int(row["num_views_before_cart"]),
            "hourOfDay": int(row["hour_of_day"]),
            "pAbandon": float(row["p_abandonment"]),
            "isAbandoned": 1,
            "coupon": {
                "coupon_code": str(row["coupon_code"]),
                "coupon_label": str(row["coupon_label"]),
                "discount_pct": float(row["discount_pct"]),
                "free_shipping": bool(row["free_shipping"]),
                "urgency": str(row["urgency_level"]),
                "rationale": str(row["rationale"])
            },
            "recoveredGMV": float(row["estimated_recovered_gmv"])
        })
        
    # Ordena por prioridade: Urgência Crítica/Alta primeiro e depois maior valor de carrinho
    urgency_order = {"Crítica": 0, "Alta": 1, "Média": 2, "Baixa": 3}
    abandoned_carts_list.sort(key=lambda x: (urgency_order.get(x["coupon"]["urgency"], 4), -x["totalVal"]))
    
    # Resumo das Métricas
    total_abandoned_gmv = float(df_abandoned["total_cart_value"].sum())
    total_recovered_gmv = float(df_coupons_active["estimated_recovered_gmv"].sum())
    coupon_distribution = df_coupons_active["coupon_label"].value_counts().to_dict()
    
    payload = {
        "kpis": {
            "totalCarts": len(df_gold),
            "abandonedCarts": len(df_abandoned),
            "abandonmentRate": float(df_gold["is_abandoned"].mean()),
            "totalGMV": float(df_gold["total_cart_value"].sum()),
            "gmvLost": total_abandoned_gmv,
            "gmvRecovered": total_recovered_gmv,
            "couponEligibleCount": len(df_coupons_active)
        },
        "funnel": {
            "views": int(df_events[df_events["event_type"] == "view"].shape[0]),
            "carts": int(df_events[df_events["event_type"] == "cart"].shape[0]),
            "purchases": int(df_events[df_events["event_type"] == "purchase"].shape[0])
        },
        "modelMetrics": {
            "bestModelName": best_name,
            "accuracy": float(res_best["accuracy"]),
            "rocAuc": float(res_best["roc_auc"]),
            "precision": float(res_best["precision"]),
            "recall": float(res_best["recall"]),
            "f1": float(res_best["f1"])
        },
        "couponDistribution": coupon_distribution,
        "abandonedCartsWithCoupons": abandoned_carts_list
    }
    
    out_path = "real_ml_stats.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        
    print(f"\n✓ Sucesso! Exportados {len(abandoned_carts_list)} carrinhos abandonados com cupons para: {out_path}")


if __name__ == "__main__":
    process_and_export_abandoned_coupons()
