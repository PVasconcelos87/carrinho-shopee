"""
Script: export_data_js.py
Descrição: Converte real_ml_stats.json para data.js (window.REAL_ML_STATS = {...}),
garantindo suporte nativo a abertura de index.html por duplo-clique no protocolo file:// sem erros de CORS do browser.
"""

import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, "real_ml_stats.json")
JS_FILE = os.path.join(BASE_DIR, "data.js")

def convert_json_to_js():
    if not os.path.exists(JSON_FILE):
        print(f"Erro: {JSON_FILE} não existe!")
        return

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data_str = f.read()

    js_content = f"// Dataset Integrado Real para execução offline/file:// sem restrições de CORS\nwindow.REAL_ML_STATS = {data_str};\n"

    with open(JS_FILE, "w", encoding="utf-8") as f:
        f.write(js_content)

    print(f"✓ Sucesso! {JS_FILE} criado/atualizado com ({os.path.getsize(JS_FILE) / 1024:.1f} KB). Funciona 100% via file:// e http://!")

if __name__ == "__main__":
    convert_json_to_js()
