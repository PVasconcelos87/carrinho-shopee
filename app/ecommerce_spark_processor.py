"""
Script: ecommerce_spark_processor.py
Otimizado para processamento em larga escala (67M linhas / 9 GB) na AWS.
Utiliza diretório dedicado para o Spark Shuffle evitando conflitos em /tmp.
"""

import os
import sys
import boto3
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, LongType
)
from pyspark.sql.window import Window

BASE_DIR = os.path.expanduser("~/data_lake_cache")
SPARK_TMP = os.path.expanduser("~/spark_shuffle_tmp")


def create_spark_session():
    os.makedirs(SPARK_TMP, exist_ok=True)
    builder = SparkSession.builder \
        .appName("ShopeeEcommerceProcessor-Medallion-Full") \
        .config("spark.local.dir", SPARK_TMP) \
        .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
        .config("spark.driver.memory", "4g") \
        .config("spark.executor.memory", "4g") \
        .config("spark.sql.shuffle.partitions", "24") \
        .config("spark.shuffle.compress", "true") \
        .config("spark.shuffle.spill.compress", "true") \
        .config("spark.io.compression.codec", "lz4")
        
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def upload_directory_to_s3(local_dir, bucket_name, s3_prefix):
    s3 = boto3.client("s3")
    print(f"Sincronizando Parquet para s3://{bucket_name}/{s3_prefix}...")
    uploaded = 0
    for root, _, files in os.walk(local_dir):
        for f in files:
            if f.endswith(".parquet") or f == "_SUCCESS":
                local_path = os.path.join(root, f)
                rel_path = os.path.relpath(local_path, local_dir)
                s3_key = f"{s3_prefix.rstrip('/')}/{rel_path}"
                s3.upload_file(local_path, bucket_name, s3_key)
                uploaded += 1
    print(f"✓ {uploaded} arquivos Parquet gravados no S3 ({s3_prefix})!")


def run_medallion_pipeline(spark, bucket_name):
    local_csv = "2019-Nov.csv"
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

    print("\n==========================================================================")
    print("  [1/2] LENDO DATASET COMPLETO (67M EVENTOS) E HIGIENIZANDO PARA SILVER")
    print("==========================================================================")
    df_raw = spark.read.option("header", "true").schema(schema).csv(local_csv)

    print("Processando e higienizando Camada Silver com PySpark...")
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
        .withColumn("is_night", F.when((F.col("hour_of_day") >= 22) | (F.col("hour_of_day") < 6), 1).otherwise(0))

    local_silver = os.path.join(BASE_DIR, "silver", "ecommerce_events")
    os.makedirs(local_silver, exist_ok=True)
    
    print("Gravando Camada Silver em formato Parquet colunar otimizado...")
    df_silver.write.mode("overwrite").parquet(local_silver)
    upload_directory_to_s3(local_silver, bucket_name, "silver/ecommerce_events/year=2019/month=11/")

    print("\n==========================================================================")
    print("  [2/2] PROCESSANDO CAMADA GOLD (SESSION_FEATURES E JORNADA DO COMPRADOR)")
    print("==========================================================================")
    df_silver_read = spark.read.parquet(local_silver)
    cart_sessions = df_silver_read.filter(F.col("event_type") == "cart").select("user_session").distinct()
    df_cart_events = df_silver_read.join(cart_sessions, on="user_session", how="inner")

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

    df_sessions = session_agg \
        .withColumn("is_abandoned", F.when(F.col("num_purchases") == 0, 1).otherwise(0)) \
        .withColumn("view_to_cart_ratio", F.round(F.col("num_views_before_cart") / F.greatest(F.col("num_cart_items"), F.lit(1)), 2)) \
        .withColumn("session_duration_sec", F.greatest(F.unix_timestamp("last_cart_ts") - F.unix_timestamp("first_event_ts"), F.lit(0))) \
        .withColumn("hour_of_day", F.hour("last_cart_ts")) \
        .withColumn("day_of_week", F.dayofweek("last_cart_ts")) \
        .withColumn("is_weekend", F.when(F.col("day_of_week").isin(1, 7), 1).otherwise(0)) \
        .withColumn("is_night", F.when((F.col("hour_of_day") >= 22) | (F.col("hour_of_day") < 6), 1).otherwise(0))

    user_window = Window.partitionBy("user_id").orderBy("first_event_ts").rowsBetween(Window.unboundedPreceding, -1)

    df_gold = df_sessions \
        .withColumn("user_prior_views", F.coalesce(F.sum("num_views_before_cart").over(user_window), F.lit(0))) \
        .withColumn("user_prior_carts", F.coalesce(F.count("user_session").over(user_window), F.lit(0))) \
        .withColumn("user_prior_abandoned_carts", F.coalesce(F.sum("is_abandoned").over(user_window), F.lit(0))) \
        .withColumn("user_total_cumulative_views", F.col("user_prior_views") + F.col("num_views_before_cart"))

    local_gold = os.path.join(BASE_DIR, "gold", "session_features")
    os.makedirs(local_gold, exist_ok=True)
    print("Gravando Camada Gold em Parquet...")
    df_gold.write.mode("overwrite").parquet(local_gold)
    upload_directory_to_s3(local_gold, bucket_name, "gold/session_features/")

    print("\n==========================================================================")
    print("  🏆 ARQUITETURA MEDALLION (67M EVENTOS) CONCLUÍDA COM SUCESSO NO S3!")
    print(f"  • Bronze: s3://{bucket_name}/bronze/ecommerce_events/year=2019/month=11/2019-Nov.csv")
    print(f"  • Silver: s3://{bucket_name}/silver/ecommerce_events/year=2019/month=11/")
    print(f"  • Gold:   s3://{bucket_name}/gold/session_features/")
    print("==========================================================================")


if __name__ == "__main__":
    bucket = sys.argv[1] if len(sys.argv) > 1 else "ecommerce-data-platform-mack-paulo"
    spark = create_spark_session()
    try:
        run_medallion_pipeline(spark, bucket)
    finally:
        spark.stop()
