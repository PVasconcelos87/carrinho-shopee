"""
Script: test_simulator.py
Descrição: Validação técnica automatizada da lógica do simulador de carrinho e recomendador de cupons de ML.
Simula 1.000 combinações randômicas de parâmetros de carrinho e valida o comportamento preditivo.
"""

import random
import pandas as pd
import numpy as np

from src.coupon_recommender import CouponRecommender
from src.model_pipeline import train_and_evaluate_models
from src.feature_engineering import build_cart_features
from src.data_generator import generate_ecommerce_events


def validate_simulator_logic():
    print("==========================================================================")
    print("  VALIDAÇÃO TÉCNICA AUTOMATIZADA DO SIMULADOR DE CARRINHO DE ML")
    print("==========================================================================")
    
    # 1. Carrega dados sintéticos/reais para treinar modelo de validação
    df_raw = generate_ecommerce_events(num_sessions=1000, random_seed=42)
    df_gold = build_cart_features(df_raw)
    ml_out = train_and_evaluate_models(df_gold, test_size=0.20, random_state=42)
    
    recommender = CouponRecommender(ml_out["best_pipeline"])
    
    # 2. Executa 1.000 simulações randômicas passando múltiplos parâmetros
    sim_results = []
    
    categories = ["electronics", "computers", "apparel", "appliances", "beauty"]
    intents = ["high_intent", "bargain_hunter", "browser"]
    
    for sim_id in range(1, 1001):
        num_items = random.randint(1, 8)
        avg_price = round(random.uniform(20.0, 1500.0), 2)
        total_val = round(num_items * avg_price, 2)
        max_price = round(avg_price * random.uniform(1.0, 1.4), 2)
        min_price = round(avg_price * random.uniform(0.6, 1.0), 2)
        
        num_views = random.randint(1, 15)
        duration_sec = float(random.randint(15, 600))
        hour_of_day = random.randint(0, 23)
        day_of_week = random.randint(0, 6)
        
        cart_row = {
            "num_cart_items": num_items,
            "total_cart_value": total_val,
            "max_item_price": max_price,
            "min_item_price": min_price,
            "avg_item_price": avg_price,
            "num_distinct_brands": random.randint(1, min(3, num_items)),
            "num_distinct_categories": random.randint(1, min(2, num_items)),
            "main_category": random.choice(categories),
            "num_views_before_cart": num_views,
            "view_to_cart_ratio": num_views / max(1, num_items),
            "session_duration_sec": duration_sec,
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week,
            "is_weekend": 1 if day_of_week in [5, 6] else 0,
            "is_night": 1 if hour_of_day in [0, 1, 2, 3, 4, 5, 22, 23] else 0
        }
        
        df_single = pd.DataFrame([cart_row])
        p_abandon = float(recommender.predict_abandonment_risk(df_single)[0])
        rec = recommender.recommend_coupon(cart_row, p_abandon)
        
        sim_results.append({
            "sim_id": sim_id,
            "total_val": total_val,
            "num_items": num_items,
            "p_abandon": p_abandon,
            "coupon_code": rec["coupon_code"],
            "coupon_label": rec["coupon_label"],
            "urgency": rec["urgency_level"]
        })
        
    df_sim = pd.DataFrame(sim_results)
    
    print(f"\n✓ 1.000 Simulações Randômicas Concluídas com Sucesso!")
    print(f" -> Probabilidade Média de Abandono: {df_sim['p_abandon'].mean():.2%}")
    print(f" -> Faixa de Probabilidades: Min = {df_sim['p_abandon'].min():.2%}, Max = {df_sim['p_abandon'].max():.2%}")
    print("\nDistribuição de Cupons em 1.000 Simulações Randômicas:")
    print(df_sim["coupon_label"].value_counts().to_string())
    
    print("\nAmostra de 5 Simulações Randômicas:")
    print(df_sim[["sim_id", "total_val", "p_abandon", "urgency", "coupon_label"]].head(5).to_string(index=False))


if __name__ == "__main__":
    validate_simulator_logic()
