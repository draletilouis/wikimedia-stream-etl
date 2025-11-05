import json
import os
import sys
import logging
from pathlib import Path
from kafka import KafkaProducer
import requests

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

# Extract configuration values
KAFKA_BROKER = config.get('kafka.broker')
TOPIC_NAME = config.get('kafka.topics.wiki_changes')
WIKI_SSE_URL = config.get('ingestion.wikimedia.url')
USER_AGENT = config.get('ingestion.wikimedia.user_agent')
ALLOWED_NAMESPACES = config.get('ingestion.wikimedia.filters.namespaces', [0])

# Producer configuration
PRODUCER_CONFIG = {
    'batch_size': config.get('kafka.producer.batch_size', 16384),
    'linger_ms': config.get('kafka.producer.linger_ms', 10),
    'compression_type': config.get('kafka.producer.compression_type', 'snappy'),
    'max_in_flight_requests_per_connection': config.get('kafka.producer.max_in_flight_requests', 5),
    'acks': config.get('kafka.producer.acks', 1),
}

logger.info(f"Configuration loaded - Kafka broker: {KAFKA_BROKER}, Topic: {TOPIC_NAME}")

# Serializer function
def serializer(event):
    """Convert Python dict to JSON bytes for Kafka."""
    return json.dumps(event).encode('utf-8')

# Initialize Kafka producer with configuration
producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=serializer,
    **PRODUCER_CONFIG
)

def consume_wiki_stream(url=WIKI_SSE_URL):
    logger.info(f"Connecting to Wikimedia EventStream: {url}")
    logger.info(f"Filtering namespaces: {ALLOWED_NAMESPACES}")

    # Create a requests session with stream=True and proper headers
    headers = {
        'Accept': 'text/event-stream',
        'User-Agent': USER_AGENT
    }

    response = requests.get(url, stream=True, headers=headers)
    response.raise_for_status()

    logger.info("Connected successfully. Listening for events...")

    event_count = 0
    filtered_count = 0

    # Process the SSE stream line by line
    for line in response.iter_lines(decode_unicode=True):
        if line and line.startswith('data: '):
            try:
                # Extract JSON data after "data: " prefix
                json_data = line[6:]  # Remove "data: " prefix
                event = json.loads(json_data)
                event_count += 1

                # Filter by allowed namespaces
                namespace = event.get('namespace')
                if namespace in ALLOWED_NAMESPACES:
                    producer.send(TOPIC_NAME, value=event)
                    filtered_count += 1
                    logger.debug(f"Sent edit: {event.get('title')} by {event.get('user')}")

                    # Log stats every 100 events
                    if filtered_count % 100 == 0:
                        logger.info(f"Processed {event_count} events, sent {filtered_count} to Kafka")

            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON: {e}")
            except Exception as e:
                logger.error(f"Error sending to Kafka: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        consume_wiki_stream()
    except KeyboardInterrupt:
        logger.info("\nStopping ingestion...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        logger.info("Flushing and closing Kafka producer...")
        producer.flush()  # Ensure all messages are sent
        producer.close()  # Clean shutdown
        logger.info("Shutdown complete.")