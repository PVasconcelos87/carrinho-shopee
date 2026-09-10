"""
Modulo: feature_engineering.py
Descrição: Processamento e Engenharia de Features (Camadas Silver -> Gold).
Converte logs de eventos de e-commerce (view, cart, purchase) em um dataset de 
carrinhos agregados com features preditivas e o rótulo alvo (target_is_abandoned).
"""

import pandas as pd
import numpy as np

def build_cart_features(df_events):
    """
    Agrega o log de eventos brutos ao nível de sessão/carrinho (user_session).
    
    Parâmetros:
        df_events (pd.DataFrame): DataFrame com colunas [event_time, event_type, product_id,
                                                    category_id, category_code, brand, price,
                                                    user_id, user_session]
                                                    
    Retorna:
        pd.DataFrame: Gold Dataset com 1 linha por carrinho com itens (`user_session`), 
                      contendo features numéricas/categóricas e a coluna target `is_abandoned`.
    """
    # Converte event_time para datetime
    df_events["event_time_dt"] = pd.to_datetime(df_events["event_time"])
    df_events = df_events.sort_values("event_time_dt").reset_index(drop=True)
    
    # Filtra apenas sessões que tiveram pelo menos 1 evento de carrinho ('cart')
    sessions_with_cart = set(df_events[df_events["event_type"] == "cart"]["user_session"].unique())
    
    # Ordena as sessões cronologicamente pelo timestamp do primeiro evento
    session_order = (
        df_events[df_events["user_session"].isin(sessions_with_cart)]
        .groupby("user_session")["event_time_dt"]
        .min()
        .sort_values()
        .index
    )
    
    cart_records = []
    
    # Rastreamento da jornada temporal de cada comprador (user_id) sem vazamento de dados
    user_history = {}
    
    for session_id in session_order:
        group = df_events[df_events["user_session"] == session_id]
        user_id = group["user_id"].iloc[0]
        
        # Separar por tipo de evento
        view_events = group[group["event_type"] == "view"]
        cart_events = group[group["event_type"] == "cart"]
        purchase_events = group[group["event_type"] == "purchase"]
        
        # Target: Se NÃO houve compra registrada na mesma sessão para o carrinho -> Abandono (1), senão (0)
        is_abandoned = 1 if purchase_events.empty else 0
        
        # Features do Carrinho
        num_cart_items = len(cart_events)
        total_cart_value = cart_events["price"].sum()
        max_item_price = cart_events["price"].max()
        min_item_price = cart_events["price"].min()
        avg_item_price = cart_events["price"].mean()
        
        # Diversidade de marcas e categorias no carrinho
        num_distinct_brands = cart_events["brand"].nunique()
        num_distinct_categories = cart_events["category_code"].nunique()
        
        # Categoria principal no carrinho (tratando valores nulos com segurança)
        cat_non_null = cart_events["category_code"].dropna()
        if not cat_non_null.empty:
            mode_series = cat_non_null.mode()
            main_category = mode_series.iloc[0] if not mode_series.empty else "other"
        else:
            main_category = "other"
            
        main_category_group = str(main_category).split(".")[0] if "." in str(main_category) else str(main_category)
        
        # Features de Engajamento e Navegação da Sessão Atual
        num_views_before_cart = len(view_events)
        view_to_cart_ratio = num_views_before_cart / max(1, num_cart_items)
        
        # Tempo total da sessão
        first_event_time = group["event_time_dt"].min()
        last_cart_time = cart_events["event_time_dt"].max()
        session_duration_sec = (last_cart_time - first_event_time).total_seconds()
        
        # Temporal
        hour_of_day = last_cart_time.hour
        day_of_week = last_cart_time.dayofweek
        is_weekend = 1 if day_of_week in [5, 6] else 0
        is_night = 1 if hour_of_day in [0, 1, 2, 3, 4, 5, 22, 23] else 0
        
        # Novas Features: Histórico Acumulado do Comprador (user_id) antes desta sessão
        u_hist = user_history.get(user_id, {
            "prior_views": 0,
            "prior_carts": 0,
            "prior_abandoned_carts": 0,
            "first_seen": first_event_time
        })
        
        prior_views = u_hist["prior_views"]
        prior_carts = u_hist["prior_carts"]
        prior_abandoned = u_hist["prior_abandoned_carts"]
        total_cumulative_views = prior_views + num_views_before_cart
        user_lifetime_hours = (first_event_time - u_hist["first_seen"]).total_seconds() / 3600.0
        prior_abandon_rate = (prior_abandoned / prior_carts) if prior_carts > 0 else 0.5
        
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
            "num_views_before_cart": num_views_before_cart,
            "view_to_cart_ratio": view_to_cart_ratio,
            "session_duration_sec": max(0.0, session_duration_sec),
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week,
            "is_weekend": is_weekend,
            "is_night": is_night,
            # Features da Jornada do Comprador
            "user_prior_views": prior_views,
            "user_prior_carts": prior_carts,
            "user_prior_abandoned_carts": prior_abandoned,
            "user_total_cumulative_views": total_cumulative_views,
            "user_lifetime_hours": max(0.0, user_lifetime_hours),
            "user_prior_abandon_rate": prior_abandon_rate,
            "is_abandoned": is_abandoned
        })
        
        # Atualiza histórico do comprador
        u_hist["prior_views"] += num_views_before_cart
        u_hist["prior_carts"] += 1
        if is_abandoned == 1:
            u_hist["prior_abandoned_carts"] += 1
        user_history[user_id] = u_hist
        
    df_gold = pd.DataFrame(cart_records)
    return df_gold


def evaluate_buyer_journey_stats(df_events):
    """
    Avalia a jornada completa de cada comprador (user_id):
    - Quantidade de visualizações (views) que o mesmo comprador realizou antes do último carrinho que virou compra.
    - Quantidade de carrinhos (carts) que o mesmo comprador montou antes do último que virou compra.
    - Duração temporal da jornada de conversão.
    
    Retorna:
        pd.DataFrame: Métricas de jornada por comprador que concluiu compra.
    """
    df_events = df_events.copy()
    if "event_time_dt" not in df_events.columns:
        df_events["event_time_dt"] = pd.to_datetime(df_events["event_time"])
    df_events = df_events.sort_values("event_time_dt").reset_index(drop=True)
    
    purchases = df_events[df_events["event_type"] == "purchase"]
    purchasing_users = purchases["user_id"].unique()
    
    records = []
    for uid in purchasing_users:
        u_events = df_events[df_events["user_id"] == uid]
        first_purch = u_events[u_events["event_type"] == "purchase"].iloc[0]
        purch_time = first_purch["event_time_dt"]
        purch_session = first_purch["user_session"]
        
        events_before = u_events[u_events["event_time_dt"] < purch_time]
        prior_sess = events_before[events_before["user_session"] != purch_session]
        
        views_prior = len(prior_sess[prior_sess["event_type"] == "view"])
        views_final_sess = len(u_events[(u_events["user_session"] == purch_session) & (u_events["event_type"] == "view") & (u_events["event_time_dt"] < purch_time)])
        total_views = views_prior + views_final_sess
        
        prior_carts = prior_sess[prior_sess["event_type"] == "cart"]["user_session"].nunique()
        prior_cart_items = len(prior_sess[prior_sess["event_type"] == "cart"])
        
        first_touch = u_events["event_time_dt"].min()
        journey_hours = (purch_time - first_touch).total_seconds() / 3600.0
        
        records.append({
            "user_id": uid,
            "purchase_session": purch_session,
            "prior_cart_sessions": prior_carts,
            "prior_cart_items": prior_cart_items,
            "views_in_prior_sessions": views_prior,
            "views_in_final_session": views_final_sess,
            "total_views_before_purchase": total_views,
            "journey_duration_hours": round(journey_hours, 2),
            "total_prior_sessions": prior_sess["user_session"].nunique()
        })
        
    return pd.DataFrame(records)


if __name__ == "__main__":
    from data_generator import generate_ecommerce_events
    df_raw = generate_ecommerce_events(num_sessions=500)
    df_gold = build_cart_features(df_raw)
    print(f"Dataset Gold construído com sucesso! Total de carrinhos: {len(df_gold)}")
    print(f"Taxa de abandono observada: {df_gold['is_abandoned'].mean():.2%}")
    print(df_gold.head())

