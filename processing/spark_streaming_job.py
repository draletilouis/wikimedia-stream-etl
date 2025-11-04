from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window
from pyspark.sql.types import StructType, StringType, LongType

# Create Spark session with Kafka integration
spark = SparkSession.builder \
    .appName("WikiStreamProcessor") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Define schema for the incoming JSON
schema = StructType() \
    .add("id", StringType()) \
    .add("title", StringType()) \
    .add("user", StringType()) \
    .add("type", StringType()) \
    .add("namespace", LongType()) \
    .add("timestamp", LongType())

#Read the Kafka stream
df_raw = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "wiki_changes") \
    .option("startingOffsets", "latest") \
    .load()

# Kafka sends keys/values as bytes, so we must decode them
df_parsed = df_raw.selectExpr("CAST(value AS STRING) as json")

#Parse JSON into structured columns
df = df_parsed.select(from_json(col("json"), schema).alias("data")).select("data.*")

# Example: count number of edits per user in 1-minute windows
df_count = df \
    .withWatermark("timestamp", "2 minutes") \
    .groupBy(
        window(col("timestamp").cast("timestamp"), "1 minute"),
        col("user")
    ) \
    .count()

#Write the processed stream to console
query = df_count.writeStream \
    .outputMode("complete") \
    .format("console") \
    .option("truncate", False) \
    .start()

query.awaitTermination()
