# Golf Availability Monitor - Web Interface
# Multi-stage Docker build for Render deployment

FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8501

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy the entire project
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r streamlit_app/requirements.txt

# Install additional dependencies for the main golf monitor
RUN pip install --no-cache-dir -r requirements.txt

# Expose ports for both Streamlit and FastAPI
EXPOSE 8501
EXPOSE 8000

# Create startup script
RUN echo '#!/bin/bash\n\
cd /app/streamlit_app\n\
python api_server.py &\n\
sleep 3\n\
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT --server.enableCORS false --server.enableXsrfProtection false' > /app/start.sh

RUN chmod +x /app/start.sh

# Start the application
CMD ["/app/start.sh"]
