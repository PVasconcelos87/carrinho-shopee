"""
Modulo: data_generator.py
Descrição: Gerador de dados sintéticos de eventos de e-commerce seguindo o schema do Kaggle 
("eCommerce behavior data from multi category store") especificado no Relatório da Sprint 1.
"""

import uuid
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Categorias e Marcas de E-commerce para o domínio Shopee
SAMPLE_PRODUCTS = [
    {"id": 1004856, "cat_id": 2053013555631882655, "cat_code": "electronics.smartphone", "brand": "samsung", "price_min": 150.0, "price_max": 1200.0},
    {"id": 1005115, "cat_id": 2053013555631882655, "cat_code": "electronics.smartphone", "brand": "apple", "price_min": 600.0, "price_max": 1500.0},
    {"id": 1004249, "cat_id": 2053013555631882655, "cat_code": "electronics.smartphone", "brand": "xiaomi", "price_min": 100.0, "price_max": 500.0},
    {"id": 1307067, "cat_id": 2053013558920217029, "cat_code": "electronics.audio.headphone", "brand": "sony", "price_min": 80.0, "price_max": 350.0},
    {"id": 1307070, "cat_id": 2053013558920217029, "cat_code": "electronics.audio.headphone", "brand": "jbl", "price_min": 30.0, "price_max": 180.0},
    {"id": 1403011, "cat_id": 2053013557972304183, "cat_code": "computers.notebook", "brand": "dell", "price_min": 450.0, "price_max": 2000.0},
    {"id": 1403015, "cat_id": 2053013557972304183, "cat_code": "computers.notebook", "brand": "lenovo", "price_min": 350.0, "price_max": 1400.0},
    {"id": 28700681, "cat_id": 2053013565463329755, "cat_code": "apparel.shoes", "brand": "nike", "price_min": 50.0, "price_max": 250.0},
    {"id": 28700685, "cat_id": 2053013565463329755, "cat_code": "apparel.shoes", "brand": "adidas", "price_min": 45.0, "price_max": 220.0},
    {"id": 3601405, "cat_id": 2053013563810775923, "cat_code": "appliances.kitchen.refrigerators", "brand": "lg", "price_min": 500.0, "price_max": 2200.0},
    {"id": 3601410, "cat_id": 2053013563810775923, "cat_code": "appliances.kitchen.refrigerators", "brand": "brastemp", "price_min": 400.0, "price_max": 1800.0},
    {"id": 5100816, "cat_id": 2053013553375347477, "cat_code": "beauty.cosmetics", "brand": "nivea", "price_min": 5.0, "price_max": 40.0},
    {"id": 5100820, "cat_id": 2053013553375347477, "cat_code": "beauty.cosmetics", "brand": "loreal", "price_min": 10.0, "price_max": 65.0},
]

def generate_ecommerce_events(num_sessions=2500, num_users=700, random_seed=42):
    """
    Gera um DataFrame Pandas simulando a camada Bronze (Raw Events), com suporte a
    jornadas completas de compradores recorrentes (multi-session buyer journeys).
    
    Parâmetros:
        num_sessions (int): Quantidade de sessões de navegação no total.
        num_users (int): Quantidade de compradores únicos recorrentes no pool.
        random_seed (int): Semente aleatória para reprodutibilidade.
        
    Retorna:
        pd.DataFrame: Log de eventos no formato Kaggle eCommerce.
    """
    random.seed(random_seed)
    np.random.seed(random_seed)
    
    events = []
    start_date = datetime(2026, 10, 1, 0, 0, 0)
    
    # Pool de compradores com perfis consolidados
    user_pool = []
    for i in range(num_users):
        u_intent = random.choices(["high_intent", "browser", "bargain_hunter"], weights=[0.35, 0.40, 0.25])[0]
        fav_prod = random.choice(SAMPLE_PRODUCTS)
        user_pool.append({
            "user_id": 500000000 + i,
            "intent": u_intent,
            "favorite_cat": fav_prod["cat_code"],
            "clock": start_date + timedelta(days=random.randint(0, 15), hours=random.randint(0, 18)),
            "session_count": 0
        })
        
    # Garante presença dos usuários VIP do projeto
    user_pool[0]["user_id"] = 386070015
    user_pool[1]["user_id"] = 244951053
    
    for session_idx in range(1, num_sessions + 1):
        user = random.choice(user_pool)
        user["session_count"] += 1
        user_id = user["user_id"]
        user_intent = user["intent"]
        
        session_id = str(uuid.uuid4())
        session_start = user["clock"]

        
        # 1. Visualizações (views)
        num_views = random.randint(1, 10) if user_intent == "browser" else random.randint(1, 4)
        curr_time = session_start
        
        viewed_products = []
        for _ in range(num_views):
            prod = random.choice(SAMPLE_PRODUCTS)
            price = round(random.uniform(prod["price_min"], prod["price_max"]), 2)
            viewed_products.append((prod, price))
            
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
            curr_time += timedelta(seconds=random.randint(10, 180))
            
        # 2. Adição ao Carrinho (cart)
        # Probabilidade de adicionar ao carrinho
        if user_intent == "high_intent":
            cart_prob = 0.90
        elif user_intent == "bargain_hunter":
            cart_prob = 0.70
        else:
            cart_prob = 0.30
            
        cart_products = []
        if random.random() < cart_prob:
            # Seleciona de 1 a 3 produtos visualizados para adicionar ao carrinho
            items_to_cart = random.sample(viewed_products, min(len(viewed_products), random.randint(1, 3)))
            for prod, price in items_to_cart:
                cart_products.append((prod, price))
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
                curr_time += timedelta(seconds=random.randint(15, 240))
                
        # 3. Compra (purchase) vs Abandono (No Purchase)
        if cart_products:
            total_cart_val = sum(p[1] for p in cart_products)
            
            # Fatores que aumentam o risco de abandono:
            # - Alto valor total do carrinho
            # - Poucas visualizações prévias (compra por impulso sem convicção)
            # - Horário da madrugada (browsing noturno)
            # - Perfil bargain_hunter sem cupom
            abandon_risk = 0.35
            if total_cart_val > 800:
                abandon_risk += 0.30
            elif total_cart_val > 400:
                abandon_risk += 0.15
                
            if num_views <= 2:
                abandon_risk += 0.10
                
            if session_start.hour in [0, 1, 2, 3, 4, 5]:
                abandon_risk += 0.15
                
            if user_intent == "bargain_hunter":
                abandon_risk += 0.20
                
            # Limita probabilidade entre 0.05 e 0.95
            abandon_risk = max(0.05, min(0.95, abandon_risk))
            
            # Se NÃO abandonar, gera o evento de compra para todos os itens do carrinho
            if random.random() > abandon_risk:
                for prod, price in cart_products:
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

        # Avança o relógio deste comprador para sua próxima sessão
        user["clock"] = curr_time + timedelta(hours=random.randint(3, 72))

    df_events = pd.DataFrame(events)
    df_events["event_time_dt"] = pd.to_datetime(df_events["event_time"])
    df_events = df_events.sort_values("event_time_dt").drop(columns=["event_time_dt"]).reset_index(drop=True)
    return df_events

if __name__ == "__main__":
    df = generate_ecommerce_events(num_sessions=100)
    print(f"Dataset sintético gerado com sucesso! Total de eventos: {len(df)}")
    print(df.head(10))
