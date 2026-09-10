"""
Script: kafka_triggers_simulator.py
Descrição: Simulador do Pipeline de Mensageria (Kafka / Event Streaming) com a execução dos 2 Gatilhos Temporais:
- Gatilho 1 (Cart + 5 Minutos sem compra): Dispara notificação/lembrete de engajamento suave.
- Gatilho 2 (Cart + 1 Hora sem compra): Executa a inferência de Machine Learning (modelo Excel),
  classifica a sessão em um dos 3 Perfis de Clientes (high_intent, bargain_hunter, browser)
  e prescreve a oferta de cupom/benefício ideal.
"""

import os
import time
import json
import joblib
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "models")
MODEL_ABANDONMENT_PATH = os.path.join(MODELS_DIR, "cart_coupon_model_excel.joblib")
MODEL_PROFILE_PATH = os.path.join(MODELS_DIR, "user_profile_model_excel.joblib")


class KafkaTriggerSimulator:
    def __init__(self):
        self.clf_abandonment = self._load_model(MODEL_ABANDONMENT_PATH)
        self.clf_profile = self._load_model(MODEL_PROFILE_PATH)

    def _load_model(self, path):
        if os.path.exists(path):
            return joblib.load(path)
        return None

    def process_cart_event(self, session_event):
        """
        Recebe um evento do tipo 'cart' e executa o encadeamento dos 2 gatilhos temporais.
        
        Parâmetros:
            session_event (dict): Dados da sessão contendo user_id, user_session, total_cart_value, etc.
        """
        session_id = session_event.get("user_session", "sess_unknown")
        user_id = session_event.get("user_id", 0)
        cart_value = session_event.get("total_cart_value", 150.0)

        print(f"\n==========================================================================")
        print(f" [KAFKA CONSUMER] Novo Evento de Carrinho Recebido! (Session: {session_id})")
        print(f" Cliente: {user_id} | Valor do Carrinho: R$ {cart_value:.2f}")
        print(f"==========================================================================")

        # ----------------------------------------------------------------------
        # GATILHO 1: Cart + 5 Minutos sem conversão
        # ----------------------------------------------------------------------
        trigger_1_response = self.execute_trigger_1_5min(session_event)

        # ----------------------------------------------------------------------
        # GATILHO 2: Cart + 1 Hora sem conversão
        # ----------------------------------------------------------------------
        trigger_2_response = self.execute_trigger_2_1hour(session_event)

        return {
            "session_id": session_id,
            "user_id": user_id,
            "trigger_5min": trigger_1_response,
            "trigger_1hour": trigger_2_response
        }

    def execute_trigger_1_5min(self, event):
        """
        Gatilho 1: 5 minutos após evento tipo 'cart' sem conversão.
        Envio de mensagem/push de engajamento suave (sem erosão de margem).
        """
        message = "Realize sua compra! Olha o seu produto aqui te esperando!"
        push_notification = {
            "trigger": "CART_PLUS_5_MINUTES",
            "time_window": "5 minutos após cart",
            "action_type": "PUSH_REMINDER",
            "message_title": "🛒 Seu carrinho está te esperando na Shopee!",
            "message_body": f"Olá! Notei que você deixou produtos incríveis no carrinho. {message}",
            "status": "DISPARADO"
        }
        print("\n⏱️ [GATILHO 1 - Cart + 5 Minutos] Disparado com Sucesso!")
        print(f"   Mensagem Enviada ao Cliente: '{push_notification['message_body']}'")
        return push_notification

    def execute_trigger_2_1hour(self, event):
        """
        Gatilho 2: 1 hora após evento tipo 'cart' sem conversão.
        Inferência de ML (Modelo Excel) -> Classifica o Perfil de Cliente -> Prescreve Cupom.
        """
        # Monta vetor de características (Features)
        num_items = event.get("num_cart_items", 1)
        num_views = event.get("num_views_before_cart", 2)
        ratio = round(num_views / max(num_items, 1), 2)
        dur = event.get("session_duration_sec", 120)
        hour = event.get("hour_of_day", 14)
        is_night = 1 if (hour < 6 or hour >= 22) else 0
        cart_value = event.get("total_cart_value", 200.0)

        df_feat = pd.DataFrame([{
            "total_cart_value": cart_value,
            "num_cart_items": num_items,
            "num_views_before_cart": num_views,
            "view_to_cart_ratio": ratio,
            "session_duration_sec": dur,
            "hour_of_day": hour,
            "is_night": is_night
        }])

        # Predict ML (Modelo Abandono + Modelo Perfil)
        if self.clf_abandonment:
            p_abandon = float(self.clf_abandonment.predict_proba(df_feat)[:, 1][0])
        else:
            # Fallback heurístico se modelo ainda não compilado
            p_abandon = 0.68

        if self.clf_profile:
            predicted_profile = str(self.clf_profile.predict(df_feat)[0])
        else:
            if num_views <= 3:
                predicted_profile = "high_intent"
            elif num_views >= 6 or is_night == 1:
                predicted_profile = "bargain_hunter"
            else:
                predicted_profile = "browser"

        # Matriz Prescritiva por Perfil de Cliente (1, 2 ou 3)
        prescription = self._prescribe_coupon_by_profile(predicted_profile, cart_value, p_abandon)

        result = {
            "trigger": "CART_PLUS_1_HOUR",
            "time_window": "1 hora após cart",
            "ml_predicted_profile": predicted_profile,
            "profile_name_pt": prescription["profile_name_pt"],
            "ml_abandonment_risk_pct": round(p_abandon * 100, 1),
            "assigned_coupon": prescription["coupon_code"],
            "coupon_label": prescription["coupon_label"],
            "action_rationale": prescription["rationale"],
            "status": "DISPARADO_COM_ML"
        }

        print("\n⏰ [GATILHO 2 - Cart + 1 Hora] Inferência ML & Regra de Perfil Executada!")
        print(f"   Perfil Identificado pelo ML: {result['profile_name_pt']} ({result['ml_predicted_profile']})")
        print(f"   Score de Abandono (ML): {result['ml_abandonment_risk_pct']}%")
        print(f"   Cupom / Benefício Prescrito: {result['coupon_label']}")
        print(f"   Justificativa de Negócio: {result['action_rationale']}")

        return result

    def _prescribe_coupon_by_profile(self, profile, cart_value, p_abandon):
        """
        Regra Prescritiva baseada nos 3 Perfis de Clientes:
        1. Comprador de Alta Intenção (high_intent)
        2. Caçador de Descontos (bargain_hunter)
        3. Navegador Indeciso (browser)
        """
        if profile == "high_intent":
            return {
                "profile_name_pt": "1. Comprador de Alta Intenção",
                "coupon_code": "FRETE_GRATIS" if cart_value >= 300 else "LEMBRETE_SEM_DESCONTO",
                "coupon_label": "Frete Grátis Shopee" if cart_value >= 300 else "Apenas Lembrete (Sem Cupom)",
                "rationale": "Cliente com alta intenção orgânica. Evita dar desconto agressivo para proteger margem financeira."
            }
        elif profile == "bargain_hunter":
            if cart_value >= 400:
                code, label = "DESC15_VIP", "Cupom 15% VIP Recuperação"
            else:
                code, label = "DESC10_FRETE", "Cupom 10% OFF + Frete Grátis"
            return {
                "profile_name_pt": "2. Caçador de Descontos",
                "coupon_code": code,
                "coupon_label": label,
                "rationale": "Cliente altamente sensível a preço/ofertas. Cupom de alto valor destrava a tomada de decisão."
            }
        else: # browser
            return {
                "profile_name_pt": "3. Navegador Indeciso",
                "coupon_code": "DESC5_FRETE",
                "coupon_label": "Cupom 5% OFF + Frete Grátis",
                "rationale": "Cliente navega por indecisão. Combo leve de 5% + Frete Grátis elimina a barreira do checkout."
            }


if __name__ == "__main__":
    simulator = KafkaTriggerSimulator()

    # Exemplo de teste com cliente Caçador de Descontos
    sample_event = {
        "user_id": 386070015,
        "user_session": "49d03116-3c95-4e13-8b9c-e3be97551fe8",
        "total_cart_value": 197.52,
        "num_cart_items": 1,
        "num_views_before_cart": 4,
        "session_duration_sec": 153,
        "hour_of_day": 5
    }

    res = simulator.process_cart_event(sample_event)
