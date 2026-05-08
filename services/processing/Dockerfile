FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed by some Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# This service is a worker, not a web server
CMD ["python", "-m", "app.main"]