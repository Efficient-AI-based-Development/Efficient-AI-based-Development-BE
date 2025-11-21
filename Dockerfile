# Multi-stage Dockerfile for Efficient AI Backend

# Stage 1: Build stage
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies using uv
RUN uv pip install --system \
    "fastapi==0.119.0" \
    "uvicorn[standard]==0.37.0" \
    "sqlalchemy" \
    "alembic" \
    "oracledb" \
    "pydantic==2.12.0" \
    "pydantic-settings==2.11.0" \
    "python-multipart" \
    "openai" \
    "fastmcp" \
    "python-jose[cryptography]" \
    "passlib[bcrypt]" \
    "httpx" \
    "orjson==3.11.3" \
    "python-dotenv==1.1.1" \
    "requests==2.32.5" \
    "langchain==0.3.27" \
    "langchain-core==0.3.79" \
    "langchain-community==0.3.31" \
    "langchain-upstage==0.7.4" \
    "langchain-anthropic==0.3.22" \
    "langchain-openai==0.3.35" \
    "langchain-text-splitters==0.3.11" \
    "langgraph==0.6.10" \
    "sse-starlette"

# Stage 2: Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder image
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy application code
COPY app/ ./app/
COPY ai_module/ ./ai_module/
COPY alembic/ ./alembic/
COPY alembic.ini ./

RUN mkdir -p /app/logs && chown -R appuser:appuser /app


# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

