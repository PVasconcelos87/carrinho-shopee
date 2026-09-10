"""
Modulo: data_loader.py
Descrição: Carregador do dataset real do Kaggle localizado na pasta /basededados/
(2019-Oct.csv, 2019-Nov.csv, etc).
"""

import os
import glob
import pandas as pd

BASE_DADOS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "basededados"
)

def get_base_dados_files():
    """
    Lista todos os arquivos CSV disponíveis no diretório /basededados.
    """
    if not os.path.exists(BASE_DADOS_DIR):
        return []
    csv_files = sorted(glob.glob(os.path.join(BASE_DADOS_DIR, "*.csv")))
    return csv_files


def load_basededados_dataset(sample_n=200000, file_pattern=None):
    """
    Carrega os registros de eventos brutos a partir dos arquivos CSV na pasta /basededados.
    
    Parâmetros:
        sample_n (int, opcional): Número de linhas para amostragem (padrão: 200.000). 
                                  Se None, lê o(s) arquivo(s) por completo.
        file_pattern (str, opcional): Nome do arquivo específico (ex: "2019-Oct.csv").
        
    Retorna:
        pd.DataFrame: DataFrame contendo os eventos de e-commerce brutos.
    """
    csv_files = get_base_dados_files()
    
    if not csv_files:
        raise FileNotFoundError(f"Nenhum arquivo .csv encontrado no diretório: {BASE_DADOS_DIR}")
        
    if file_pattern:
        target_files = [f for f in csv_files if file_pattern in f]
        if target_files:
            csv_files = target_files

    print(f"Encontrados {len(csv_files)} arquivo(s) de dados em: {BASE_DADOS_DIR}")
    for f in csv_files:
        size_gb = os.path.getsize(f) / (1024 ** 3)
        print(f" -> {os.path.basename(f)} ({size_gb:.2f} GB)")
        
    # Leitura otimizada por chunks ou nrows
    df_list = []
    rows_per_file = sample_n // len(csv_files) if (sample_n and len(csv_files) > 0) else sample_n
    
    for f in csv_files:
        print(f"Lendo registros de {os.path.basename(f)}...")
        if rows_per_file:
            df_chunk = pd.read_csv(f, nrows=rows_per_file)
        else:
            df_chunk = pd.read_csv(f)
        df_list.append(df_chunk)
        
    df_all = pd.concat(df_list, ignore_index=True)
    print(f" -> Total de eventos carregados de /basededados: {len(df_all):,}")
    return df_all


if __name__ == "__main__":
    df = load_basededados_dataset(sample_n=50000)
    print("\nInformações do Dataset Carregado:")
    print(df.info())
    print("\nDistribuição dos Tipos de Eventos:")
    print(df["event_type"].value_counts())
