# Dockerfile for FastMCP API Server
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (if exists) or install directly
COPY requirements.txt* ./

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    python-dotenv \
    openai \
    anthropic

# Copy application code
COPY server.py ./

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8787

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8787/health')" || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8787"]

