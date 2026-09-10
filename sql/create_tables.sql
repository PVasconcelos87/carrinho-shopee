-- ============================================================================
-- PROJETO HANDS-ON ENGENHARIA DE DADOS - MACKENZIE
-- Schema Relacional da Camada Serving (PostgreSQL)
-- Database: ecommerce_db
-- ============================================================================

-- 1. Dimensão Usuários
CREATE TABLE IF NOT EXISTS dim_users (
    user_id BIGINT PRIMARY KEY,
    first_interaction TIMESTAMP,
    user_intent_profile VARCHAR(30),
    total_sessions INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Dimensão Produtos
CREATE TABLE IF NOT EXISTS dim_products (
    product_id BIGINT PRIMARY KEY,
    category_id BIGINT,
    category_code VARCHAR(150),
    main_category VARCHAR(50),
    brand VARCHAR(80),
    price NUMERIC(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabela Fato de Eventos Consolidados (Silver)
CREATE TABLE IF NOT EXISTS fact_events (
    event_id SERIAL PRIMARY KEY,
    event_time TIMESTAMP NOT NULL,
    event_type VARCHAR(20) NOT NULL,
    product_id BIGINT REFERENCES dim_products(product_id),
    user_id BIGINT,
    user_session VARCHAR(64) NOT NULL,
    price NUMERIC(10, 2),
    hour_of_day INT,
    is_night INT
);

-- 4. WIDE TABLE GOLD: session_features (Alimentação do Modelo de ML)
CREATE TABLE IF NOT EXISTS session_features (
    session_id VARCHAR(64) PRIMARY KEY,
    user_id BIGINT,
    total_cart_value NUMERIC(12, 2),
    num_cart_items INT,
    num_views_before_cart INT,
    view_to_cart_ratio NUMERIC(8, 2),
    session_duration_sec NUMERIC(10, 2),
    hour_of_day INT,
    day_of_week INT,
    is_weekend INT,
    is_night INT,
    main_category VARCHAR(50),
    -- Variáveis Comportamentais Enriquecidas da Jornada do Comprador
    user_prior_views INT DEFAULT 0,
    user_prior_carts INT DEFAULT 0,
    user_prior_abandoned_carts INT DEFAULT 0,
    user_total_cumulative_views INT DEFAULT 0,
    user_lifetime_hours NUMERIC(10, 2) DEFAULT 0.0,
    user_prior_abandon_rate NUMERIC(5, 4) DEFAULT 0.5,
    is_abandoned INT NOT NULL, -- Target (1 = Abandono, 0 = Compra)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Tabela de Prescrições e Cupons de Retenção (Gatilho 2)
CREATE TABLE IF NOT EXISTS cart_coupons_prescribed (
    prescription_id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) REFERENCES session_features(session_id),
    user_id BIGINT,
    total_cart_value NUMERIC(12, 2),
    p_abandonment NUMERIC(6, 4),
    urgency_level VARCHAR(20),
    coupon_code VARCHAR(30),
    coupon_label VARCHAR(100),
    discount_pct NUMERIC(5, 2),
    estimated_recovered_gmv NUMERIC(12, 2),
    trigger_executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para otimização analítica
CREATE INDEX IF NOT EXISTS idx_events_session ON fact_events(user_session);
CREATE INDEX IF NOT EXISTS idx_events_user ON fact_events(user_id);
CREATE INDEX IF NOT EXISTS idx_features_user ON session_features(user_id);
CREATE INDEX IF NOT EXISTS idx_features_target ON session_features(is_abandoned);
