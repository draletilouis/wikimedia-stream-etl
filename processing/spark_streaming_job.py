from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, from_unixtime
from pyspark.sql.types import StructType, StringType, LongType
import os
import sys
import logging
from pathlib import Path

# Add parent directory to path to import common modules
sys.path.insert(0, str(Path(__file__).parent.parent))
from common.config_loader import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load configuration
config = load_config()
logger.info("Configuration loaded successfully")

# Extract configuration values
APP_NAME = config.get('spark.app_name', 'WikiStreamProcessor')
KAFKA_BOOTSTRAP_SERVERS = config.get('spark.kafka.bootstrap_servers')
KAFKA_TOPIC = config.get('spark.kafka.subscribe')
STARTING_OFFSETS = config.get('spark.kafka.starting_offsets', 'latest')

# Database configuration
POSTGRES_HOST = config.get('postgres.host')
POSTGRES_PORT = config.get('postgres.port', 5432)
POSTGRES_DB = config.get('postgres.database')
POSTGRES_USER = config.get('postgres.user')
POSTGRES_PASSWORD = config.get('postgres.password')
POSTGRES_URL = f'jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'

# Windowing configuration
WINDOW_DURATION = config.get('spark.windowing.duration', '1 minute')
WATERMARK_DURATION = config.get('spark.windowing.watermark', '2 minutes')

# Trigger configuration
TRIGGER_INTERVAL = config.get('spark.trigger.processing_time', '30 seconds')

# Checkpoint location
CHECKPOINT_LOCATION = config.get('spark.checkpoint.location', '/tmp/spark_checkpoint')

# Spark packages
JAR_PACKAGES = ','.join(config.get('spark.jars.packages', []))

# Log level
LOG_LEVEL = config.get('spark.log_level', 'WARN')

logger.info(f"Spark Configuration:")
logger.info(f"  App Name: {APP_NAME}")
logger.info(f"  Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
logger.info(f"  Topic: {KAFKA_TOPIC}")
logger.info(f"  PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
logger.info(f"  Window: {WINDOW_DURATION}, Watermark: {WATERMARK_DURATION}")
logger.info(f"  Trigger: {TRIGGER_INTERVAL}")

# Create Spark session with Kafka and PostgreSQL integration
spark = SparkSession.builder \
    .appName(APP_NAME) \
    .config("spark.jars.packages", JAR_PACKAGES) \
    .getOrCreate()

spark.sparkContext.setLogLevel(LOG_LEVEL)

# Define schema for the incoming JSON
schema = StructType() \
    .add("id", StringType()) \
    .add("title", StringType()) \
    .add("user", StringType()) \
    .add("type", StringType()) \
    .add("namespace", LongType()) \
    .add("timestamp", LongType())

#Read the Kafka stream
logger.info("Starting Kafka stream reader...")
df_raw = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", KAFKA_TOPIC) \
    .option("startingOffsets", STARTING_OFFSETS) \
    .load()

# Kafka sends keys/values as bytes, so we must decode them
df_parsed = df_raw.selectExpr("CAST(value AS STRING) as json")

#Parse JSON into structured columns
df = df_parsed.select(from_json(col("json"), schema).alias("data")).select("data.*")

# Convert timestamp from Unix seconds to timestamp type
# Wikipedia timestamps are in seconds, so we use from_unixtime
df = df.withColumn("timestamp", from_unixtime(col("timestamp")).cast("timestamp"))

# Aggregate: count number of edits per user in configurable windows
logger.info(f"Setting up aggregations with window={WINDOW_DURATION}, watermark={WATERMARK_DURATION}")
df_count = df \
    .withWatermark("timestamp", WATERMARK_DURATION) \
    .groupBy(
        window(col("timestamp"), WINDOW_DURATION),
        col("user")
    ) \
    .count()

# Function to write each micro-batch to PostgreSQL
def write_to_postgres(batch_df, batch_id):
    """
    Write each micro-batch to PostgreSQL.
    This function is called for each streaming batch.
    """
    if batch_df.count() > 0:
        # Rename columns to match PostgreSQL table schema
        batch_df = batch_df.select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("user").alias("user_name"),
            col("count").alias("edit_count")
        )

        # Write to PostgreSQL
        batch_df.write \
            .format("jdbc") \
            .option("url", POSTGRES_URL) \
            .option("dbtable", "user_edit_counts") \
            .option("user", POSTGRES_USER) \
            .option("password", POSTGRES_PASSWORD) \
            .option("driver", "org.postgresql.Driver") \
            .mode("append") \
            .save()

        logger.info(f"Batch {batch_id}: Wrote {batch_df.count()} rows to PostgreSQL")

# Write the processed stream to PostgreSQL using foreachBatch
logger.info(f"Starting streaming query with trigger interval: {TRIGGER_INTERVAL}")
logger.info(f"Checkpoint location: {CHECKPOINT_LOCATION}")

query = df_count.writeStream \
    .outputMode("update") \
    .foreachBatch(write_to_postgres) \
    .option("checkpointLocation", CHECKPOINT_LOCATION) \
    .trigger(processingTime=TRIGGER_INTERVAL) \
    .start()

logger.info("Streaming query started. Waiting for termination...")
query.awaitTermination()
