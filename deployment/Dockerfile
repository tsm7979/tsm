# Multi-stage Dockerfile for TSM Platform
# Optimized for production deployment

# Stage 1: Builder
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /build

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Set labels
LABEL maintainer="TSM Platform <dev@tsm-platform.com>"
LABEL version="1.0.0"
LABEL description="TSM AI Control Plane"

# Create non-root user
RUN groupadd -r tsm && useradd -r -g tsm tsm

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/tsm/.local

# Copy application code
COPY --chown=tsm:tsm . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R tsm:tsm /app/data /app/logs /app/config

# Set Python path
ENV PATH=/home/tsm/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose ports
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Switch to non-root user
USER tsm

# Run application
CMD ["python", "-m", "uvicorn", "gateway.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
