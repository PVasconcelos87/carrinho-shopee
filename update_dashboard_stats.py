"""
Script: update_dashboard_stats.py
Descrição: Atualiza real_ml_stats.json e data.js com os novos números do modelo enriquecido
com as métricas da jornada do comprador (visualizações e carrinhos antes da compra).
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATS_FILE = os.path.join(BASE_DIR, "real_ml_stats.json")
JS_FILE = os.path.join(BASE_DIR, "data.js")

def update_stats():
    print(f"Lendo {STATS_FILE}...")
    with open(STATS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Novas Métricas Consolidadas do Modelo Enriquecido
    data["modelMetrics"] = {
        "bestModelName": "Random Forest Classifier (Enriquecido)",
        "accuracy": 0.7523,
        "rocAuc": 0.6798,
        "precision": 0.7741,
        "recall": 0.9443,
        "f1": 0.8508,
        "confusionMatrix": {
            "tn": 20,
            "fp": 89,
            "fn": 18,
            "tp": 305
        }
    }

    # 2. Tabela Comparativa de Modelos
    data["modelsComparison"] = {
        "rf": {
            "name": "Random Forest Classifier (Vencedor)",
            "accuracy": 0.7523,
            "rocAuc": 0.6798,
            "precision": 0.7741,
            "recall": 0.9443,
            "f1": 0.8508,
            "cm": {"tn": 20, "fp": 89, "fn": 18, "tp": 305}
        },
        "hgb": {
            "name": "HistGradientBoosting",
            "accuracy": 0.7245,
            "rocAuc": 0.6190,
            "precision": 0.7757,
            "recall": 0.8885,
            "f1": 0.8283,
            "cm": {"tn": 26, "fp": 83, "fn": 36, "tp": 287}
        },
        "lr": {
            "name": "Regressão Logística (Baseline)",
            "accuracy": 0.7315,
            "rocAuc": 0.6842,
            "precision": 0.7607,
            "recall": 0.9350,
            "f1": 0.8389,
            "cm": {"tn": 14, "fp": 95, "fn": 21, "tp": 302}
        }
    }

    # 3. Estatísticas da Jornada do Comprador (Visualizações e Carrinhos antes da Compra)
    data["buyerJourneyStats"] = {
        "viewsBeforePurchase": {
            "mean": 10.1,
            "median": 7.0,
            "std": 8.08,
            "p25": 3.0,
            "p75": 16.0,
            "p90": 22.0,
            "min": 1,
            "max": 34
        },
        "priorCartsBeforePurchase": {
            "mean": 0.99,
            "median": 1.0,
            "std": 1.11,
            "p25": 0.0,
            "p75": 2.0,
            "p90": 3.0,
            "min": 0,
            "max": 5
        },
        "cartFrequencyDistribution": {
            "zeroCartsDirect": 42.7,
            "oneCartPrior": 29.8,
            "twoCartsPrior": 17.3,
            "threeCartsPrior": 6.7,
            "fourOrMoreCartsPrior": 3.5
        },
        "journeyDurationHours": {
            "mean": 54.6,
            "median": 47.8,
            "meanDays": 2.3,
            "medianDays": 2.0
        },
        "abandonmentByPriorCarts": {
            "0_prior": {"abandonRate": 0.792, "conversionRate": 0.208},
            "1_prior": {"abandonRate": 0.735, "conversionRate": 0.265},
            "2_prior": {"abandonRate": 0.690, "conversionRate": 0.310},
            "3_plus_prior": {"abandonRate": 0.558, "conversionRate": 0.442}
        }
    }

    # 4. Importância das Variáveis Atualizada
    data["featureImportances"] = [
        {"feature": "session_duration_sec", "importance": 12.8, "label": "Duração da Sessão (seg)"},
        {"feature": "num_views_before_cart", "importance": 9.8, "label": "Visualizações na Sessão"},
        {"feature": "user_lifetime_hours", "importance": 8.7, "label": "Horas de Maturação do Usuário ★"},
        {"feature": "total_cart_value", "importance": 7.4, "label": "Valor Total do Carrinho"},
        {"feature": "user_total_cumulative_views", "importance": 7.2, "label": "Views Totais Acumuladas ★"},
        {"feature": "avg_item_price", "importance": 7.1, "label": "Preço Médio dos Itens"},
        {"feature": "max_item_price", "importance": 6.9, "label": "Preço Máximo do Item"},
        {"feature": "user_prior_carts", "importance": 5.8, "label": "Carrinhos Prévios Montados ★"}
    ]

    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ {STATS_FILE} atualizado com sucesso!")

    # 5. Exporta para data.js
    with open(STATS_FILE, "r", encoding="utf-8") as f:
        data_str = f.read()

    js_content = f"// Dataset Integrado Real para execução offline/file:// sem restrições de CORS\nwindow.REAL_ML_STATS = {data_str};\n"
    with open(JS_FILE, "w", encoding="utf-8") as f:
        f.write(js_content)

    print(f"✓ {JS_FILE} atualizado com sucesso ({os.path.getsize(JS_FILE) / 1024:.1f} KB)!")

if __name__ == "__main__":
    update_stats()
