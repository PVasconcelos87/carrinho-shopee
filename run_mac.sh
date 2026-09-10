#!/usr/bin/env bash
# ============================================================================
# PROJETO HANDS-ON ENGENHARIA DE DADOS - MACKENZIE
# Script de Execução e Automação para macOS (MacBook M1/M2/M3/M4 e Intel)
# ============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================================="
echo "    🛒 SHOPEE DATA PLATFORM — ABANDONO DE CARRINHO & MACHINE LEARNING"
echo "    MBA em Engenharia de Dados | Ambiente macOS (MacBook)"
echo "=========================================================================="

# 1. Checa Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Erro: Python 3 não encontrado no seu Mac. Instale via brew ou python.org."
    exit 1
fi

# 2. Configura Virtualenv Local no Mac se não existir
if [ ! -d ".venv" ]; then
    echo "📦 Criando ambiente virtual Python (.venv) para isolar os pacotes no Mac..."
    python3 -m venv .venv
fi

echo "✓ Ativando ambiente virtual (.venv)..."
source .venv/bin/activate

# 3. Menu de Opções Didático para o Estudante
echo ""
echo "Escolha a ação que deseja executar no seu Mac:"
echo "--------------------------------------------------------------------------"
echo "  [1] Instalar dependências Python (requirements.txt)"
echo "  [2] Subir infraestrutura Docker (Kafka, Spark, Postgres, pgAdmin, Web)"
echo "  [3] Executar Pipeline Completo de ML & Jornada do Comprador"
echo "  [4] Abrir Simulador Web & Gatilhos no navegador (Porta 8000)"
echo "  [5] Iniciar Dashboard Analítico Streamlit (Porta 8501)"
echo "  [6] Ingestão Batch para o Amazon S3 Bronze (AWS Academy)"
echo "  [7] Executar Processamento PySpark Medallion (Bronze -> Silver -> Gold)"
echo "  [8] Parar containers Docker (docker compose down)"
echo "  [0] Sair"
echo "--------------------------------------------------------------------------"
read -p "Digite a opção desejada [1-8]: " OPTION

case $OPTION in
    1)
        echo "\n📦 Instalando / atualizando dependências Python..."
        pip install --upgrade pip
        pip install -r requirements.txt
        echo "\n✓ Todas as dependências foram instaladas com sucesso no seu Mac!"
        ;;

    2)
        echo "\n🐳 Verificando o Docker Desktop no seu Mac..."
        if ! docker info >/dev/null 2>&1; then
            echo "❌ Atenção: O aplicativo Docker Desktop não está em execução."
            echo "👉 Abra o Docker Desktop na pasta Aplicativos do seu Mac e tente novamente."
            exit 1
        fi
        echo "Subindo containers com emulação otimizada para Mac (Apple Silicon & Intel)..."
        docker compose up -d
        echo ""
        docker compose ps
        echo "\n✓ Infraestrutura pronta!"
        echo "  • Web Dashboard & Simulador: http://localhost:8000"
        echo "  • Spark Master Web UI:       http://localhost:8080"
        echo "  • pgAdmin 4:                 http://localhost:5050 (Login: admin@mackenzie.br | admin)"
        echo "  • PostgreSQL:                localhost:5432 (ecommerce_db)"
        echo "  • Kafka Broker:              localhost:9092"
        ;;

    3)
        echo "\n🧠 Executando Pipeline de Machine Learning & Avaliação de Jornada..."
        python3 run_pipeline.py
        echo "\n✓ Atualizando os números no dashboard..."
        python3 update_dashboard_stats.py
        ;;

    4)
        echo "\n🌐 Abrindo o Simulador Web & Gatilhos Temporais no Safari/Chrome..."
        if docker ps | grep -q ecommerce-web-dashboard; then
            open "http://localhost:8000"
        else
            echo "Iniciando servidor web nativo rápido na porta 8000..."
            open "http://localhost:8000"
            python3 -m http.server 8000
        fi
        ;;

    5)
        echo "\n📊 Iniciando Dashboard Analítico Streamlit..."
        echo "Pressione Ctrl+C para encerrar o Streamlit."
        streamlit run dashboard/app_streamlit.py
        ;;

    6)
        read -p "Digite o nome do seu Bucket S3 no AWS Academy (ex: ecommerce-data-platform-mack-lab-paulo): " BUCKET
        read -p "Digite o caminho do arquivo CSV (pressione Enter para '2019-Nov.csv'): " CSV_FILE
        CSV_FILE=${CSV_FILE:-"2019-Nov.csv"}
        python3 app/batch_ingestion.py "$BUCKET" "$CSV_FILE"
        ;;

    7)
        read -p "Digite o nome do seu Bucket S3 no AWS Academy (ex: ecommerce-data-platform-mack-lab-paulo): " BUCKET
        python3 app/ecommerce_spark_processor.py "$BUCKET"
        ;;

    8)
        echo "\n🛑 Parando todos os containers Docker..."
        docker compose down
        echo "✓ Containers finalizados com sucesso!"
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
