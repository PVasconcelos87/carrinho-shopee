"""
Script: train_excel_model.py
Descrição: Treina o Modelo de Machine Learning (Scikit-Learn) diretamente em cima de planilhas Excel (.xlsx).
Gera um arquivo de exemplo 'modelo_carrinho_excel.xlsx' se nenhuma planilha for fornecida.
Treina o classificador de risco de abandono (is_abandoned) e o classificador de Perfil de Cliente
(high_intent, bargain_hunter, browser).
"""

import os
import random
import joblib
import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")
EXCEL_FILE_PATH = os.path.join(BASE_DIR, "modelo_carrinho_excel.xlsx")
MODEL_ABANDONMENT_PATH = os.path.join(MODELS_DIR, "cart_coupon_model_excel.joblib")
MODEL_PROFILE_PATH = os.path.join(MODELS_DIR, "user_profile_model_excel.joblib")


def generate_sample_excel_dataset(filepath, num_rows=1500):
    """
    Gera uma planilha Excel exemplo 'modelo_carrinho_excel.xlsx' calibrada com dados reais de e-commerce.
    """
    print(f"Gerando planilha Excel de exemplo em: {filepath} ({num_rows} registros)...")
    np.random.seed(42)

    session_ids = [f"sess_{10000 + i}" for i in range(num_rows)]
    user_ids = [np.random.choice([386070015, 244951053, 500000000 + np.random.randint(1, 1000)]) for _ in range(num_rows)]
    
    total_cart_values = np.round(np.random.exponential(scale=350, size=num_rows) + 40, 2)
    num_items = np.random.choice([1, 2, 3, 4, 5], size=num_rows, p=[0.55, 0.25, 0.12, 0.05, 0.03])
    num_views = np.array([int(i * np.random.uniform(1.2, 3.5)) + np.random.randint(1, 4) for i in num_items])
    session_durations = np.array([int(v * np.random.uniform(15, 45)) + np.random.randint(10, 60) for v in num_views])
    hours = np.random.randint(0, 24, size=num_rows)
    is_nights = np.array([1 if (h < 6 or h >= 22) else 0 for h in hours])

    # Features Históricas do Comprador
    user_prior_views_list = []
    user_prior_carts_list = []
    user_tracker = {}

    for uid in user_ids:
        hist = user_tracker.get(uid, {"views": 0, "carts": 0})
        user_prior_views_list.append(hist["views"])
        user_prior_carts_list.append(hist["carts"])
        hist["views"] += random.randint(1, 5)
        hist["carts"] += 1
        user_tracker[uid] = hist

    # Lógica probabilística para gerar perfis de clientes realistas
    profiles = []
    is_abandoneds = []

    for i in range(num_rows):
        v = num_views[i]
        val = total_cart_values[i]
        dur = session_durations[i]
        night = is_nights[i]
        prior_c = user_prior_carts_list[i]

        # Determina perfil
        if v <= 3 and dur < 90:
            prof = "high_intent"
            p_ab = 0.25 if not night else 0.40
        elif v >= 6 or (night == 1 and val >= 400):
            prof = "bargain_hunter"
            p_ab = 0.70 if val >= 300 else 0.55
        else:
            prof = "browser"
            p_ab = 0.50

        # Histórico de carrinhos prévios amadurece a decisão do comprador
        if prior_c >= 2:
            p_ab -= 0.15
        elif prior_c == 1:
            p_ab -= 0.05
        p_ab = max(0.10, min(0.90, p_ab))

        profiles.append(prof)
        is_ab = 1 if np.random.rand() < p_ab else 0
        is_abandoneds.append(is_ab)

    df_excel = pd.DataFrame({
        "session_id": session_ids,
        "user_id": user_ids,
        "total_cart_value": total_cart_values,
        "num_cart_items": num_items,
        "num_views_before_cart": num_views,
        "user_prior_views": user_prior_views_list,
        "user_prior_carts": user_prior_carts_list,
        "session_duration_sec": session_durations,
        "hour_of_day": hours,
        "is_night": is_nights,
        "user_profile": profiles,
        "is_abandoned": is_abandoneds
    })

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df_excel.to_excel(filepath, index=False, engine="openpyxl")
    print(f"✓ Planilha Excel '{os.path.basename(filepath)}' gerada com sucesso com {len(df_excel)} linhas!")
    return df_excel


def load_dataset_from_excel(filepath):
    """
    Lê a planilha Excel (.xlsx ou .xls). Se não existir, gera a planilha de exemplo.
    """
    if not os.path.exists(filepath):
        print(f"Aviso: Planilha '{filepath}' não encontrada. Criando nova planilha de exemplo...")
        return generate_sample_excel_dataset(filepath)

    print(f"Lendo dados diretamente da planilha Excel: {filepath}...")
    df = pd.read_excel(filepath, engine="openpyxl")
    print(f"✓ Planilha Excel carregada com sucesso! Total de registros: {len(df):,}")
    return df


def train_models_from_excel(excel_path=EXCEL_FILE_PATH):
    print("==========================================================================")
    print("  TREINAMENTO DE MACHINE LEARNING COM BASE EM PLANILHA EXCEL (.XLSX)")
    print("==========================================================================")

    df = load_dataset_from_excel(excel_path)
    os.makedirs(MODELS_DIR, exist_ok=True)

    # Feature Engineering para o Modelo
    df["view_to_cart_ratio"] = np.round(df["num_views_before_cart"] / np.maximum(df["num_cart_items"], 1), 2)

    feature_cols = [
        "total_cart_value", "num_cart_items", "num_views_before_cart",
        "view_to_cart_ratio", "session_duration_sec", "hour_of_day", "is_night"
    ]
    if "user_prior_views" in df.columns:
        feature_cols.append("user_prior_views")
    if "user_prior_carts" in df.columns:
        feature_cols.append("user_prior_carts")

    X = df[feature_cols].fillna(0)
    y_abandonment = df["is_abandoned"]
    y_profile = df["user_profile"]

    # --------------------------------------------------------------------------
    # 1. TREINAMENTO DO CLASSIFICADOR DE RISCO DE ABANDONO (Target: is_abandoned)
    # --------------------------------------------------------------------------
    print("\n[1/2] Treinando Modelo de Abandono (Random Forest)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y_abandonment, test_size=0.2, random_state=42)

    clf_abandonment = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    clf_abandonment.fit(X_train, y_train)

    y_pred_ab = clf_abandonment.predict(X_test)
    y_prob_ab = clf_abandonment.predict_proba(X_test)[:, 1]

    acc_ab = accuracy_score(y_test, y_pred_ab)
    roc_ab = roc_auc_score(y_test, y_prob_ab)

    print(f"  ✓ Acurácia do Modelo de Abandono: {acc_ab * 100:.2f}%")
    print(f"  ✓ ROC-AUC Score: {roc_ab:.4f}")

    joblib.dump(clf_abandonment, MODEL_ABANDONMENT_PATH)
    print(f"  ✓ Modelo salvo em: {MODEL_ABANDONMENT_PATH}")

    # --------------------------------------------------------------------------
    # 2. TREINAMENTO DO CLASSIFICADOR DE PERFIL DE CLIENTE (Target: user_profile)
    # --------------------------------------------------------------------------
    print("\n[2/2] Treinando Modelo de Perfil do Cliente (high_intent / bargain_hunter / browser)...")
    X_train_p, X_test_p, y_train_p, y_test_p = train_test_split(X, y_profile, test_size=0.2, random_state=42)

    clf_profile = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
    clf_profile.fit(X_train_p, y_train_p)

    y_pred_p = clf_profile.predict(X_test_p)
    acc_p = accuracy_score(y_test_p, y_pred_p)

    print(f"  ✓ Acurácia do Classificador de Perfil: {acc_p * 100:.2f}%")
    print(classification_report(y_test_p, y_pred_p))

    joblib.dump(clf_profile, MODEL_PROFILE_PATH)
    print(f"  ✓ Modelo de Perfis salvo em: {MODEL_PROFILE_PATH}")

    print("\n==========================================================================")
    print("  ✓ PROCESSO CONCLUÍDO COM SUCESSO NO EXCEL!")
    print("==========================================================================")
    return clf_abandonment, clf_profile


if __name__ == "__main__":
    train_models_from_excel()
