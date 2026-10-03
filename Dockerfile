# Production Dockerfile for SkillBridge
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy application code
COPY backend backend
COPY frontend frontend

# Create data directory for SQLite
RUN mkdir -p /app/backend/data

# Environment
ENV SKILLBRIDGE_DB=/app/backend/data/skillbridge.db
ENV PYTHONUNBUFFERED=1

# Expose port
#
# Platforms such as Render and Railway do not route to a fixed port. They
# inject a PORT variable and forward traffic to it, so the app must read it.
# Hardcoding 8000 here is what made the earlier deploy configs unusable: the
# container listened where nobody was listening.
ENV PORT=8000
EXPOSE 8000

# Health check must probe the same port the app actually binds.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/api/health" || exit 1

# Run the app.
#
# exec keeps uvicorn as PID 1 so it receives SIGTERM directly and shuts down
# cleanly; without it, /bin/sh would swallow the signal and the platform would
# SIGKILL the process after its grace period.
#
# --forwarded-allow-ips trusts the platform's proxy for client IPs. That is
# safe here because the app is not reachable except through that proxy.
CMD exec uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips="*"
