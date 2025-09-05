FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy data file (add this line)
COPY data/dataset.csv /app/data/dataset.csv

# Create startup script
RUN echo '#!/bin/bash\n\
echo "🎵 Starting Spotify Music Explorer..."\n\
echo "⚡ Backend will be available at: http://localhost:8000"\n\
echo "🎯 Dashboard will be available at: http://localhost:8501"\n\
echo ""\n\
\n\
# Start FastAPI backend\n\
echo "Starting FastAPI backend..."\n\
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &\n\
BACKEND_PID=$!\n\
\n\
# Wait for backend to start\n\
echo "Waiting for backend to initialize..."\n\
sleep 8\n\
\n\
# Start Streamlit frontend\n\
echo "Starting Streamlit dashboard..."\n\
streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true\n\
' > /app/start.sh && chmod +x /app/start.sh

# Expose ports
EXPOSE 8000 8501

# Run startup script
CMD ["/app/start.sh"]