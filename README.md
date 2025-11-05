# Wikimedia Streaming Analytics Project

A real-time data pipeline that ingests Wikipedia edit events, processes them with Apache Spark, stores aggregated metrics in PostgreSQL, and visualizes them in a dashboard.

## Architecture

```
Wikipedia SSE Stream → Kafka → Spark Streaming → PostgreSQL → Streamlit Dashboard
    (Real-time)       (Buffer)   (Aggregation)    (Storage)    (Visualization)
```

### Data Flow

1. **Ingestion**: Python consumer connects to Wikimedia EventStreams (SSE) and publishes events to Kafka
2. **Buffering**: Kafka stores raw events temporarily, providing fault tolerance and decoupling
3. **Processing**: Spark Streaming reads from Kafka, aggregates edits per user/minute, writes to PostgreSQL
4. **Storage**: PostgreSQL stores pre-aggregated metrics (not raw events)
5. **Dashboard**: Streamlit queries PostgreSQL for real-time visualizations

## Features

- ✅ Real-time Wikipedia edit stream ingestion
- ✅ Distributed message buffering with Kafka
- ✅ Windowed aggregations with Apache Spark
- ✅ Time-series data storage in PostgreSQL
- ✅ Configuration-driven (no hardcoded values)
- ✅ Docker Compose for easy deployment
- ✅ Scalable and production-ready

## Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- 4GB RAM minimum
- Port availability: 2181, 9092, 29092, 5433, 8501

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd wikimedia-streaming-project

# Create environment file
cp .env.example .env

# (Optional) Edit .env to change passwords
nano .env
```

### 2. Start Infrastructure

```bash
cd docker
docker-compose up -d
```

This starts:
- Zookeeper (Kafka dependency)
- Kafka broker
- PostgreSQL database
- Wiki consumer (ingestion service)

### 3. Run Spark Streaming Job

```bash
cd processing
pip install -r requirements.txt
python spark_streaming_job.py
```

You should see logs like:
```
Configuration loaded successfully
Starting Kafka stream reader...
Batch 0: Wrote 25 rows to PostgreSQL
```

### 4. Verify Data

```bash
# Check Kafka has messages
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic wiki_changes \
  --from-beginning \
  --max-messages 5

# Check PostgreSQL has data
docker exec -it postgres psql -U wiki_user -d wiki_streaming \
  -c "SELECT * FROM user_edit_counts ORDER BY window_start DESC LIMIT 10;"
```

### 5. View Dashboard (Coming Soon)

```bash
cd dashboards
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Open browser to `http://localhost:8501`

## Project Structure

```
wikimedia-streaming-project/
├── ingestion/              # Data ingestion service
│   ├── wiki_sse_consumer.py   # Wikimedia → Kafka
│   ├── Dockerfile
│   └── requirements.txt
│
├── processing/             # Spark streaming jobs
│   ├── spark_streaming_job.py  # Kafka → PostgreSQL
│   └── requirements.txt
│
├── database/               # Database schemas
│   ├── init.sql              # Table definitions
│   └── README.md
│
├── dashboards/             # Visualization layer
│   ├── streamlit_app.py      # Dashboard app
│   └── requirements.txt
│
├── config/                 # Configuration files
│   ├── conf.yaml             # Main configuration
│   └── README.md             # Config guide
│
├── common/                 # Shared utilities
│   └── config_loader.py      # Config loader
│
├── docker/                 # Docker configuration
│   └── docker-compose.yml    # Service definitions
│
├── .env.example            # Environment variables template
├── .gitignore
└── README.md               # This file
```

## Configuration

All settings are in `config/conf.yaml`. Key configurations:

### Ingestion
```yaml
ingestion:
  wikimedia:
    url: "https://stream.wikimedia.org/v2/stream/recentchange"
    filters:
      namespaces: [0]  # 0 = main articles only
```

### Kafka
```yaml
kafka:
  broker: "kafka:9092"  # Docker internal address
  topics:
    wiki_changes: "wiki_changes"
```

### Spark
```yaml
spark:
  windowing:
    duration: "1 minute"      # Aggregation window size
    watermark: "2 minutes"    # Late event tolerance
  trigger:
    processing_time: "30 seconds"  # Batch interval
```

### PostgreSQL
```yaml
postgres:
  host: "postgres"
  database: "wiki_streaming"
  user: "wiki_user"
  password: "${POSTGRES_PASSWORD}"  # From .env
```

See [config/README.md](config/README.md) for full configuration guide.

## Environment Variables

Create `.env` file with:

```bash
# Database
POSTGRES_PASSWORD=wiki_password
POSTGRES_USER=wiki_user
POSTGRES_DB=wiki_streaming

# Environment
ENVIRONMENT=development
```

See [.env.example](.env.example) for all options.

## Database Schema

### user_edit_counts
Stores aggregated edit counts per user per time window.

| Column | Type | Description |
|--------|------|-------------|
| window_start | TIMESTAMP | Window start time |
| window_end | TIMESTAMP | Window end time |
| user_name | VARCHAR(255) | Wikipedia username |
| edit_count | BIGINT | Number of edits in window |
| created_at | TIMESTAMP | Insert timestamp |

**Indexes:**
- Primary key: `(window_start, user_name)`
- Index on `window_start DESC` (for time-range queries)
- Index on `user_name` (for user lookups)

### Views
- `recent_user_activity` - Last 24 hours of activity
- `top_contributors_hourly` - Top 50 users in last hour

See [database/README.md](database/README.md) for details.

## Development

### Run Locally (Without Docker)

**Terminal 1 - Infrastructure:**
```bash
cd docker
docker-compose up kafka postgres  # Just Kafka and PostgreSQL
```

**Terminal 2 - Ingestion:**
```bash
cd ingestion
pip install -r requirements.txt
export KAFKA_BROKER=localhost:29092  # Use host port
python wiki_sse_consumer.py
```

**Terminal 3 - Processing:**
```bash
cd processing
pip install -r requirements.txt
export KAFKA_BOOTSTRAP_SERVERS=localhost:29092
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5433
python spark_streaming_job.py
```

### Configuration Override

Use environment variables to override config:

```bash
# Change window size
export SPARK_WINDOWING_DURATION="5 minutes"

# Change log level
export SPARK_LOG_LEVEL=DEBUG

# Run with overrides
python spark_streaming_job.py
```

### Add Custom Aggregations

Edit `processing/spark_streaming_job.py`:

```python
# Example: Count edits by namespace
df_namespace = df \
    .withWatermark("timestamp", WATERMARK_DURATION) \
    .groupBy(
        window(col("timestamp").cast("timestamp"), WINDOW_DURATION),
        col("namespace")
    ) \
    .count()
```

## Monitoring

### Check Service Health

```bash
# View all containers
docker-compose ps

# Check logs
docker-compose logs -f wiki-consumer
docker-compose logs -f kafka

# Spark job logs
tail -f processing/logs/spark.log
```

### Kafka Monitoring

```bash
# List topics
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Check consumer lag
docker exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group spark_streaming_consumer \
  --describe
```

### Database Queries

```sql
-- Total edits in last hour
SELECT SUM(edit_count) as total_edits
FROM user_edit_counts
WHERE window_start >= NOW() - INTERVAL '1 hour';

-- Top 10 contributors today
SELECT user_name, SUM(edit_count) as total
FROM user_edit_counts
WHERE window_start >= CURRENT_DATE
GROUP BY user_name
ORDER BY total DESC
LIMIT 10;

-- Activity timeline (edits per minute, last hour)
SELECT window_start, SUM(edit_count) as edits
FROM user_edit_counts
WHERE window_start >= NOW() - INTERVAL '1 hour'
GROUP BY window_start
ORDER BY window_start;
```

## Troubleshooting

### Kafka connection refused

**Problem:** Can't connect to Kafka

**Solution:**
- From Docker containers: Use `kafka:9092`
- From host machine: Use `localhost:29092`
- Set `KAFKA_BROKER` environment variable accordingly

### No data in PostgreSQL

**Problem:** Tables are empty

**Checks:**
1. Is wiki-consumer running? `docker-compose logs wiki-consumer`
2. Is Kafka receiving messages? (See Kafka monitoring above)
3. Is Spark job running? Check console output
4. Check Spark checkpoint: `ls -la /tmp/spark_checkpoint/`

**Solution:** Restart Spark with fresh checkpoint:
```bash
rm -rf /tmp/spark_checkpoint
python spark_streaming_job.py
```

### Out of memory

**Problem:** Spark crashes with OOM

**Solution:** Adjust executor memory in `config/conf.yaml`:
```yaml
spark:
  executor:
    memory: "4g"  # Increase from 2g
```

### Port already in use

**Problem:** `Bind for 0.0.0.0:5432 failed`

**Solution:** Change port in `docker/docker-compose.yml`:
```yaml
ports:
  - "5433:5432"  # Already set to avoid conflicts
```

## Performance Tuning

### Increase Throughput

1. **Reduce window size:**
   ```yaml
   spark:
     windowing:
       duration: "30 seconds"  # Smaller windows = more frequent writes
   ```

2. **Increase parallelism:**
   ```yaml
   spark:
     executor:
       instances: 4
       cores: 2
   ```

3. **Tune Kafka batch size:**
   ```yaml
   kafka:
     producer:
       batch_size: 32768  # Increase from 16384
       linger_ms: 20      # Wait longer for batches
   ```

### Reduce Latency

1. **Faster triggers:**
   ```yaml
   spark:
     trigger:
       processing_time: "10 seconds"  # Down from 30 seconds
   ```

2. **Reduce watermark:**
   ```yaml
   spark:
     windowing:
       watermark: "30 seconds"  # Down from 2 minutes
   ```

## Production Deployment

### Recommendations

1. **Security:**
   - Change default passwords in `.env`
   - Enable Kafka authentication (SASL)
   - Use SSL for PostgreSQL connections
   - Don't expose Kafka ports publicly

2. **Scaling:**
   - Deploy Kafka cluster (3+ brokers)
   - Use distributed storage for checkpoints (S3, HDFS)
   - Run Spark on cluster (YARN, Kubernetes)
   - Add PostgreSQL read replicas

3. **Reliability:**
   - Enable Kafka replication (factor=3)
   - Configure retention policies
   - Set up monitoring (Prometheus + Grafana)
   - Implement alerting

4. **Data Retention:**
   ```sql
   -- Schedule cleanup job
   DELETE FROM user_edit_counts
   WHERE window_start < NOW() - INTERVAL '30 days';
   ```

### Production Configuration

Create `config/conf.prod.yaml`:
```yaml
spark:
  checkpoint:
    location: "s3a://your-bucket/spark/checkpoints"
  executor:
    instances: 4
    cores: 4
    memory: "4g"

kafka:
  retention:
    ms: 2592000000  # 30 days

postgres:
  pool:
    max_size: 20

monitoring:
  enabled: true
```

Load with:
```bash
export ENVIRONMENT=prod
python spark_streaming_job.py
```

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-aggregation`
3. Commit changes: `git commit -am 'Add namespace aggregation'`
4. Push to branch: `git push origin feature/new-aggregation`
5. Submit pull request

## License

This project is licensed under the MIT License.

## Acknowledgments

- Wikimedia Foundation for the EventStreams API
- Apache Kafka and Spark communities
- PostgreSQL development team

## Resources

- [Wikimedia EventStreams Documentation](https://wikitech.wikimedia.org/wiki/Event_Platform/EventStreams)
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Apache Spark Streaming Guide](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## Contact

For questions or issues, please open an issue on GitHub.

---

**Status:** ✅ Production Ready

**Last Updated:** 2025-11-05
