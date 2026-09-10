"""
Script: ecommerce_spark_processor.py
Descrição: Processamento distribuído com PySpark no Amazon S3 (Medallion Architecture: Bronze -> Silver -> Gold).
Gera os dados higienizados em Parquet (Silver) e a Wide Table de features (Gold: session_features).
"""

import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, LongType, TimestampType, IntegerType
)
from pyspark.sql.window import Window


def create_spark_session():
    """
    Inicializa a SparkSession configurada com os conectores S3A para a AWS.
def create_spark_session(is_local=False):
    """
    Inicializa a SparkSession configurada para execução no Mac (local) ou na AWS (S3A).
    """
    builder = SparkSession.builder.appName("ShopeeEcommerceProcessor-Medallion")
    
    if not is_local:
        builder = builder \
            .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262") \
            .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
            .config("spark.hadoop.fs.s3a.endpoint", "s3.amazonaws.com")
            
    builder = builder \
        .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
        .config("spark.driver.memory", "2g")
        
    spark = builder.getOrCreate()

    if not is_local:
        sc = spark.sparkContext
        conf = sc._jsc.hadoopConfiguration()
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_session_token = os.getenv("AWS_SESSION_TOKEN")

        if aws_access_key and aws_secret_key:
            conf.set("fs.s3a.access.key", aws_access_key)
            conf.set("fs.s3a.secret.key", aws_secret_key)
            if aws_session_token:
                conf.set("fs.s3a.session.token", aws_session_token)
                conf.set("fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.TemporaryAWSCredentialsProvider")
        else:
            conf.set("fs.s3a.aws.credentials.provider", "com.amazonaws.auth.InstanceProfileCredentialsProvider")

    spark.sparkContext.setLogLevel("WARN")
    return spark


def process_bronze_to_silver(spark, target_location, is_local=False):
    """
    ETL Camada Bronze -> Camada Silver
    """
    if is_local:
        bronze_path = os.path.join(target_location, "bronze", "2019-Nov.csv")
        silver_path = os.path.join(target_location, "silver", "ecommerce_events")
    else:
        bronze_path = f"s3a://{target_location}/bronze/ecommerce_events/year=2019/month=11/2019-Nov.csv"
        silver_path = f"s3a://{target_location}/silver/ecommerce_events/year=2019/month=11/"

    print(f"\n[1/2] Lendo dados da Camada Bronze: {bronze_path}...")

    schema = StructType([
        StructField("event_time", StringType(), True),
        StructField("event_type", StringType(), True),
        StructField("product_id", LongType(), True),
        StructField("category_id", LongType(), True),
        StructField("category_code", StringType(), True),
        StructField("brand", StringType(), True),
        StructField("price", DoubleType(), True),
        StructField("user_id", LongType(), True),
        StructField("user_session", StringType(), True),
    ])

    df_raw = spark.read.option("header", "true").schema(schema).csv(bronze_path)

    print("Higienizando, tipando e validando eventos...")
    df_silver = df_raw \
        .withColumn("event_time_clean", F.substring(F.col("event_time"), 1, 19)) \
        .withColumn("event_time_ts", F.to_timestamp(F.col("event_time_clean"), "yyyy-MM-dd HH:mm:ss")) \
        .filter(F.col("event_time_ts").isNotNull()) \
        .filter(F.col("product_id").isNotNull() & F.col("user_id").isNotNull() & F.col("user_session").isNotNull()) \
        .filter(F.col("price") > 0.0) \
        .filter(F.col("event_type").isin("view", "cart", "purchase")) \
        .withColumn("category_code", F.coalesce(F.col("category_code"), F.lit("outros.desconhecido"))) \
        .withColumn("brand", F.coalesce(F.col("brand"), F.lit("generico"))) \
        .withColumn("hour_of_day", F.hour(F.col("event_time_ts"))) \
        .withColumn("is_night", F.when((F.col("hour_of_day") >= 22) | (F.col("hour_of_day") < 6), 1).otherwise(0)) \
        .dropDuplicates(["event_time", "event_type", "product_id", "user_id", "user_session"])

    print(f"Escrevendo Camada Silver em Parquet em: {silver_path}...")
    df_silver.write.mode("overwrite").parquet(silver_path)
    print("✓ Camada Silver gerada com sucesso em formato Parquet colunar otimizado!")
    return df_silver


def process_silver_to_gold(spark, target_location, is_local=False):
    """
    ETL Camada Silver -> Camada Gold (session_features Wide Table)
    """
    if is_local:
        silver_path = os.path.join(target_location, "silver", "ecommerce_events")
        gold_path = os.path.join(target_location, "gold", "session_features")
    else:
        silver_path = f"s3a://{target_location}/silver/ecommerce_events/year=2019/month=11/"
        gold_path = f"s3a://{target_location}/gold/session_features/"

    print(f"\n[2/2] Construindo Camada Gold (session_features) a partir de: {silver_path}...")
    df_silver = spark.read.parquet(silver_path)

    # Identifica sessões que possuem pelo menos 1 evento de carrinho
    cart_sessions = df_silver.filter(F.col("event_type") == "cart").select("user_session").distinct()
    df_cart_events = df_silver.join(cart_sessions, on="user_session", how="inner")

    # Agregação ao nível de sessão
    session_agg = df_cart_events.groupBy("user_session", "user_id").agg(
        F.sum(F.when(F.col("event_type") == "cart", F.col("price")).otherwise(0.0)).alias("total_cart_value"),
        F.count(F.when(F.col("event_type") == "cart", 1)).alias("num_cart_items"),
        F.count(F.when(F.col("event_type") == "view", 1)).alias("num_views_before_cart"),
        F.count(F.when(F.col("event_type") == "purchase", 1)).alias("num_purchases"),
        F.min("event_time_ts").alias("first_event_ts"),
        F.max(F.when(F.col("event_type") == "cart", F.col("event_time_ts"))).alias("last_cart_ts"),
        F.max("price").alias("max_item_price"),
        F.min(F.when(F.col("event_type") == "cart", F.col("price"))).alias("min_item_price"),
        F.avg(F.when(F.col("event_type") == "cart", F.col("price"))).alias("avg_item_price"),
        F.countDistinct(F.when(F.col("event_type") == "cart", F.col("brand"))).alias("num_distinct_brands"),
        F.first(F.when(F.col("event_type") == "cart", F.col("category_code"))).alias("main_category")
    )

    # Definição do Target e Ratios
    df_sessions = session_agg \
        .withColumn("is_abandoned", F.when(F.col("num_purchases") == 0, 1).otherwise(0)) \
        .withColumn("view_to_cart_ratio", F.round(F.col("num_views_before_cart") / F.greatest(F.col("num_cart_items"), F.lit(1)), 2)) \
        .withColumn("session_duration_sec", F.greatest(F.unix_timestamp("last_cart_ts") - F.unix_timestamp("first_event_ts"), F.lit(0))) \
        .withColumn("hour_of_day", F.hour("last_cart_ts")) \
        .withColumn("day_of_week", F.dayofweek("last_cart_ts")) \
        .withColumn("is_weekend", F.when(F.col("day_of_week").isin(1, 7), 1).otherwise(0)) \
        .withColumn("is_night", F.when((F.col("hour_of_day") >= 22) | (F.col("hour_of_day") < 6), 1).otherwise(0))

    # Janela temporal por comprador para features cumulativas (Zero-leakage)
    user_window = Window.partitionBy("user_id").orderBy("first_event_ts").rowsBetween(Window.unboundedPreceding, -1)

    df_gold = df_sessions \
        .withColumn("user_prior_views", F.coalesce(F.sum("num_views_before_cart").over(user_window), F.lit(0))) \
        .withColumn("user_prior_carts", F.coalesce(F.count("user_session").over(user_window), F.lit(0))) \
        .withColumn("user_prior_abandoned_carts", F.coalesce(F.sum("is_abandoned").over(user_window), F.lit(0))) \
        .withColumn("user_total_cumulative_views", F.col("user_prior_views") + F.col("num_views_before_cart"))

    print(f"Escrevendo Camada Gold (session_features) em: {gold_path}...")
    df_gold.write.mode("overwrite").parquet(gold_path)
    print("✓ Camada Gold (Wide Table session_features) gerada com sucesso!")
    return df_gold


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.getenv("S3_BUCKET_NAME", "local")
    is_local_mode = target in ["local", "--local", "data_lake"] or not target.startswith("s3") and "ecommerce-" not in target

    if is_local_mode:
        print("⚡ Modo Local ativado (Processamento no macOS / Sistema de Arquivos Local).")
        target_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data_lake")
        os.makedirs(os.path.join(target_dir, "silver"), exist_ok=True)
        os.makedirs(os.path.join(target_dir, "gold"), exist_ok=True)
        spark = create_spark_session(is_local=True)
        try:
            process_bronze_to_silver(spark, target_dir, is_local=True)
            process_silver_to_gold(spark, target_dir, is_local=True)
        finally:
            spark.stop()
    else:
        print(f"☁️ Modo AWS S3 ativado (Bucket: {target}).")
        spark = create_spark_session(is_local=False)
        try:
            process_bronze_to_silver(spark, target, is_local=False)
            process_silver_to_gold(spark, target, is_local=False)
        finally:
            spark.stop()
