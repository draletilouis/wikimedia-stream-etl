# Wikimedia Streaming Project - Setup Guide

## Architecture Overview

```
Wikimedia SSE Stream → Kafka Topic → Spark Streaming → PostgreSQL → Dashboard
   (Raw events)      (Buffer)      (Aggregation)    (Storage)    (Queries)
```

## Components

### 1. **Ingestion Layer** - [ingestion/wiki_sse_consumer.py](ingestion/wiki_sse_consumer.py)
- Consumes Wikipedia real-time edit stream via SSE
- Publishes raw events to Kafka topic `wiki_changes`

### 2. **Message Broker** - Kafka
- Buffers raw events between ingestion and processing
- Provides reliability and decoupling
- Configured in [docker/docker-compose.yml](docker/docker-compose.yml)

### 3. **Processing Layer** - [processing/spark_streaming_job.py](processing/spark_streaming_job.py)
- Reads from Kafka topic
- Aggregates edits per user per 1-minute window
- Writes aggregated data to PostgreSQL every 30 seconds

### 4. **Storage Layer** - PostgreSQL
- Stores pre-aggregated metrics (not raw events)
- Tables: `user_edit_counts`, `namespace_edit_counts`, `top_pages`
- Views for common queries: `recent_user_activity`, `top_contributors_hourly`

## Quick Start

### 1. Start Infrastructure
```bash
cd docker
docker-compose up -d
```

This starts:
- Zookeeper (port 2181)
- Kafka (ports 9092, 29092)
- PostgreSQL (port 5433)
- Wiki Consumer (ingestion service)

### 2. Run Spark Streaming Job
```bash
cd processing
pip install -r requirements.txt
python spark_streaming_job.py
```

### 3. Verify Data Flow

Check Kafka has messages:
```bash
docker exec -it kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic wiki_changes --from-beginning --max-messages 5
```

Check PostgreSQL has aggregations:
```bash
docker exec -it postgres psql -U wiki_user -d wiki_streaming -c "SELECT * FROM user_edit_counts ORDER BY window_start DESC LIMIT 10;"
```

## Configuration

### Database Connection
- **Host**: localhost:5433
- **Database**: wiki_streaming
- **User**: wiki_user
- **Password**: wiki_password

### Spark Processing
- **Window size**: 1 minute
- **Watermark**: 2 minutes (handles late events)
- **Trigger interval**: 30 seconds
- **Output mode**: update (only changed rows)

## Data Flow Example

1. **Raw Event** (from Wikimedia):
```json
{
  "id": "12345",
  "title": "Python (programming language)",
  "user": "AliceEditor",
  "type": "edit",
  "namespace": 0,
  "timestamp": 1699189234000
}
```

2. **Spark Aggregation** (1-minute window):
```
window_start: 2025-11-05 10:00:00
window_end:   2025-11-05 10:01:00
user_name:    AliceEditor
edit_count:   15
```

3. **PostgreSQL Storage**:
```sql
INSERT INTO user_edit_counts VALUES
  ('2025-11-05 10:00:00', '2025-11-05 10:01:00', 'AliceEditor', 15);
```

4. **Dashboard Query**:
```sql
SELECT user_name, SUM(edit_count) as total
FROM user_edit_counts
WHERE window_start >= NOW() - INTERVAL '1 hour'
GROUP BY user_name
ORDER BY total DESC LIMIT 10;
```

## Next Steps

1. **Dashboard**: Create Streamlit app to visualize metrics from PostgreSQL
2. **More Aggregations**: Add namespace and top pages aggregations
3. **Monitoring**: Add metrics collection and alerting
4. **Scaling**: Add more Kafka partitions and Spark executors

## Troubleshooting

### Spark can't connect to PostgreSQL
- Check port mapping (5433 on host → 5432 in container)
- Verify PostgreSQL is running: `docker ps | grep postgres`

### No data in PostgreSQL
- Check Spark logs for errors
- Verify Kafka has messages: `kafka-console-consumer`
- Check Spark checkpoint location: `/tmp/spark_checkpoint`

### Kafka consumer lag
- Increase Spark processing parallelism
- Reduce window size or trigger interval
- Add more Spark executors
