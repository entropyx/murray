FROM python:3.12.7

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the rest of the application
COPY . .

# create directory for metrics
RUN mkdir -p /app/traffic_metrics

# Define the volume
VOLUME ["/app/traffic_metrics"]

# Ensure fork method for multiprocessing
ENV PYTHONMULTIPROCESSING_START_METHOD=fork

EXPOSE 8501

# Add healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run the application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]