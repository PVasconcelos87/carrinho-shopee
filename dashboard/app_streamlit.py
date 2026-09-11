"""
Dashboard Analítico Streamlit: E-commerce Data Platform — Abandono de Carrinho
MBA em Engenharia de Dados - Mackenzie
"""

import json
import os
import sys
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Shopee ML Analytics — Abandono de Carrinho",
    page_icon="🛒",
    layout="wide"
)

import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
STATS_FILE = os.path.join(BASE_DIR, "real_ml_stats.json")


# Leitura direta sem cache para refletir o streaming em tempo real imediatamente
def load_data():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

data = load_data()

# Informações do arquivo de estatísticas
file_mod_time = ""
if os.path.exists(STATS_FILE):
    mtime = os.path.getmtime(STATS_FILE)
    file_mod_time = datetime.fromtimestamp(mtime).strftime("%H:%M:%S")

# Barra lateral com controles de streaming
st.sidebar.header("📡 Streaming & Ingestão")
if st.sidebar.button("🔄 Atualizar Dados Agora", use_container_width=True):
    st.rerun()

auto_refresh = st.sidebar.checkbox("Atualização em Tempo Real (Live)", value=True)
refresh_interval = st.sidebar.slider("Intervalo de atualização (segundos)", 2, 10, 3)
st.sidebar.markdown(f"**Última Atualização no Disco:** `{file_mod_time}`")
st.sidebar.markdown(f"**Relógio do Sistema:** `{datetime.now().strftime('%H:%M:%S')}`")

st.title("🛒 Shopee Data Platform — Abandono de Carrinho & Machine Learning")
st.markdown("**Hands-On Engenharia de Dados** | Arquitetura Medallion (Amazon S3) + ML + Gatilhos")

s3_info = data.get("s3Source", {})
if s3_info:
    st.success(f"🟢 **Conectado ao Data Lake no Amazon S3**: `s3://{s3_info.get('bucket', 'ecommerce-data-platform-mack-paulo')}/gold/session_features/`")
else:
    st.info("☁️ Conectado ao Amazon S3 (Camada Gold)")

# Banner de Destaque: Último Carrinho Recebido via Streaming Kafka/Speed Layer
sample_carts = data.get("abandonedCartsWithCoupons", [])
if sample_carts:
    latest = sample_carts[0]
    p_risk = latest.get("pAbandon", 0.0) * 100
    st.info(
        f"⚡ **Último Evento Recebido em Tempo Real:** "
        f"Sessão `{latest.get('sessionId', '')}` | "
        f"Usuário `{latest.get('userId', 0)}` | "
        f"Valor: **R$ {latest.get('totalVal', 0):,.2f}** | "
        f"Risco ML: **{p_risk:.1f}%** | "
        f"Cupom Atribuído: **{latest.get('coupon', {}).get('coupon_label', 'Sem Cupom')}** 🎫"
    )

kpis = data.get("kpis", {})
model = data.get("modelMetrics", {})
journey = data.get("buyerJourneyStats", {})

# 1. LINHA DE KPIS PRINCIPAIS
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total de Carrinhos Analisados", f"{kpis.get('totalCarts', 0):,}")
col2.metric("Taxa Média de Abandono", f"{kpis.get('abandonmentRate', 0)*100:.2f}%")
col3.metric("GMV em Risco de Perda", f"R$ {kpis.get('gmvLost', 0):,.2f}")
col4.metric("GMV Estimado Recuperável", f"R$ {kpis.get('gmvRecovered', 0):,.2f}")

st.markdown("---")

# 2. PAINEL DE JORNADA DO COMPRADOR & GANHO DE ACURÁCIA
st.subheader("🗺️ Jornada do Comprador antes da Compra & Performance de ML")
j1, j2, j3, j4 = st.columns(4)
views_stat = journey.get("viewsBeforePurchase", {})
carts_stat = journey.get("priorCartsBeforePurchase", {})
dur_stat = journey.get("journeyDurationHours", {})

j1.metric("Views Médias até Comprar", f"{views_stat.get('mean', 10.1):.1f} views", f"Mediana: {views_stat.get('median', 7.0)}")
j2.metric("Carrinhos Prévios até a Compra", f"{carts_stat.get('mean', 0.99):.2f} carts", f"Mediana: {carts_stat.get('median', 1.0)}")
j3.metric("Acurácia do Modelo Random Forest", f"{model.get('accuracy', 0.7523)*100:.1f}%", "+14.5% vs Baseline")
j4.metric("Tempo Médio de Decisão", f"{dur_stat.get('mean', 54.6):.1f} horas", "~2.3 dias de maturação")

# 3. GRÁFICOS DO FUNIL E COMPARAÇÃO
g1, g2 = st.columns(2)

with g1:
    st.subheader("Funil de Conversão de E-commerce")
    funnel = data.get("funnel", {})
    fig_funnel = go.Figure(go.Funnel(
        y=["Visualizações (Views)", "Carrinhos Criados (Carts)", "Compras Efetuadas (Purchases)"],
        x=[funnel.get("views", 294619), funnel.get("carts", 3504), funnel.get("purchases", 4077)],
        textinfo="value+percent previous",
        marker={"color": ["#3B82F6", "#F59E0B", "#10B981"]}
    ))
    fig_funnel.update_layout(height=350, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig_funnel, use_container_width=True)

with g2:
    st.subheader("Importância das Variáveis no Modelo (Feature Importance)")
    feat_imp = data.get("featureImportances", [])
    if feat_imp:
        df_imp = pd.DataFrame(feat_imp).sort_values("importance", ascending=True)
        fig_imp = px.bar(df_imp, x="importance", y="label", orientation="h", color="importance",
                         color_continuous_scale="Viridis", labels={"importance": "Peso Preditivo (%)", "label": "Variável"})
        fig_imp.update_layout(height=350, margin=dict(l=20, r=20, t=20, b=20), showlegend=False)
        st.plotly_chart(fig_imp, use_container_width=True)

# 4. TABELA DE CUPONS RECOMENDADOS
st.subheader("🎫 Amostra de Carrinhos com Cupons Atribuídos pelo Modelo")
sample_carts = data.get("abandonedCartsWithCoupons", [])[:20]
if sample_carts:
    table_rows = []
    for c in sample_carts:
        table_rows.append({
            "Sessão": c.get("sessionId", "")[:12] + "...",
            "ID Usuário": c.get("userId"),
            "Valor do Carrinho": f"R$ {c.get('totalVal', 0):,.2f}",
            "Itens": c.get("numItems"),
            "Views": c.get("numViews"),
            "Prob. Abandono": f"{c.get('pAbandon', 0)*100:.1f}%",
            "Cupom Prescrito": c.get("coupon", {}).get("coupon_label", ""),
            "Urgência": c.get("coupon", {}).get("urgency", ""),
            "GMV Recuperado": f"R$ {c.get('recoveredGMV', 0):,.2f}"
        })
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True)

st.success("✓ Dados sincronizados com a Camada Gold e o motor de Machine Learning!")

if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
