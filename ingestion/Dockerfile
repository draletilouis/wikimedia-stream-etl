FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY wiki_sse_consumer.py .

# Set environment variables (can be overridden in docker-compose)
ENV KAFKA_BROKER=kafka:9092
ENV TOPIC_NAME=wiki_changes

# Run the consumer
CMD ["python", "-u", "wiki_sse_consumer.py"]
