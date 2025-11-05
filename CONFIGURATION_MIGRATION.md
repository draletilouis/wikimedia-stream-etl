# Configuration Migration Summary

## What Changed

Your project has been migrated from hardcoded values to a production-ready configuration system.

### Before (Hardcoded)

```python
# ingestion/wiki_sse_consumer.py
KAFKA_BROKER = 'localhost:9092'  # ❌ Hardcoded
WIKI_SSE_URL = 'https://...'     # ❌ Hardcoded

# processing/spark_streaming_job.py
POSTGRES_URL = 'jdbc:postgresql://localhost:5433/...'  # ❌ Hardcoded
window(..., "1 minute")  # ❌ Hardcoded
.trigger(processingTime='30 seconds')  # ❌ Hardcoded
```

**Problems:**
- Values mixed in code
- Different values in different files
- Can't change without editing code
- Docker vs local requires code changes
- Secrets in version control

### After (Configuration-Driven)

```python
# All services load from config
from common.config_loader import load_config
config = load_config()

# Values from config/conf.yaml
KAFKA_BROKER = config.get('kafka.broker')
WINDOW_DURATION = config.get('spark.windowing.duration')
POSTGRES_URL = f'jdbc:postgresql://{config.get("postgres.host")}:...'
```

**Benefits:**
- ✅ Single source of truth ([config/conf.yaml](config/conf.yaml))
- ✅ Environment-specific overrides
- ✅ Secrets via environment variables
- ✅ Change behavior without code changes
- ✅ Docker and local work with same code

---

## New Files Created

### 1. Configuration Files

| File | Purpose |
|------|---------|
| [config/conf.yaml](config/conf.yaml) | Main configuration with all settings |
| [.env.example](.env.example) | Template for environment variables |
| `.env` (gitignored) | Actual secrets (created from template) |

### 2. Configuration Loader

| File | Purpose |
|------|---------|
| [common/config_loader.py](common/config_loader.py) | Configuration loading utility |
| [common/__init__.py](common/__init__.py) | Package marker |

### 3. Documentation

| File | Purpose |
|------|---------|
| [config/README.md](config/README.md) | Configuration guide |
| [CONFIGURATION_MIGRATION.md](CONFIGURATION_MIGRATION.md) | This file |

---

## Files Modified

### 1. Ingestion Service

**File**: [ingestion/wiki_sse_consumer.py](ingestion/wiki_sse_consumer.py)

**Changes:**
- Added config loader import
- Removed hardcoded values
- Load settings from config
- Added proper logging
- Configurable namespace filtering
- Kafka producer tuning from config

**New features:**
- Event counting and statistics
- Configurable batch sizes
- Compression settings

### 2. Spark Streaming Job

**File**: [processing/spark_streaming_job.py](processing/spark_streaming_job.py)

**Changes:**
- Added config loader import
- All hardcoded values now from config:
  - Kafka bootstrap servers
  - PostgreSQL connection
  - Window duration
  - Watermark duration
  - Trigger interval
  - Checkpoint location
  - JAR packages
  - Log level
- Added proper logging
- Dynamic JDBC URL construction

**Configurable parameters:**
- Window size (was: 1 minute, now: configurable)
- Watermark (was: 2 minutes, now: configurable)
- Trigger (was: 30 seconds, now: configurable)
- Checkpoint path (was: /tmp/..., now: configurable)

### 3. Docker Compose

**File**: [docker/docker-compose.yml](docker/docker-compose.yml)

**Changes:**
- Added environment variable substitution
- Mount config directory as read-only volume
- Mount common utilities
- Use `.env` file for secrets
- Database credentials from environment

**New capabilities:**
- Change passwords via `.env`
- Override settings per environment
- Secure secret management

### 4. Requirements

Updated all `requirements.txt` files to include `pyyaml>=6.0`.

### 5. .gitignore

**File**: [.gitignore](.gitignore)

**Added:**
- Spark checkpoint directories
- Log directories
- `.env` file (secrets protection)

---

## How to Use

### Setup (One Time)

1. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your secrets:**
   ```bash
   # Edit this file
   nano .env
   ```

3. **Review configuration:**
   ```bash
   # Check config/conf.yaml
   # Adjust values as needed
   ```

### Running Services

#### Docker (Production)

```bash
cd docker
docker-compose up -d
```

Configuration is automatically loaded from:
- `config/conf.yaml` (mounted as volume)
- `.env` (environment variables)

#### Local Development

```bash
# Terminal 1: Ingestion
cd ingestion
pip install -r requirements.txt
python wiki_sse_consumer.py

# Terminal 2: Processing
cd processing
pip install -r requirements.txt
python spark_streaming_job.py
```

Configuration is loaded from:
- `config/conf.yaml` (relative path)
- Environment variables (if set)

### Changing Configuration

#### Option 1: Edit conf.yaml (Permanent)

```yaml
# config/conf.yaml
spark:
  windowing:
    duration: "5 minutes"  # Changed from 1 minute
  trigger:
    processing_time: "1 minute"  # Changed from 30 seconds
```

Restart services to apply.

#### Option 2: Environment Variables (Temporary/Override)

```bash
# Override for one run
export KAFKA_BROKER=different-kafka:9092
export SPARK_LOG_LEVEL=DEBUG
python spark_streaming_job.py
```

#### Option 3: Environment-Specific Config

```bash
# Create production config
cat > config/conf.prod.yaml <<EOF
spark:
  executor:
    instances: 4
    memory: "4g"
EOF

# Use it
export ENVIRONMENT=prod
python spark_streaming_job.py
```

---

## Configuration Reference

### Key Settings

#### Ingestion

```yaml
ingestion:
  wikimedia:
    url: "https://stream.wikimedia.org/v2/stream/recentchange"
    filters:
      namespaces: [0]  # Which namespaces to ingest
```

#### Kafka

```yaml
kafka:
  broker: "kafka:9092"  # Change for local: localhost:29092
  topics:
    wiki_changes: "wiki_changes"
  producer:
    batch_size: 16384
    compression_type: "snappy"
```

#### Spark

```yaml
spark:
  kafka:
    bootstrap_servers: "localhost:9092"  # For local Spark
  windowing:
    duration: "1 minute"
    watermark: "2 minutes"
  trigger:
    processing_time: "30 seconds"
  checkpoint:
    location: "/tmp/spark_checkpoint"
```

#### PostgreSQL

```yaml
postgres:
  host: "postgres"  # Docker: postgres, Local: localhost
  port: 5432        # Internal port (external: 5433)
  database: "wiki_streaming"
  user: "wiki_user"
  password: "${POSTGRES_PASSWORD}"  # From .env
```

---

## Environment Variable Mapping

| Environment Variable | Configuration Key | Default |
|---------------------|-------------------|---------|
| `KAFKA_BROKER` | `kafka.broker` | `kafka:9092` |
| `KAFKA_BOOTSTRAP_SERVERS` | `spark.kafka.bootstrap_servers` | `localhost:9092` |
| `POSTGRES_HOST` | `postgres.host` | `postgres` |
| `POSTGRES_PORT` | `postgres.port` | `5432` |
| `POSTGRES_DB` | `postgres.database` | `wiki_streaming` |
| `POSTGRES_USER` | `postgres.user` | `wiki_user` |
| `POSTGRES_PASSWORD` | `postgres.password` | (no default) |
| `CHECKPOINT_LOCATION` | `spark.checkpoint.location` | `/tmp/spark_checkpoint` |
| `ENVIRONMENT` | Environment name | `development` |

---

## Migration Checklist

- ✅ Created comprehensive configuration file
- ✅ Created configuration loader utility
- ✅ Updated ingestion service
- ✅ Updated Spark streaming job
- ✅ Updated Docker Compose for volume mounts
- ✅ Created .env template
- ✅ Added pyyaml to all requirements
- ✅ Updated .gitignore for secrets
- ✅ Created configuration documentation

---

## Testing the Migration

### 1. Verify Configuration Loads

```bash
cd processing
python -c "from common.config_loader import load_config; c=load_config(); print(c.get('kafka.broker'))"
```

Should print: `kafka:9092`

### 2. Test Docker Startup

```bash
cd docker
docker-compose config  # Validate docker-compose.yml
docker-compose up postgres  # Start just PostgreSQL
```

### 3. Test Full Pipeline

```bash
cd docker
docker-compose up -d
docker-compose logs -f wiki-consumer  # Check ingestion logs
```

Look for: `Configuration loaded - Kafka broker: kafka:9092`

---

## Troubleshooting

### Config file not found

**Error**: `Config file not found: config/conf.yaml`

**Solution**: Run from project root or set `CONFIG_PATH`:
```bash
export CONFIG_PATH=/full/path/to/config/conf.yaml
```

### Import error for config_loader

**Error**: `ModuleNotFoundError: No module named 'common'`

**Solution**: Install dependencies:
```bash
pip install pyyaml
```

Or ensure running from correct directory with `sys.path` fix.

### Docker can't find config

**Error**: Container logs show config errors

**Solution**: Ensure volumes are mounted correctly:
```bash
docker-compose config  # Check volume paths
```

Paths should be relative to `docker/` directory: `../config`

---

## Next Steps

1. **Review conf.yaml** - Adjust defaults for your use case
2. **Create .env** - Set secure passwords
3. **Test locally** - Run ingestion and processing
4. **Deploy** - Use docker-compose up
5. **Monitor** - Check logs for configuration values
6. **Iterate** - Adjust configuration as needed

---

## Benefits Achieved

| Aspect | Before | After |
|--------|--------|-------|
| **Maintenance** | Edit code | Edit config |
| **Docker vs Local** | Different code | Same code, different config |
| **Secrets** | In code | In .env (gitignored) |
| **Tuning** | Redeploy code | Restart service |
| **Environments** | Manual management | Automatic overrides |
| **Documentation** | Comments | Configuration file |
| **Validation** | Runtime errors | Startup validation |

Your project is now **production-ready** with proper configuration management!
