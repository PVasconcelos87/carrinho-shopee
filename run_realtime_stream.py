#!/usr/bin/env python3
"""
Atalho raiz para executar o Pipeline Integrado de Streaming em Tempo Real
Kafka -> Amazon S3 (Bronze, Silver, Gold) -> PostgreSQL -> Web Dashboard & Streamlit
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from app.run_realtime_stream_pipeline import main

if __name__ == "__main__":
    main()
