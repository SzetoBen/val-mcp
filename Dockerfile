# Use Python 3.11 slim base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Set working directory
WORKDIR /app

# Install system dependencies if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml to install dependencies
COPY pyproject.toml ./

# Install dependencies using pip
RUN pip install --no-cache-dir .

# Copy application code
COPY valorant.py ./valorant.py

# Expose the default port
EXPOSE 8080

# Start the server (valorant.py checks for PORT environment variable to run in SSE mode)
CMD ["python", "valorant.py"]
