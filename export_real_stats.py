"""
Script: export_real_stats.py
Descrição: Processa dados reais da pasta /basededados e gera um arquivo JSON com as estatísticas 
e lote de previsões de ML para alimentar a interface do index.html (app.js).
"""

import os
import json
import pandas as pd
import numpy as np

from src.data_loader import load_basededados_dataset
from src.feature_engineering import build_cart_features
from src.model_pipeline import train_and_evaluate_models
from src.coupon_recommender import CouponRecommender


def export_stats_to_json():
    print("Processando dados reais de /basededados para exportação visual...")
    
    # 1. Carrega amostragem significativa dos eventos reais (150.000 linhas)
    df_events = load_basededados_dataset(sample_n=150000)
    
    # Contagens de eventos para o funil
    event_counts = df_events["event_type"].value_counts().to_dict()
    num_views = event_counts.get("view", 0)
    num_carts = event_counts.get("cart", 0)
    num_purchases = event_counts.get("purchase", 0)
    
    # 2. Feature Engineering (Gold Dataset)
    df_gold = build_cart_features(df_events)
    
    total_carts = len(df_gold)
    abandoned_carts = int(df_gold["is_abandoned"].sum())
    abandonment_rate = float(df_gold["is_abandoned"].mean())
    total_gmv = float(df_gold["total_cart_value"].sum())
    gmv_lost = float(df_gold[df_gold["is_abandoned"] == 1]["total_cart_value"].sum())
    
    # 3. Distribuição por Categoria
    df_gold_abandoned = df_gold[df_gold["is_abandoned"] == 1]
    cat_counts = df_gold_abandoned["main_category"].value_counts().head(5).to_dict()
    
    # 4. Distribuição por Horário
    hourly_abandon = df_gold.groupby("hour_of_day")["is_abandoned"].mean().round(3).to_dict()
    
    # 5. Treinamento de ML no dataset real
    ml_res = train_and_evaluate_models(df_gold, test_size=0.25, random_state=42)
    best_pipe = ml_res["best_pipeline"]
    best_name = ml_res["best_model_name"]
    
    res_best = ml_res["results"][best_name]
    
    # 6. Motor de Cupons nos carrinhos de teste
    recommender = CouponRecommender(best_pipe)
    df_test = df_gold.loc[ml_res["X_test"].index].copy()
    df_rec = recommender.process_cart_batch(df_test)
    
    gmv_recovered = float(df_rec["estimated_recovered_gmv"].sum())
    
    # Amostra de 50 carrinhos para a tabela do index.html
    sample_carts = []
    for idx, row in df_rec.head(50).iterrows():
        sample_carts.append({
            "sessionId": str(row["user_session"])[:12],
            "totalVal": float(row["total_cart_value"]),
            "numItems": int(row["num_cart_items"]),
            "numViews": int(row["num_views_before_cart"]),
            "hourOfDay": int(row["hour_of_day"]),
            "pAbandon": float(row["p_abandonment"]),
            "isAbandoned": int(row["is_abandoned"]),
            "coupon": {
                "coupon_code": str(row["coupon_code"]),
                "coupon_label": str(row["coupon_label"]),
                "discount_pct": float(row["discount_pct"]),
                "urgency": str(row["urgency_level"]),
                "rationale": str(row["rationale"])
            },
            "recoveredGMV": float(row["estimated_recovered_gmv"])
        })
        
    export_payload = {
        "kpis": {
            "totalCarts": total_carts,
            "abandonedCarts": abandoned_carts,
            "abandonmentRate": abandonment_rate,
            "totalGMV": total_gmv,
            "gmvLost": gmv_lost,
            "gmvRecovered": gmv_recovered
        },
        "funnel": {
            "views": num_views,
            "carts": num_carts,
            "purchases": num_purchases
        },
        "categories": cat_counts,
        "hourlyAbandonment": hourly_abandon,
        "modelMetrics": {
            "bestModelName": best_name,
            "accuracy": float(res_best["accuracy"]),
            "rocAuc": float(res_best["roc_auc"]),
            "precision": float(res_best["precision"]),
            "recall": float(res_best["recall"]),
            "f1": float(res_best["f1"])
        },
        "sampleCarts": sample_carts
    }
    
    out_path = "real_ml_stats.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(export_payload, f, ensure_ascii=False, indent=2)
        
    print(f"\nEstatísticas e previsões reais exportadas com sucesso para: {out_path}")


if __name__ == "__main__":
    export_stats_to_json()
