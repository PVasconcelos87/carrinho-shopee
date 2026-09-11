"""
Script: populate_postgres.py
Descrição: Carrega os dados processados da Camada Gold (session_features) e prescreve cupons
para o banco relacional PostgreSQL (Serving Layer) rodando no Docker.
"""

import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text

DB_URL = os.getenv("DATABASE_URL", "postgresql://mack_user:mack_password@localhost:5432/ecommerce_db")
BASE_DIR = os.path.expanduser("~/data_lake_cache/gold/session_features")


def populate_serving_layer():
    print("==========================================================================")
    print("  CARREGANDO DADOS DA CAMADA GOLD PARA O POSTGRESQL (SERVING LAYER)")
    print("==========================================================================")
    
    # 1. Conecta ao PostgreSQL
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Conexão com PostgreSQL estabelecida com sucesso!")
    except Exception as e:
        print(f"Erro ao conectar ao PostgreSQL: {e}")
        print("Certifique-se de que os containers Docker estão rodando (docker compose up -d).")
        return

    # 2. Localiza arquivos Parquet da Camada Gold
    df_gold = None
    if os.path.exists(BASE_DIR):
        print(f"Lendo Parquet da Camada Gold a partir de: {BASE_DIR}...")
        df_gold = pd.read_parquet(BASE_DIR)
    elif os.path.exists("/tmp/gold_parquet"):
        df_gold = pd.read_parquet("/tmp/gold_parquet")
    else:
        print("Buscando dados da Gold via gerador de features...")
        from src.feature_engineering import build_cart_features
        from src.evaluate_buyer_journey import generate_multi_session_ecommerce_events
        df_events = generate_multi_session_ecommerce_events(num_users=800)
        df_gold = build_cart_features(df_events)

    print(f"✓ Total de registros na Gold prontos para carga: {len(df_gold):,}")

    # 3. Formata para a tabela session_features
    df_gold_pg = df_gold.rename(columns={"user_session": "session_id"})
    cols_expected = [
        "session_id", "user_id", "total_cart_value", "num_cart_items",
        "num_views_before_cart", "view_to_cart_ratio", "session_duration_sec",
        "hour_of_day", "day_of_week", "is_weekend", "is_night", "main_category",
        "user_prior_views", "user_prior_carts", "user_prior_abandoned_carts",
        "user_total_cumulative_views", "user_lifetime_hours", "user_prior_abandon_rate",
        "is_abandoned"
    ]
    for c in cols_expected:
        if c not in df_gold_pg.columns:
            df_gold_pg[c] = 0

    df_gold_pg = df_gold_pg[cols_expected].drop_duplicates(subset=["session_id"])
    
    print(f"Inserindo {len(df_gold_pg):,} registros na tabela 'session_features'...")
    df_gold_pg.to_sql("session_features", engine, if_exists="append", index=False)
    print("✓ Tabela 'session_features' populada com sucesso!")

    # 4. Popula tabela de cupons prescritos (cart_coupons_prescribed)
    from src.coupon_recommender import CouponRecommender
    import joblib
    model_path = "models/cart_coupon_model.joblib"
    if os.path.exists(model_path):
        pipe = joblib.load(model_path)
        recommender = CouponRecommender(pipe)
        df_rec = recommender.process_cart_batch(df_gold.head(500).copy())
        
        df_rec_pg = df_rec.rename(columns={"user_session": "session_id"})[[
            "session_id", "user_id", "total_cart_value", "p_abandonment",
            "urgency_level", "coupon_code", "coupon_label", "discount_pct",
            "estimated_recovered_gmv"
        ]].drop_duplicates(subset=["session_id"])
        
        print(f"Inserindo {len(df_rec_pg):,} prescrições de cupons na tabela 'cart_coupons_prescribed'...")
        df_rec_pg.to_sql("cart_coupons_prescribed", engine, if_exists="append", index=False)
        print("✓ Tabela 'cart_coupons_prescribed' populada com sucesso!")

    print("\n==========================================================================")
    print("  🐘 SERVING LAYER 100% OPERACIONAL NO POSTGRESQL!")
    print("  • Host: localhost:5432 (externo via EC2)")
    print("  • Database: ecommerce_db | User: mack_user")
    print("  • pgAdmin Web: Porta 5050 (http://SEU_IP:5050)")
    print("==========================================================================")


if __name__ == "__main__":
    populate_serving_layer()
