# Dockerfile for Spark Streaming Processor
FROM python:3.11-slim

# Install Java (required for Spark)
RUN apt-get update && \
    apt-get install -y openjdk-21-jre-headless && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set Java home
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY spark_streaming_job.py .

# Note: common and config directories are mounted as volumes by docker-compose

# Create checkpoint directory
RUN mkdir -p /tmp/spark_checkpoint

# Set environment variables for Spark
ENV PYSPARK_PYTHON=python3
ENV PYSPARK_DRIVER_PYTHON=python3

# Run the Spark streaming job
CMD ["python", "-u", "spark_streaming_job.py"]
