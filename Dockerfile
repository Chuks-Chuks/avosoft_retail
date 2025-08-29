FROM python:3.11-slim

WORKDIR /app

# Install system deps (kept minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy project
COPY . /app

# Make sure module imports work
ENV PYTHONPATH=/app

# Default command (compose will override with --date)
CMD ["python", "-m", "avosoft_engine.cli"]