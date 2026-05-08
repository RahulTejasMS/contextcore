# ============================================================
# Dockerfile — Gateway Service
# Multi-stage build: keeps the final image small
# ============================================================

# Stage 1: Base image with Python
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements first (Docker caches this layer)
# So if only code changes, it won't re-install packages
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code
COPY app/ ./app/

# Tell Python not to write .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose the port this service runs on
EXPOSE 8000

# Command to start the service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]