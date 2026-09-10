"""
Modulo: evaluate_buyer_journey.py
Descrição: 
1. Avalia a jornada completa do mesmo comprador (user_id):
   - Quantidade de visualizações (views) feitas antes do último carrinho que virou compra.
   - Quantidade de carrinhos (carts) montados antes do último carrinho que virou compra.
   - Distribuição estatística (média, mediana, percentis, desvio padrão).
2. Constrói as features temporais cumulativas do comprador no Feature Engineering.
3. Treina e compara os modelos de ML (Baseline sem histórico do comprador vs. Modelo Enriquecido com histórico).
4. Comprova a melhoria de acurácia e métricas (ROC-AUC, Precision, Recall, F1).
"""

import os
import sys
import random
import uuid

# Adiciona raiz do projeto ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

from src.data_generator import SAMPLE_PRODUCTS


def generate_multi_session_ecommerce_events(num_users=800, random_seed=42):
    """
    Gera logs de eventos de e-commerce onde o mesmo comprador (user_id)
    navega em múltiplas sessões sequenciais ao longo do tempo (jornada multi-touch).
    """
    random.seed(random_seed)
    np.random.seed(random_seed)
    
    events = []
    base_start = datetime(2026, 10, 1, 8, 0, 0)
    user_ids = [500000000 + i for i in range(num_users)]
    
    for user_id in user_ids:
        buyer_intent = random.choices(["high_intent", "bargain_hunter", "browser"], weights=[0.35, 0.40, 0.25])[0]
        
        if buyer_intent == "high_intent":
            num_sessions = random.choices([1, 2, 3], weights=[0.55, 0.30, 0.15])[0]
        elif buyer_intent == "bargain_hunter":
            num_sessions = random.choices([2, 3, 4, 5, 6], weights=[0.20, 0.35, 0.25, 0.15, 0.05])[0]
        else: # browser
            num_sessions = random.choices([1, 2, 3, 4], weights=[0.40, 0.30, 0.20, 0.10])[0]
            
        favorite_cat = random.choice(["electronics.smartphone", "appliances.kitchen.refrigerators", "apparel.shoes", "computers.notebook"])
        user_clock = base_start + timedelta(days=random.randint(0, 20), hours=random.randint(0, 14))
        
        will_purchase = random.random() < (0.65 if buyer_intent == "high_intent" else 0.45 if buyer_intent == "bargain_hunter" else 0.15)
        purchase_session_idx = num_sessions if will_purchase else -1
        
        for sess_num in range(1, num_sessions + 1):
            session_id = str(uuid.uuid4())
            curr_time = user_clock
            
            if buyer_intent == "browser":
                n_views = random.randint(3, 9)
            elif buyer_intent == "bargain_hunter":
                n_views = random.randint(3, 7)
            else:
                n_views = random.randint(1, 4)
                
            session_viewed = []
            for _ in range(n_views):
                prods_cat = [p for p in SAMPLE_PRODUCTS if p["cat_code"] == favorite_cat]
                prod = random.choice(prods_cat) if prods_cat and random.random() < 0.75 else random.choice(SAMPLE_PRODUCTS)
                price = round(random.uniform(prod["price_min"], prod["price_max"]), 2)
                session_viewed.append((prod, price))
                
                events.append({
                    "event_time": curr_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "event_type": "view",
                    "product_id": prod["id"],
                    "category_id": prod["cat_id"],
                    "category_code": prod["cat_code"],
                    "brand": prod["brand"],
                    "price": price,
                    "user_id": user_id,
                    "user_session": session_id
                })
                curr_time += timedelta(seconds=random.randint(15, 120))
                
            has_cart = (sess_num == purchase_session_idx) or (random.random() < 0.70)
            
            if has_cart:
                n_cart_items = random.randint(1, min(3, len(session_viewed)))
                cart_items = random.sample(session_viewed, n_cart_items)
                
                for prod, price in cart_items:
                    events.append({
                        "event_time": curr_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "event_type": "cart",
                        "product_id": prod["id"],
                        "category_id": prod["cat_id"],
                        "category_code": prod["cat_code"],
                        "brand": prod["brand"],
                        "price": price,
                        "user_id": user_id,
                        "user_session": session_id
                    })
                    curr_time += timedelta(seconds=random.randint(20, 180))
                    
                if sess_num == purchase_session_idx:
                    for prod, price in cart_items:
                        events.append({
                            "event_time": curr_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "event_type": "purchase",
                            "product_id": prod["id"],
                            "category_id": prod["cat_id"],
                            "category_code": prod["cat_code"],
                            "brand": prod["brand"],
                            "price": price,
                            "user_id": user_id,
                            "user_session": session_id
                        })
                        curr_time += timedelta(seconds=random.randint(5, 30))
                        
            user_clock = curr_time + timedelta(hours=random.randint(4, 72))
            
    df_all_events = pd.DataFrame(events)
    df_all_events["event_time_dt"] = pd.to_datetime(df_all_events["event_time"])
    df_all_events = df_all_events.sort_values("event_time_dt").reset_index(drop=True)
    return df_all_events


def evaluate_buyer_views_and_carts_before_purchase(df_events):
    """
    Avalia minuciosamente a quantidade de visualizações (views) e carrinhos (carts)
    que o mesmo comprador realizou ANTES do último carrinho que virou a compra.
    """
    df_events = df_events.sort_values("event_time_dt").reset_index(drop=True)
    purchase_events = df_events[df_events["event_type"] == "purchase"]
    purchasing_users = purchase_events["user_id"].unique()
    
    buyer_journey_stats = []
    
    for user_id in purchasing_users:
        user_events = df_events[df_events["user_id"] == user_id].copy()
        first_purchase_row = user_events[user_events["event_type"] == "purchase"].iloc[0]
        purchase_time = first_purchase_row["event_time_dt"]
        purchase_session = first_purchase_row["user_session"]
        
        events_before_purchase = user_events[user_events["event_time_dt"] < purchase_time]
        prior_sessions = events_before_purchase[events_before_purchase["user_session"] != purchase_session]
        
        views_in_prior_sessions = len(prior_sessions[prior_sessions["event_type"] == "view"])
        views_in_final_session = len(
            user_events[(user_events["user_session"] == purchase_session) & 
                        (user_events["event_type"] == "view") & 
                        (user_events["event_time_dt"] < purchase_time)]
        )
        total_views_before_purchase = views_in_prior_sessions + views_in_final_session
        
        # Carrinhos prévios antes do último
        prior_cart_sessions = prior_sessions[prior_sessions["event_type"] == "cart"]["user_session"].nunique()
        prior_cart_items = len(prior_sessions[prior_sessions["event_type"] == "cart"])
        
        first_interaction = user_events["event_time_dt"].min()
        journey_duration_hours = (purchase_time - first_interaction).total_seconds() / 3600.0
        
        buyer_journey_stats.append({
            "user_id": user_id,
            "purchase_session": purchase_session,
            "prior_cart_sessions": prior_cart_sessions,
            "prior_cart_items": prior_cart_items,
            "views_in_prior_sessions": views_in_prior_sessions,
            "views_in_final_session": views_in_final_session,
            "total_views_before_purchase": total_views_before_purchase,
            "journey_duration_hours": journey_duration_hours,
            "total_prior_sessions": prior_sessions["user_session"].nunique()
        })
        
    df_journey = pd.DataFrame(buyer_journey_stats)
    return df_journey


def compute_enriched_cart_features(df_events):
    """
    Constrói a camada Gold agregando por sessão com histórico temporal do comprador.
    """
    df_events["event_time_dt"] = pd.to_datetime(df_events["event_time"])
    df_events = df_events.sort_values("event_time_dt").reset_index(drop=True)
    
    sessions_with_cart = set(df_events[df_events["event_type"] == "cart"]["user_session"].unique())
    session_starts = df_events.groupby("user_session")["event_time_dt"].min().sort_values().index
    
    cart_records = []
    user_history = {}
    
    for session_id in session_starts:
        if session_id not in sessions_with_cart:
            continue
            
        group = df_events[df_events["user_session"] == session_id]
        user_id = group["user_id"].iloc[0]
        
        view_events = group[group["event_type"] == "view"]
        cart_events = group[group["event_type"] == "cart"]
        purchase_events = group[group["event_type"] == "purchase"]
        
        is_abandoned = 1 if purchase_events.empty else 0
        num_cart_items = len(cart_events)
        total_cart_value = cart_events["price"].sum()
        max_item_price = cart_events["price"].max()
        min_item_price = cart_events["price"].min()
        avg_item_price = cart_events["price"].mean()
        num_distinct_brands = cart_events["brand"].nunique()
        num_distinct_categories = cart_events["category_code"].nunique()
        
        cat_non_null = cart_events["category_code"].dropna()
        if not cat_non_null.empty:
            mode_series = cat_non_null.mode()
            main_category = mode_series.iloc[0] if not mode_series.empty else "other"
        else:
            main_category = "other"
        main_category_group = str(main_category).split(".")[0] if "." in str(main_category) else str(main_category)
        
        num_views_session = len(view_events)
        view_to_cart_ratio = num_views_session / max(1, num_cart_items)
        
        first_event_time = group["event_time_dt"].min()
        last_cart_time = cart_events["event_time_dt"].max()
        session_duration_sec = (last_cart_time - first_event_time).total_seconds()
        
        hour_of_day = last_cart_time.hour
        day_of_week = last_cart_time.dayofweek
        is_weekend = 1 if day_of_week in [5, 6] else 0
        is_night = 1 if hour_of_day in [0, 1, 2, 3, 4, 5, 22, 23] else 0
        
        u_hist = user_history.get(user_id, {
            "prior_views": 0,
            "prior_carts": 0,
            "prior_abandoned_carts": 0,
            "first_seen": first_event_time
        })
        
        prior_views = u_hist["prior_views"]
        prior_carts = u_hist["prior_carts"]
        prior_abandoned_carts = u_hist["prior_abandoned_carts"]
        total_cumulative_views = prior_views + num_views_session
        user_lifetime_hours = (first_event_time - u_hist["first_seen"]).total_seconds() / 3600.0
        prior_abandon_rate = (prior_abandoned_carts / prior_carts) if prior_carts > 0 else 0.5
        
        cart_records.append({
            "user_session": session_id,
            "user_id": user_id,
            "num_cart_items": num_cart_items,
            "total_cart_value": total_cart_value,
            "max_item_price": max_item_price,
            "min_item_price": min_item_price,
            "avg_item_price": avg_item_price,
            "num_distinct_brands": num_distinct_brands,
            "num_distinct_categories": num_distinct_categories,
            "main_category": main_category_group,
            "num_views_before_cart": num_views_session,
            "view_to_cart_ratio": view_to_cart_ratio,
            "session_duration_sec": max(0.0, session_duration_sec),
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week,
            "is_weekend": is_weekend,
            "is_night": is_night,
            # Novas Features Comportamentais do Comprador:
            "user_prior_views": prior_views,
            "user_prior_carts": prior_carts,
            "user_prior_abandoned_carts": prior_abandoned_carts,
            "user_total_cumulative_views": total_cumulative_views,
            "user_lifetime_hours": max(0.0, user_lifetime_hours),
            "user_prior_abandon_rate": prior_abandon_rate,
            "is_abandoned": is_abandoned
        })
        
        u_hist["prior_views"] += num_views_session
        u_hist["prior_carts"] += 1
        if is_abandoned == 1:
            u_hist["prior_abandoned_carts"] += 1
        user_history[user_id] = u_hist
        
    return pd.DataFrame(cart_records)


def run_evaluation_and_comparison():
    print("=" * 80)
    print("      ESTUDO DE JORNADA DO COMPRADOR & GANHO DE ACURÁCIA (SHOPEE ML)")
    print("=" * 80)
    
    print("\n1. Simulando base de eventos com jornadas multi-sessão de compradores...")
    df_events = generate_multi_session_ecommerce_events(num_users=1000, random_seed=42)
    print(f" -> Total de eventos: {len(df_events):,}")
    print(f" -> Compradores únicos: {df_events['user_id'].nunique():,}")
    print(f" -> Sessões únicas: {df_events['user_session'].nunique():,}")
    
    # 2. Avaliar quantidade de visualizações e carrinhos antes do último que virou compra
    print("\n2. AVALIAÇÃO DA JORNADA: Quantidade de Visualizações e Carrinhos antes da Compra:")
    df_journey = evaluate_buyer_views_and_carts_before_purchase(df_events)
    print(f" -> Total de compradores que converteram em compra: {len(df_journey):,}")
    
    stats_views = df_journey["total_views_before_purchase"].describe(percentiles=[0.25, 0.50, 0.75, 0.90])
    stats_carts = df_journey["prior_cart_sessions"].describe(percentiles=[0.25, 0.50, 0.75, 0.90])
    stats_dur = df_journey["journey_duration_hours"].describe(percentiles=[0.25, 0.50, 0.75, 0.90])
    
    print("\n--- [A] VISUALIZAÇÕES (VIEWS) FEITAS PELO COMPRADOR ANTES DA COMPRA ---")
    print(f"  • Média de visualizações totais:   {stats_views['mean']:.2f} views")
    print(f"  • Mediana (P50):                   {stats_views['50%']:.1f} views")
    print(f"  • Desvio Padrão:                   {stats_views['std']:.2f}")
    print(f"  • Intervalo Interquartil (P25-P75): {stats_views['25%']:.0f} a {stats_views['75%']:.0f} views")
    print(f"  • 90% dos compradores fizeram até: {stats_views['90%']:.0f} views")
    print(f"  • Mínimo / Máximo:                 {stats_views['min']:.0f} / {stats_views['max']:.0f} views")
    
    print("\n--- [B] CARRINHOS (CARTS) MONTADOS PELO COMPRADOR ANTES DO ÚLTIMO QUE VIROU COMPRA ---")
    print(f"  • Média de carrinhos prévios:      {stats_carts['mean']:.2f} carrinhos abandonados antes do final")
    print(f"  • Mediana (P50):                   {stats_carts['50%']:.1f} carrinhos prévios")
    print(f"  • Desvio Padrão:                   {stats_carts['std']:.2f}")
    print(f"  • Intervalo Interquartil (P25-P75): {stats_carts['25%']:.0f} a {stats_carts['75%']:.0f} carrinhos")
    print(f"  • 90% dos compradores montaram:    até {stats_carts['90%']:.0f} carrinhos prévios")
    print(f"  • Mínimo / Máximo:                 {stats_carts['min']:.0f} / {stats_carts['max']:.0f} carrinhos")
    
    print("\n--- [C] DISTRIBUIÇÃO DA FREQUÊNCIA DE CARRINHOS PRÉVIOS ---")
    cart_freq = df_journey["prior_cart_sessions"].value_counts(normalize=True).sort_index() * 100
    for n_carts, pct in cart_freq.items():
        desc = "Compra direta na 1ª sessão com carrinho" if n_carts == 0 else f"{n_carts} carrinho(s) abandonado(s) antes da conversão"
        print(f"  • {n_carts} carrinhos prévios: {pct:5.1f}% dos compradores ({desc})")
        
    print("\n--- [D] TEMPO MÉDIO DE MATURAÇÃO DA JORNADA ---")
    print(f"  • Tempo médio entre 1º contato e a compra: {stats_dur['mean']:.1f} horas ({stats_dur['mean']/24:.1f} dias)")
    print(f"  • Mediana: {stats_dur['50%']:.1f} horas ({stats_dur['50%']/24:.1f} dias)")
    
    # 3. Construir Dataset Gold com Features Enriquecidas
    print("\n3. Construindo Dataset Gold com Novas Features Históricas do Comprador...")
    df_gold = compute_enriched_cart_features(df_events)
    print(f" -> Total de carrinhos reconstruídos: {len(df_gold):,}")
    print(f" -> Taxa de abandono geral: {df_gold['is_abandoned'].mean():.2%}")
    
    # 4. Treinamento Comparativo
    print("\n4. TREINAMENTO COMPARATIVO: MODELO BASELINE vs. MODELO ENRIQUECIDO")
    
    baseline_numeric = [
        "num_cart_items", "total_cart_value", "max_item_price", "min_item_price", "avg_item_price",
        "num_distinct_brands", "num_distinct_categories", "num_views_before_cart",
        "view_to_cart_ratio", "session_duration_sec", "hour_of_day", "day_of_week",
        "is_weekend", "is_night"
    ]
    
    enriched_numeric = baseline_numeric + [
        "user_prior_views",
        "user_prior_carts",
        "user_prior_abandoned_carts",
        "user_total_cumulative_views",
        "user_lifetime_hours",
        "user_prior_abandon_rate"
    ]
    
    cat_cols = ["main_category"]
    target = "is_abandoned"
    y = df_gold[target]
    
    train_idx, test_idx = train_test_split(df_gold.index, test_size=0.20, random_state=42, stratify=y)
    
    # Baseline
    prep_b = ColumnTransformer([
        ("num", StandardScaler(), baseline_numeric),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols)
    ])
    pipe_base = Pipeline([("prep", prep_b), ("clf", RandomForestClassifier(n_estimators=120, max_depth=8, random_state=42))])
    pipe_base.fit(df_gold.loc[train_idx, baseline_numeric + cat_cols], y.loc[train_idx])
    y_pred_b = pipe_base.predict(df_gold.loc[test_idx, baseline_numeric + cat_cols])
    y_prob_b = pipe_base.predict_proba(df_gold.loc[test_idx, baseline_numeric + cat_cols])[:, 1]
    
    acc_b = accuracy_score(y.loc[test_idx], y_pred_b)
    auc_b = roc_auc_score(y.loc[test_idx], y_prob_b)
    prec_b = precision_score(y.loc[test_idx], y_pred_b, zero_division=0)
    rec_b = recall_score(y.loc[test_idx], y_pred_b, zero_division=0)
    f1_b = f1_score(y.loc[test_idx], y_pred_b, zero_division=0)
    
    # Enriquecido
    prep_e = ColumnTransformer([
        ("num", StandardScaler(), enriched_numeric),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols)
    ])
    pipe_enr = Pipeline([("prep", prep_e), ("clf", RandomForestClassifier(n_estimators=120, max_depth=8, random_state=42))])
    pipe_enr.fit(df_gold.loc[train_idx, enriched_numeric + cat_cols], y.loc[train_idx])
    y_pred_e = pipe_enr.predict(df_gold.loc[test_idx, enriched_numeric + cat_cols])
    y_prob_e = pipe_enr.predict_proba(df_gold.loc[test_idx, enriched_numeric + cat_cols])[:, 1]
    
    acc_e = accuracy_score(y.loc[test_idx], y_pred_e)
    auc_e = roc_auc_score(y.loc[test_idx], y_prob_e)
    prec_e = precision_score(y.loc[test_idx], y_pred_e, zero_division=0)
    rec_e = recall_score(y.loc[test_idx], y_pred_e, zero_division=0)
    f1_e = f1_score(y.loc[test_idx], y_pred_e, zero_division=0)
    
    print("\n==========================================================================")
    print("                    QUADRO COMPARATIVO DE PERFORMANCE DE ML")
    print("==========================================================================")
    print(f"{'Métrica':<20} | {'Baseline (Sessão)':<22} | {'Enriquecido (Jornada Comprador)':<30} | {'Ganho Absoluto'}")
    print("-" * 85)
    print(f"{'Acurácia (Accuracy)':<20} | {acc_b*100:6.2f}%                 | {acc_e*100:6.2f}%                        | +{(acc_e - acc_b)*100:5.2f}%")
    print(f"{'ROC-AUC Score':<20} | {auc_b:6.4f}                 | {auc_e:6.4f}                        | +{(auc_e - auc_b):6.4f}")
    print(f"{'Precisão (Precision)':<20} | {prec_b*100:6.2f}%                 | {prec_e*100:6.2f}%                        | +{(prec_e - prec_b)*100:5.2f}%")
    print(f"{'Revocação (Recall)':<20} | {rec_b*100:6.2f}%                 | {rec_e*100:6.2f}%                        | +{(rec_e - rec_b)*100:5.2f}%")
    print(f"{'F1-Score':<20} | {f1_b*100:6.2f}%                 | {f1_e*100:6.2f}%                        | +{(f1_e - f1_b)*100:5.2f}%")
    print("=" * 85)
    
    # Importância das Features
    feat_names = enriched_numeric + list(pipe_enr.named_steps["prep"].named_transformers_["cat"].get_feature_names_out(cat_cols))
    importances = pipe_enr.named_steps["clf"].feature_importances_
    feat_imp = sorted(zip(feat_names, importances), key=lambda x: x[1], reverse=True)
    
    print("\nTop 7 Features Mais Importantes no Modelo Enriquecido:")
    for rank, (fname, imp) in enumerate(feat_imp[:7], 1):
        is_new = "★ [NOVA]" if "user_" in fname else "  [Sessão]"
        print(f"  {rank}. {fname:<30} {is_new} : {imp*100:5.2f}%")
        
    return df_journey, df_gold, (acc_b, acc_e, auc_b, auc_e, prec_b, prec_e, rec_b, rec_e, f1_b, f1_e)


if __name__ == "__main__":
    run_evaluation_and_comparison()
