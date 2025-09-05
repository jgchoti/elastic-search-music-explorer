FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Elasticsearch
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Elasticsearch (single node for demo)
RUN wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | apt-key add - \
    && echo "deb https://artifacts.elastic.co/packages/8.x/apt stable main" | tee /etc/apt/sources.list.d/elastic-8.x.list \
    && apt-get update && apt-get install -y elasticsearch

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Configure Elasticsearch for single node
RUN echo "discovery.type: single-node" >> /etc/elasticsearch/elasticsearch.yml \
    && echo "xpack.security.enabled: false" >> /etc/elasticsearch/elasticsearch.yml

# Create startup script
RUN echo '#!/bin/bash\n\
echo "Starting Elasticsearch..."\n\
service elasticsearch start\n\
sleep 30\n\
\n\
echo "Starting FastAPI backend..."\n\
uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} &\n\
\n\
echo "Starting Streamlit dashboard..."\n\
streamlit run app.py --server.address 0.0.0.0 --server.port ${PORT:-8501} --server.headless true\n\
' > /app/start.sh && chmod +x /app/start.sh

EXPOSE ${PORT:-8000}
CMD ["/app/start.sh"]