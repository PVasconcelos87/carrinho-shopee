#!/usr/bin/env python3
"""
Script Orquestrador Principal: run_pipeline.py
Executa o fluxo completo do Projeto de Engenharia de Dados & Machine Learning:
1. Ingestão/Carregamento dos Dados Reais da pasta /basededados (2019-Oct.csv, 2019-Nov.csv)
2. Processamento e Engenharia de Features (Camadas Silver -> Gold)
3. Treinamento e Comparação de Modelos de ML (Regressão Logística, Random Forest, Gradient Boosting)
4. Seleção e Avaliação do Melhor Modelo (ROC-AUC, Precision, Recall, F1, Matriz de Confusão)
5. Execução do Motor de Decisão para Oferta de Cupons de Desconto
6. Geração de Relatório de Resultados e Impacto Financeiro Estimado
"""

import sys
import os
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np

# Adiciona o diretório atual ao path de execução
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data_loader import load_basededados_dataset, get_base_dados_files
from src.data_generator import generate_ecommerce_events
from src.feature_engineering import build_cart_features, evaluate_buyer_journey_stats
from src.model_pipeline import train_and_evaluate_models
from src.coupon_recommender import CouponRecommender


def main():
    print("=" * 80)
    print("      SHOPEE CART ABANDONMENT & COUPON RECOMMENDATION ML PIPELINE")
    print("      MBA em Engenharia de Dados - Projeto Hands-On (Sprint 1)")
    print("=" * 80)
    
    # 1. Ingestão (Bronze) - Carrega do 2019-Nov.csv ou da pasta /basededados ou gera base multi-sessão
    if os.path.exists("2019-Nov.csv"):
        print(f"\n[ETAPA 1/6] Carregando dataset real a partir de 2019-Nov.csv...")
        df_raw_events = pd.read_csv("2019-Nov.csv", nrows=150000)
    elif get_base_dados_files():
        print(f"\n[ETAPA 1/6] Carregando dataset real a partir da pasta /basededados...")
        df_raw_events = load_basededados_dataset(sample_n=150000)
    else:
        print("\n[ETAPA 1/6] Gerando dados multi-sessão da jornada do comprador (Fallback)...")
        from src.evaluate_buyer_journey import generate_multi_session_ecommerce_events
        df_raw_events = generate_multi_session_ecommerce_events(num_users=1000, random_seed=42)
        
    print(f" -> Total de eventos brutos registrados: {len(df_raw_events):,}")
    print(f" -> Compradores únicos no log: {df_raw_events['user_id'].nunique():,}")
    print(f" -> Distribuição de eventos por tipo:\n{df_raw_events['event_type'].value_counts().to_string()}\n")
    
    # 2. Avaliação Específica: Jornada do Comprador Antes da Compra Final
    print("[ETAPA 2/6] Avaliando quantidade de visualizações e carrinhos antes da compra...")
    df_journey = evaluate_buyer_journey_stats(df_raw_events)
    if not df_journey.empty:
        v_mean = df_journey["total_views_before_purchase"].mean()
        v_median = df_journey["total_views_before_purchase"].median()
        c_mean = df_journey["prior_cart_sessions"].mean()
        c_median = df_journey["prior_cart_sessions"].median()
        dur_mean = df_journey["journey_duration_hours"].mean()
        direct_purch_pct = (df_journey["prior_cart_sessions"] == 0).mean() * 100
        
        print(f" -> Total de compradores convertidos em compra: {len(df_journey):,}")
        print(f" -> Visualizações antes da compra : Média = {v_mean:.1f} views | Mediana = {v_median:.1f} views")
        print(f" -> Carrinhos prévios antes do final : Média = {c_mean:.2f} carts | Mediana = {c_median:.1f} carts")
        print(f" -> Conversão direta (0 carrinhos prévios) : {direct_purch_pct:.1f}% dos compradores")
        print(f" -> Conversão após abandono prévio (1+ carts) : {100.0 - direct_purch_pct:.1f}% dos compradores")
        print(f" -> Duração média da jornada até comprar: {dur_mean:.1f} horas ({dur_mean/24:.1f} dias)\n")
    else:
        print(" -> Nenhum evento de compra registrado no conjunto de eventos.\n")

    # 3. Engenharia de Features (Gold)
    print("[ETAPA 3/6] Processando e transformando em dataset de carrinhos enriquecido (Camada Gold)...")
    df_gold = build_cart_features(df_raw_events)
    print(f" -> Total de carrinhos reconstruídos: {len(df_gold):,}")
    print(f" -> Taxa de abandono observada no dataset: {df_gold['is_abandoned'].mean():.2%}")
    print(f" -> Valor total acumulado nos carrinhos: R$ {df_gold['total_cart_value'].sum():,.2f}\n")
    
    # 4. Treinamento e Comparação de Modelos de ML
    print("[ETAPA 4/6] Treinando e comparando algoritmos de Machine Learning...")
    ml_output = train_and_evaluate_models(df_gold, test_size=0.20, random_state=42)
    best_name = ml_output["best_model_name"]
    best_pipe = ml_output["best_pipeline"]
    
    # 5. Avaliação do Melhor Modelo
    print(f"\n[ETAPA 5/6] Resultados do Modelo Vencedor ({best_name}):")
    results = ml_output["results"][best_name]
    print(f" -> Acurácia:             {results['accuracy']:.4f}")
    print(f" -> ROC-AUC:              {results['roc_auc']:.4f}")
    print(f" -> Precisão (Precision): {results['precision']:.4f}")
    print(f" -> Revocação (Recall):   {results['recall']:.4f}")
    print(f" -> F1-Score:             {results['f1']:.4f}")
    print(" -> Matriz de Confusão [TN, FP / FN, TP]:")
    print(f"    {results['confusion_matrix']}\n")
    
    # 6. Recomendação de Cupons de Desconto
    print("[ETAPA 6/6] Executando o Motor de Decisão para Recomendação de Cupons...")
    recommender = CouponRecommender(best_pipe)
    
    # Processa lote de teste
    X_test = ml_output["X_test"]
    df_test_carts = df_gold.loc[X_test.index].copy()
    
    df_recommendations = recommender.process_cart_batch(df_test_carts)
    
    print("\n" + "=" * 80)
    print("                RESUMO EXECUTIVO DE OFERTA DE CUPONS DE DESCONTO")
    print("=" * 80)
    
    coupon_summary = df_recommendations["coupon_label"].value_counts()
    print("\nDistribuição de Cupons Recomendados:")
    for label, count in coupon_summary.items():
        pct = count / len(df_recommendations)
        print(f"  • {label:<35}: {count:3d} carrinhos ({pct:6.1%})")
        
    total_gmv_test = df_recommendations["total_cart_value"].sum()
    total_gmv_at_risk = df_recommendations[df_recommendations["p_abandonment"] >= 0.50]["total_cart_value"].sum()
    estimated_recovered_gmv = df_recommendations["estimated_recovered_gmv"].sum()
    
    print("\nImpacto Financeiro Estimado no Conjunto de Teste:")
    print(f"  • Valor Total Transacionado no Carrinho:  R$ {total_gmv_test:12,.2f}")
    print(f"  • GMV em Alto Risco de Abandono (p>=50%): R$ {total_gmv_at_risk:12,.2f}")
    print(f"  • GMV Potencialmente Recuperado c/ Cupom: R$ {estimated_recovered_gmv:12,.2f}")
    print(f"  • Taxa Potencial de Recuperação de GMV:   {estimated_recovered_gmv / max(1, total_gmv_at_risk):12.1%}")
    
    print("\nAmostra de Carrinhos com Cupons Atribuídos:")
    cols_show = ["user_session", "total_cart_value", "p_abandonment", "coupon_label", "urgency_level", "estimated_recovered_gmv"]
    print(df_recommendations[cols_show].head(10).to_string(index=False))
    
    print("\nPipeline executado com sucesso!")


if __name__ == "__main__":
    main()
