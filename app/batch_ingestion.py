"""
Script: batch_ingestion.py
Descrição: Ingestão em lote (Batch Layer) do arquivo histórico de eventos para a Camada Bronze no Amazon S3.
Compatível com o ambiente AWS Academy Learner Lab (suporte a Session Token).
"""

import os
import sys
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Configurações do S3 e Dataset
DEFAULT_BUCKET = os.getenv("S3_BUCKET_NAME", "ecommerce-data-platform-mack-lab")
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
LOCAL_FILE = os.getenv("LOCAL_DATA_FILE", "2019-Nov.csv")
S3_KEY = "bronze/ecommerce_events/year=2019/month=11/2019-Nov.csv"


def get_s3_client():
    """
    Inicializa o cliente S3 com suporte automático às credenciais do AWS Academy
    (Access Key, Secret Key e Session Token ou IAM LabRole na EC2).
    """
    try:
        session = boto3.Session(region_name=REGION)
        s3 = session.client("s3")
        return s3
    except Exception as e:
        print(f"Erro ao inicializar sessão AWS: {e}")
        sys.exit(1)


def ensure_bucket_exists(s3, bucket_name):
    """Verifica se o bucket existe; se não existir, tenta criar."""
    try:
        s3.head_bucket(Bucket=bucket_name)
        print(f"✓ Bucket '{bucket_name}' encontrado e acessível.")
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "404":
            print(f"Bucket '{bucket_name}' não existe. Criando na região {REGION}...")
            if REGION == "us-east-1":
                s3.create_bucket(Bucket=bucket_name)
            else:
                s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": REGION}
                )
            print(f"✓ Bucket '{bucket_name}' criado com sucesso!")
        elif error_code == "403":
            print(f"Erro de Acesso (403): O bucket '{bucket_name}' já existe em outra conta ou faltam permissões.")
            sys.exit(1)
        else:
            print(f"Erro ao verificar bucket: {e}")
            sys.exit(1)


class ProgressPercentage:
    """Callback para exibir o progresso do upload no terminal."""
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0

    def __call__(self, bytes_amount):
        self._seen_so_far += bytes_amount
        percentage = (self._seen_so_far / self._size) * 100
        mb_seen = self._seen_so_far / (1024 * 1024)
        mb_total = self._size / (1024 * 1024)
        sys.stdout.write(f"\rProgresso do Upload: {percentage:.1f}% ({mb_seen:.1f} MB / {mb_total:.1f} MB)")
        sys.stdout.flush()


def upload_bronze(local_path, bucket_name, s3_target_key):
    s3 = get_s3_client()
    ensure_bucket_exists(s3, bucket_name)

    if not os.path.exists(local_path):
        print(f"Aviso: Arquivo '{local_path}' não encontrado localmente.")
        print("Dica: Baixe o dataset '2019-Nov.csv' ou gere uma amostra de teste.")
        return False

    print(f"\nIniciando upload de '{local_path}' para s3://{bucket_name}/{s3_target_key}...")
    try:
        s3.upload_file(
            Filename=local_path,
            Bucket=bucket_name,
            Key=s3_target_key,
            Callback=ProgressPercentage(local_path)
        )
        print(f"\n✓ Upload concluído com sucesso na Camada Bronze!")
        print(f"URI no S3: s3://{bucket_name}/{s3_target_key}")
        return True
    except NoCredentialsError:
        print("\nErro: Credenciais da AWS não encontradas. Configure o AWS CLI ou AWS_SESSION_TOKEN.")
        return False
    except Exception as e:
        print(f"\nErro durante o upload: {e}")
        return False


if __name__ == "__main__":
    bucket = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BUCKET
    file_path = sys.argv[2] if len(sys.argv) > 2 else LOCAL_FILE
    upload_bronze(file_path, bucket, S3_KEY)
