"""
Modulo: coupon_recommender.py
Descrição: Motor de Decisão e Recomendação Inteligente de Cupons de Desconto.
Combina o score preditivo de probabilidade de abandono (ML) com o valor financeiro 
do carrinho para recomendar a melhor estratégia de oferta de cupom de desconto.
"""

import pandas as pd
import numpy as np


class CouponRecommender:
    """
    Motor de Recomendação de Cupons para Carrinhos de E-commerce.
    """
    
    def __init__(self, model_pipeline):
        """
        Inicializa o recomendador com uma pipeline de ML treinada.
        
        Parâmetros:
            model_pipeline (Pipeline): Pipeline do Scikit-Learn (Preprocessor + Classifier).
        """
        self.pipeline = model_pipeline
        
    def predict_abandonment_risk(self, df_cart):
        """
        Calcula a probabilidade de abandono para um ou mais carrinhos.
        
        Parâmetros:
            df_cart (pd.DataFrame): DataFrame contendo as features do carrinho.
            
        Retorna:
            np.ndarray: Probabilidades de abandono (valores entre 0.0 e 1.0).
        """
        if self.pipeline is None:
            # Modo heurístico de fallback
            probs = []
            for _, r in df_cart.iterrows():
                val = r.get("total_cart_value", 100.0)
                v = r.get("num_views_before_cart", 1)
                night = r.get("is_night", 0)
                p = 0.45 + (0.20 if val > 400 else 0.0) + (0.10 if night else 0.0) - (0.15 if v > 4 else 0.0)
                probs.append(min(0.95, max(0.10, p)))
            return np.array(probs)

        df_cart = df_cart.copy()
        required_cols = [
            "num_cart_items", "total_cart_value", "max_item_price", "min_item_price", "avg_item_price",
            "num_distinct_brands", "num_distinct_categories", "num_views_before_cart",
            "view_to_cart_ratio", "session_duration_sec", "hour_of_day", "day_of_week",
            "is_weekend", "is_night", "user_prior_views", "user_prior_carts",
            "user_prior_abandoned_carts", "user_total_cumulative_views", "user_lifetime_hours",
            "user_prior_abandon_rate", "main_category"
        ]
        for col in required_cols:
            if col not in df_cart.columns:
                df_cart[col] = "other" if col == "main_category" else 0.0

        if hasattr(self.pipeline, "predict_proba"):
            probs = self.pipeline.predict_proba(df_cart)[:, 1]
        else:
            probs = self.pipeline.predict(df_cart).astype(float)
        return probs

    def recommend_coupon(self, cart_row, p_abandon):
        """
        Aplica as regras estratégicas de negócio para selecionar o cupom de desconto ideal.
        
        Parâmetros:
            cart_row (pd.Series ou dict): Dados da linha do carrinho (total_cart_value, num_cart_items, etc).
            p_abandon (float): Probabilidade de abandono estimada pelo modelo de ML (0.0 a 1.0).
            
        Retorna:
            dict: Decisão de cupom contendo [coupon_code, coupon_label, discount_pct, free_shipping, rationale]
        """
        total_val = cart_row["total_cart_value"]
        
        # Nível 1: Baixo Risco de Abandono (Comprador orgânico)
        if p_abandon < 0.40:
            return {
                "coupon_code": "NENHUM",
                "coupon_label": "Sem Cupom Necessário",
                "discount_pct": 0.0,
                "free_shipping": False,
                "urgency_level": "Baixa",
                "rationale": "Cliente apresenta alta intenção de compra orgânica. Oferta de cupom iria erodir margem desnecessariamente."
            }
            
        # Nível 2: Risco Moderado de Abandono (0.40 <= p < 0.65)
        elif 0.40 <= p_abandon < 0.65:
            if total_val >= 300.0:
                return {
                    "coupon_code": "FRETE_GRATIS",
                    "coupon_label": "Frete Grátis Shopee",
                    "discount_pct": 0.0,
                    "free_shipping": True,
                    "urgency_level": "Média",
                    "rationale": "Risco moderado em carrinho de médio/alto valor. O benefício do frete grátis elimina a principal barreira de checkout."
                }
            else:
                return {
                    "coupon_code": "DESC5",
                    "coupon_label": "Cupom 5% OFF",
                    "discount_pct": 0.05,
                    "free_shipping": False,
                    "urgency_level": "Média",
                    "rationale": "Risco moderado em carrinho de ticket menor. Desconto leve de 5% incentiva a finalização imediata."
                }
                
        # Nível 3: Alto Risco de Abandono (0.65 <= p < 0.85)
        elif 0.65 <= p_abandon < 0.85:
            if total_val >= 500.0:
                return {
                    "coupon_code": "DESC10",
                    "coupon_label": "Cupom 10% OFF Especial",
                    "discount_pct": 0.10,
                    "free_shipping": False,
                    "urgency_level": "Alta",
                    "rationale": "Alto risco de perda de carrinho de valor expressivo. Cupom de 10% OFF atua como forte gatilho de conversão."
                }
            else:
                return {
                    "coupon_code": "DESC5_FRETE",
                    "coupon_label": "Cupom 5% OFF + Frete Grátis",
                    "discount_pct": 0.05,
                    "free_shipping": True,
                    "urgency_level": "Alta",
                    "rationale": "Alto risco em ticket intermediário. Combo de 5% + Frete Grátis oferece percepção de alto valor para o cliente."
                }
                
        # Nível 4: Risco Crítico de Abandono (p >= 0.85)
        else:
            if total_val >= 800.0:
                return {
                    "coupon_code": "RECUPE15",
                    "coupon_label": "Cupom 15% VIP Recuperação",
                    "discount_pct": 0.15,
                    "free_shipping": True,
                    "urgency_level": "Crítica",
                    "rationale": "Abandono iminente em carrinho de altíssimo valor (GMV). Recuperação agressiva com 15% OFF + Frete Grátis preserva receita substancial."
                }
            else:
                return {
                    "coupon_code": "DESC10_FRETE",
                    "coupon_label": "Cupom 10% OFF + Frete Grátis",
                    "discount_pct": 0.10,
                    "free_shipping": True,
                    "urgency_level": "Crítica",
                    "rationale": "Carrinho prestes a ser abandonado. Incentivo máximo de 10% OFF + Frete Grátis para salvar a transação."
                }

    def process_cart_batch(self, df_carts):
        """
        Processa um lote de carrinhos e adiciona previsões de ML e recomendações de cupons.
        
        Parâmetros:
            df_carts (pd.DataFrame): DataFrame com as colunas de features do carrinho.
            
        Retorna:
            pd.DataFrame: DataFrame enriquecido com probabilidade de abandono e detalhes do cupom.
        """
        df_out = df_carts.copy()
        probs = self.predict_abandonment_risk(df_carts)
        df_out["p_abandonment"] = probs
        
        rec_list = []
        for idx, row in df_out.iterrows():
            p_ab = row["p_abandonment"]
            rec = self.recommend_coupon(row, p_ab)
            rec_list.append(rec)
            
        df_rec = pd.DataFrame(rec_list, index=df_out.index)
        for col in df_rec.columns:
            df_out[col] = df_rec[col]
            
        # Estimativa de ROI / GMV Recuperado
        # Supondo um lift de conversão médio de 35% com a oferta de cupom oportuna
        LIFT_CONVERSION = 0.35
        df_out["estimated_recovered_gmv"] = np.where(
            df_out["coupon_code"] != "NENHUM",
            df_out["total_cart_value"] * LIFT_CONVERSION * (1.0 - df_out["discount_pct"]),
            0.0
        )
        
        return df_out


if __name__ == "__main__":
    from data_generator import generate_ecommerce_events
    from feature_engineering import build_cart_features
    from model_pipeline import train_and_evaluate_models
    
    df_raw = generate_ecommerce_events(num_sessions=1000)
    df_gold = build_cart_features(df_raw)
    ml_res = train_and_evaluate_models(df_gold)
    
    recommender = CouponRecommender(ml_res["best_pipeline"])
    df_results = recommender.process_cart_batch(df_gold.head(20))
    print("\n--- Resultados do Lote de Teste (Motor de Cupons) ---")
    print(df_results[["user_session", "total_cart_value", "p_abandonment", "coupon_label", "urgency_level", "estimated_recovered_gmv"]].head(10))
