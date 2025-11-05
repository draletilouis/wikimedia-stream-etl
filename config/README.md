# Configuration Guide

This directory contains configuration files for the Wikimedia Streaming Project.

## Files

- **conf.yaml** - Main configuration file with all application settings
- **conf.{env}.yaml** (optional) - Environment-specific overrides

## Configuration Layers

The configuration system uses a layered approach:

```
1. conf.yaml (base configuration)
   ↓
2. conf.{environment}.yaml (environment overrides, optional)
   ↓
3. Environment variables (runtime overrides)
   ↓
4. Command-line arguments (highest priority, if supported)
```

## Usage

### In Python Code

```python
from common.config_loader import load_config

# Load default configuration
config = load_config()

# Access configuration values using dot notation
kafka_broker = config.get('kafka.broker')
window_duration = config.get('spark.windowing.duration')

# Access with default value
log_level = config.get('logging.level', 'INFO')

# Get entire section
postgres_config = config.get_section('postgres')
```

### Environment Variable Overrides

The following environment variables can override configuration values:

| Environment Variable | Overrides | Example |
|---------------------|-----------|---------|
| `KAFKA_BROKER` | `kafka.broker` | `kafka:9092` |
| `KAFKA_BOOTSTRAP_SERVERS` | `spark.kafka.bootstrap_servers` | `localhost:29092` |
| `POSTGRES_HOST` | `postgres.host` | `localhost` |
| `POSTGRES_PORT` | `postgres.port` | `5433` |
| `POSTGRES_DB` | `postgres.database` | `wiki_streaming` |
| `POSTGRES_USER` | `postgres.user` | `wiki_user` |
| `POSTGRES_PASSWORD` | `postgres.password` | `secret` |
| `SPARK_LOG_LEVEL` | `spark.log_level` | `WARN` |
| `CHECKPOINT_LOCATION` | `spark.checkpoint.location` | `/tmp/checkpoint` |
| `ENVIRONMENT` | Environment name | `production` |

### Docker Usage

When running with Docker Compose:

1. Create `.env` file from template:
   ```bash
   cp ../.env.example ../.env
   ```

2. Edit `.env` with your values:
   ```bash
   POSTGRES_PASSWORD=your_secure_password
   ENVIRONMENT=production
   ```

3. Start services:
   ```bash
   cd docker
   docker-compose up -d
   ```

The configuration files are mounted as read-only volumes into containers.

## Environment-Specific Configuration

### Development

Create `conf.dev.yaml`:
```yaml
spark:
  log_level: "DEBUG"
  checkpoint:
    location: "/tmp/spark_checkpoint"

logging:
  level: "DEBUG"
```

Load with:
```python
config = load_config(env='dev')
# Or set environment variable
# export ENVIRONMENT=dev
```

### Production

Create `conf.prod.yaml`:
```yaml
spark:
  log_level: "ERROR"
  checkpoint:
    location: "s3a://your-bucket/spark/checkpoints"

  executor:
    instances: 4
    cores: 4
    memory: "4g"

postgres:
  pool:
    max_size: 20

monitoring:
  enabled: true
```

## Configuration Sections

### Ingestion

Controls Wikipedia stream ingestion behavior:

- **url**: Wikimedia EventStreams endpoint
- **filters.namespaces**: Which namespaces to ingest (0 = articles)
- **retry**: Retry configuration for connection failures

### Kafka

Kafka broker and topic configuration:

- **broker**: Kafka broker address
- **topics**: Topic names
- **producer**: Producer tuning parameters
- **consumer**: Consumer group settings

### Spark

Spark Streaming job configuration:

- **windowing**: Window and watermark durations
- **trigger**: Micro-batch trigger interval
- **checkpoint**: Checkpoint location
- **executor**: Executor resources (cluster mode)

### PostgreSQL

Database connection and behavior:

- **host/port/database**: Connection details
- **user/password**: Credentials (use env vars!)
- **pool**: Connection pooling settings
- **write**: Write batch size and mode

### Dashboard

Streamlit dashboard settings:

- **refresh**: Auto-refresh interval
- **queries**: Default time ranges
- **layout**: Theme and display options

### Logging

Application logging configuration:

- **level**: Global log level
- **format**: Log message format
- **components**: Component-specific log levels

## Security Best Practices

### ❌ Don't

- Commit `.env` files to version control
- Hard-code passwords in configuration files
- Use default passwords in production
- Share configuration files with credentials

### ✅ Do

- Use environment variables for secrets
- Reference secrets using `${VAR_NAME}` syntax
- Use different credentials per environment
- Rotate passwords regularly
- Use read-only volume mounts in Docker

## Validation

Configuration is automatically validated on load. Required keys:

- `kafka.broker`
- `kafka.topics.wiki_changes`
- `postgres.host`
- `postgres.database`
- `postgres.user`

Missing required keys will raise a `ValueError`.

## Troubleshooting

### Configuration not loading

**Issue**: `Config file not found`

**Solution**: Ensure `config/conf.yaml` exists or set `CONFIG_PATH` environment variable:
```bash
export CONFIG_PATH=/path/to/conf.yaml
```

### Environment variables not substituted

**Issue**: Configuration shows `${POSTGRES_PASSWORD}` literal

**Solution**: Ensure environment variable is set before running:
```bash
export POSTGRES_PASSWORD=mypassword
python script.py
```

### Docker containers can't connect

**Issue**: Connection refused errors

**Solution**: Use Docker service names in configuration:
- ✅ `kafka:9092` (inside Docker network)
- ❌ `localhost:9092` (won't work from container)

Set overrides in docker-compose.yml:
```yaml
environment:
  KAFKA_BROKER: 'kafka:9092'
```

## Examples

### Minimal Configuration

```yaml
kafka:
  broker: "localhost:29092"
  topics:
    wiki_changes: "wiki_changes"

postgres:
  host: "localhost"
  port: 5433
  database: "wiki_streaming"
  user: "wiki_user"
  password: "${POSTGRES_PASSWORD}"

spark:
  kafka:
    bootstrap_servers: "localhost:29092"
```

### Production Configuration

See `conf.yaml` for comprehensive production-ready configuration with all available options.
