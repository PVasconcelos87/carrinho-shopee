#!/usr/bin/env bash
# ============================================================================
# PROJETO HANDS-ON ENGENHARIA DE DADOS - MACKENZIE
# Script de Execução e Automação para AWS EC2 (Ubuntu Linux)
# ============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# 1. Detectar IP Público da instância EC2
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 60" 2>/dev/null || true)
if [ -n "$TOKEN" ]; then
    PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)
fi

if [ -z "$PUBLIC_IP" ]; then
    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || curl -s ifconfig.me 2>/dev/null || echo "SEU-IP-EC2")
fi

echo "=========================================================================="
echo "    🛒 SHOPEE DATA PLATFORM — ABANDONO DE CARRINHO & MACHINE LEARNING"
echo "    MBA em Engenharia de Dados | Ambiente AWS EC2 (Ubuntu)"
echo "    Instância EC2 IP Público: $PUBLIC_IP"
echo "=========================================================================="

# 2. Comando Docker Compose (detecta se é 'docker compose' ou 'docker-compose')
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    DOCKER_COMPOSE_CMD=""
fi

# 3. Menu de Opções
echo ""
echo "Escolha a ação que deseja executar na sua EC2:"
echo "--------------------------------------------------------------------------"
echo "  [1] Configurar ambiente inicial (Docker, Docker Compose e Python)"
echo "  [2] Subir infraestrutura completa (Kafka, Spark, Postgres, pgAdmin, Web)"
echo "  [3] Executar Pipeline Completo de ML & Jornada do Comprador"
echo "  [4] Iniciar Dashboard Analítico Streamlit (Porta 8501 - Acesso Remoto)"
echo "  [5] Ingestão Batch para o Amazon S3 Bronze (AWS Academy)"
echo "  [6] Processamento PySpark Medallion no S3 (Bronze -> Silver -> Gold)"
echo "  [7] Ver status e logs dos containers Docker"
echo "  [8] Parar containers Docker ($DOCKER_COMPOSE_CMD down)"
echo "  [9] Atualizar código do repositório Git (git pull)"
echo "  [0] Sair"
echo "--------------------------------------------------------------------------"
read -p "Digite a opção desejada [1-9]: " OPTION

case $OPTION in
    1)
        echo -e "\n📦 Instalando Docker, Docker Compose e ferramentas Python no Ubuntu..."
        sudo apt update
        sudo apt install -y docker.io docker-compose git python3-pip python3-venv
        sudo systemctl enable --now docker
        sudo groupadd -f docker
        sudo usermod -aG docker $USER
        
        if [ ! -d ".venv" ]; then
            echo "📦 Criando ambiente virtual Python (.venv)..."
            python3 -m venv .venv
        fi
        source .venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        echo -e "\n✓ Ambiente configurado com sucesso!"
        echo "💡 Dica: Se o Docker der erro de permissão sem sudo, execute: newgrp docker"
        ;;

    2)
        echo -e "\n🐳 Iniciando containers com Docker Compose..."
        if [ -z "$DOCKER_COMPOSE_CMD" ]; then
            sudo apt install -y docker-compose
            DOCKER_COMPOSE_CMD="docker-compose"
        fi
        
        # Garante que o serviço docker esteja rodando
        sudo systemctl start docker 2>/dev/null || true
        
        $DOCKER_COMPOSE_CMD up -d
        echo ""
        $DOCKER_COMPOSE_CMD ps
        echo -e "\n✓ Infraestrutura pronta e acessível externamente via navegador:"
        echo "  • Web Dashboard & Simulador: http://${PUBLIC_IP}:8000"
        echo "  • Spark Master Web UI:       http://${PUBLIC_IP}:8080"
        echo "  • pgAdmin 4:                 http://${PUBLIC_IP}:5050 (Login: admin@mackenzie.br | admin)"
        echo "  • PostgreSQL:                ${PUBLIC_IP}:5432 (ecommerce_db)"
        echo "  • Kafka Broker:              ${PUBLIC_IP}:9092"
        echo ""
        echo "⚠️ Lembre-se: No Security Group da EC2 na AWS, libere as portas 8000, 8501, 8080, 5050 se quiser acessar do seu MacBook."
        ;;

    3)
        echo -e "\n🧠 Executando Pipeline de Machine Learning na EC2..."
        if [ -f ".venv/bin/activate" ]; then
            source .venv/bin/activate
        fi
        python3 run_pipeline.py
        echo -e "\n✓ Atualizando estatísticas reais para o dashboard..."
        python3 update_dashboard_stats.py
        ;;

    4)
        echo -e "\n📊 Iniciando Streamlit na EC2 para acesso público..."
        echo "Acesse pelo seu navegador: http://${PUBLIC_IP}:8501"
        echo "Pressione Ctrl+C para encerrar."
        if [ -f ".venv/bin/activate" ]; then
            source .venv/bin/activate
        fi
        streamlit run dashboard/app_streamlit.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
        ;;

    5)
        read -p "Digite o nome do seu Bucket S3 no AWS Academy (ex: ecommerce-data-platform-mack-lab-paulo): " BUCKET
        read -p "Digite o caminho do arquivo CSV (pressione Enter para '2019-Nov.csv'): " CSV_FILE
        CSV_FILE=${CSV_FILE:-"2019-Nov.csv"}
        if [ -f ".venv/bin/activate" ]; then
            source .venv/bin/activate
        fi
        python3 app/batch_ingestion.py "$BUCKET" "$CSV_FILE"
        ;;

    6)
        read -p "Digite o nome do seu Bucket S3 no AWS Academy (ex: ecommerce-data-platform-mack-lab-paulo): " BUCKET
        if [ -f ".venv/bin/activate" ]; then
            source .venv/bin/activate
        fi
        python3 app/ecommerce_spark_processor.py "$BUCKET"
        ;;

    7)
        echo -e "\n📋 Status dos containers Docker:"
        $DOCKER_COMPOSE_CMD ps
        echo -e "\nÚltimos logs:"
        $DOCKER_COMPOSE_CMD logs --tail=20
        ;;

    8)
        echo -e "\n🛑 Parando todos os containers Docker..."
        $DOCKER_COMPOSE_CMD down
        echo "✓ Containers finalizados com sucesso!"
        ;;

    9)
        echo -e "\n🔄 Atualizando código do repositório Git..."
        git pull origin main || git pull
        echo "✓ Repositório atualizado!"
        ;;

    0)
        echo "Saindo..."
        exit 0
        ;;

    *)
        echo "Opção inválida."
        exit 1
        ;;
esac
