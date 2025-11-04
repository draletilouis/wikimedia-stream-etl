import json
import os
from kafka import KafkaProducer
import requests

# Kafka configuration (use environment variables with defaults)
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'localhost:9092')
TOPIC_NAME = os.getenv('TOPIC_NAME', 'wiki_changes')

# Wikimedia EventStreams URL
WIKI_SSE_URL = 'https://stream.wikimedia.org/v2/stream/recentchange'

# Serializer function
def serializer(event):
    """Convert Python dict to JSON bytes for Kafka."""
    return json.dumps(event).encode('utf-8')

# Initialize Kafka producer
producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=serializer
)

def consume_wiki_stream(url=WIKI_SSE_URL):
    print("Connecting to Wikimedia EventStream...")

    # Create a requests session with stream=True and proper headers
    headers = {
        'Accept': 'text/event-stream',
        'User-Agent': 'WikiStreamConsumer/1.0 (Educational Project; Python/3.11)'
    }

    response = requests.get(url, stream=True, headers=headers)
    response.raise_for_status()

    print("Connected successfully. Listening for events...")

    # Process the SSE stream line by line
    for line in response.iter_lines(decode_unicode=True):
        if line and line.startswith('data: '):
            try:
                # Extract JSON data after "data: " prefix
                json_data = line[6:]  # Remove "data: " prefix
                event = json.loads(json_data)

                # Optional: filter only main namespace edits
                if event.get('namespace') == 0:
                    producer.send(TOPIC_NAME, value=event)
                    print(f"Sent edit: {event.get('title')} by {event.get('user')}")
            except json.JSONDecodeError as e:
                print(f"Failed to decode JSON: {e}")
            except Exception as e:
                print(f"Error sending to Kafka: {e}")

if __name__ == "__main__":
    try:
        consume_wiki_stream()
    except KeyboardInterrupt:
        print("\nStopping ingestion...")
    finally:
        print("Flushing and closing Kafka producer...")
        producer.flush()  # Ensure all messages are sent
        producer.close()  # Clean shutdown
        print("Done.")