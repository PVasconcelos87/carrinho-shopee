"""
Modulo: model_pipeline.py
Descrição: Pipeline de Treinamento, Comparação de Modelos e Avaliação de Performance de ML
para Previsão de Abandono de Carrinho de E-commerce.
"""

import os
import joblib
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)

FEATURE_NUMERIC = [
    "num_cart_items",
    "total_cart_value",
    "max_item_price",
    "min_item_price",
    "avg_item_price",
    "num_distinct_brands",
    "num_distinct_categories",
    "num_views_before_cart",
    "view_to_cart_ratio",
    "session_duration_sec",
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "is_night",
    # Features Comportamentais do Comprador (Multi-session Journey)
    "user_prior_views",
    "user_prior_carts",
    "user_prior_abandoned_carts",
    "user_total_cumulative_views",
    "user_lifetime_hours",
    "user_prior_abandon_rate"
]

FEATURE_CATEGORICAL = [
    "main_category"
]

TARGET = "is_abandoned"


def get_preprocessor():
    """
    Cria o transformador de colunas (ColumnTransformer) para pré-processar
    variáveis numéricas (StandardScaler) e categóricas (OneHotEncoder).
    """
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), FEATURE_NUMERIC),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), FEATURE_CATEGORICAL)
        ]
    )
    return preprocessor


def train_and_evaluate_models(df_gold, test_size=0.2, random_state=42):
    """
    Treina e compara múltiplos modelos de classificação (Regressão Logística, Random Forest, Gradient Boosting).
    
    Parâmetros:
        df_gold (pd.DataFrame): Dataset Gold gerado pelo módulo feature_engineering.py
        test_size (float): Proporção do conjunto de teste (padrão 0.20)
        random_state (int): Semente para reprodutibilidade.
        
    Retorna:
        dict: Dicionário contendo os modelos treinados, métricas de avaliação e a melhor pipeline.
    """
    df_gold = df_gold.copy()
    for col in FEATURE_NUMERIC:
        if col not in df_gold.columns:
            df_gold[col] = 0.0
    for col in FEATURE_CATEGORICAL:
        if col not in df_gold.columns:
            df_gold[col] = "other"
            
    X = df_gold[FEATURE_NUMERIC + FEATURE_CATEGORICAL].fillna(0)
    y = df_gold[TARGET]
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    
    preprocessor = get_preprocessor()
    
    models = {
        "Regressão Logística (Baseline)": LogisticRegression(max_iter=1000, solver="liblinear", C=1.0, random_state=random_state),
        "Random Forest Classifier": RandomForestClassifier(n_estimators=120, max_depth=8, random_state=random_state),
        "HistGradientBoosting": HistGradientBoostingClassifier(max_iter=100, max_depth=6, random_state=random_state)
    }
    
    results = {}
    best_model_name = None
    best_roc_auc = -1.0
    best_pipeline = None
    
    for name, clf in models.items():
        pipe = Pipeline(steps=[
            ("preprocessor", preprocessor),
            ("classifier", clf)
        ])
        
        pipe.fit(X_train, y_train)
        
        y_pred = pipe.predict(X_test)
        y_proba = pipe.predict_proba(X_test)[:, 1] if hasattr(pipe, "predict_proba") else y_pred
        
        acc = accuracy_score(y_test, y_pred)
        roc_auc = roc_auc_score(y_test, y_proba)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        cm = confusion_matrix(y_test, y_pred)
        
        results[name] = {
            "pipeline": pipe,
            "accuracy": acc,
            "roc_auc": roc_auc,
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "confusion_matrix": cm,
            "y_test": y_test,
            "y_proba": y_proba
        }
        
        print(f"=== Modelo: {name} ===")
        print(f"  Accuracy:  {acc:.4f}")
        print(f"  ROC-AUC:   {roc_auc:.4f}")
        print(f"  Precision: {prec:.4f}")
        print(f"  Recall:    {rec:.4f}")
        print(f"  F1-Score:  {f1:.4f}\n")
        
        if roc_auc > best_roc_auc:
            best_roc_auc = roc_auc
            best_model_name = name
            best_pipeline = pipe
            
    print(f"★ Melhor Modelo Selecionado: {best_model_name} (ROC-AUC: {best_roc_auc:.4f})")
    
    # Salvar a melhor pipeline treinada
    os.makedirs("models", exist_ok=True)
    model_path = os.path.join("models", "cart_coupon_model.joblib")
    joblib.dump(best_pipeline, model_path)
    print(f"Modelo salvo em: {model_path}")
    
    return {
        "results": results,
        "best_model_name": best_model_name,
        "best_pipeline": best_pipeline,
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test
    }


if __name__ == "__main__":
    from data_generator import generate_ecommerce_events
    from feature_engineering import build_cart_features
    
    df_raw = generate_ecommerce_events(num_sessions=1500)
    df_gold = build_cart_features(df_raw)
    res = train_and_evaluate_models(df_gold)
