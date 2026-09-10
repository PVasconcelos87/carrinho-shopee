"""
Script: export_medallion_samples.py
Descrição: Processa o dataset de /basededados e extrai 100 registros de cada camada da Arquitetura Medallion (permitindo exatamente 10 páginas de 10 registros cada):
1. Bronze (Raw Events)
2. Silver (Trusted Events)
3. Gold (Curated Cart Dataset & ML)
Salva o resultado em real_ml_stats.json.
"""

import os
import json
import pandas as pd
import numpy as np

from src.data_loader import load_basededados_dataset
from src.feature_engineering import build_cart_features


def export_medallion_data():
    print("Processando 100 registros das Camadas Medallion (10 páginas de 10 registros por camada)...")
    
    # 1. BRONZE (Raw Events) - 100 registros
    df_bronze = load_basededados_dataset(sample_n=5000)
    bronze_samples = df_bronze.head(100).fillna("").to_dict(orient="records")
    
    # 2. SILVER (Trusted Events - Higienizados) - 100 registros
    df_silver = df_bronze.copy()
    df_silver["event_time_dt"] = pd.to_datetime(df_silver["event_time"])
    df_silver["hour_of_day"] = df_silver["event_time_dt"].dt.hour
    df_silver["day_of_week"] = df_silver["event_time_dt"].dt.dayofweek
    df_silver["category_code"] = df_silver["category_code"].fillna("outros.desconhecido")
    df_silver["brand"] = df_silver["brand"].fillna("generico")
    
    silver_samples = df_silver[[
        "event_time", "event_type", "product_id", "category_code", 
        "brand", "price", "user_id", "user_session", "hour_of_day"
    ]].head(100).to_dict(orient="records")
    
    # 3. GOLD (Curated Cart Dataset) - 100 registros
    df_gold = build_cart_features(df_bronze)
    gold_samples = df_gold.head(100).to_dict(orient="records")
    
    stats_file = "real_ml_stats.json"
    if os.path.exists(stats_file):
        with open(stats_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
        
    data["medallion"] = {
        "bronze": {
            "name": "Bronze (Raw Events)",
            "description": "Dados brutos originais do Kaggle sem aplicação de regras de negócio.",
            "total_records": len(bronze_samples),
            "sample": bronze_samples
        },
        "silver": {
            "name": "Silver (Trusted Events)",
            "description": "Dados higienizados, tipados e enriquecidos temporalmente.",
            "total_records": len(silver_samples),
            "sample": silver_samples
        },
        "gold": {
            "name": "Gold (Curated Cart Dataset & ML)",
            "description": "Agregação ao nível de carrinho (user_session), rótulo is_abandoned e cupons preditivos.",
            "total_records": len(gold_samples),
            "sample": gold_samples
        }
    }
    
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print(f"✓ 100 registros por camada exportados com sucesso para: {stats_file}")


if __name__ == "__main__":
    export_medallion_data()
