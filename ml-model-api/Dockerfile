# Multi-stage build for production-ready Flask ML API
# Stage 1: Dependencies stage
FROM python:3.11-slim AS dependencies

# Set build arguments
ARG BUILD_ENV=production

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgomp1 \
        libglib2.0-0 \
        libgtk-3-0 \
        libavcodec-dev \
        libavformat-dev \
        libswscale-dev \
        && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Production stage
FROM python:3.11-slim AS production

# Security: Create non-root user
RUN groupadd -r appuser && \
    useradd -r -g appuser -d /app -s /bin/bash appuser

# Install runtime system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgomp1 \
        libgtk-3-0 \
        libavcodec58 \
        libavformat58 \
        libswscale5 \
        curl \
        && rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    FLASK_ENV=production \
    FLASK_APP=app.py

# Copy Python dependencies from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories with proper permissions
RUN mkdir -p /app/uploads /app/models /app/logs && \
    chown -R appuser:appuser /app/uploads /app/models /app/logs

# Change to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run the application
CMD ["python", "app.py"]
