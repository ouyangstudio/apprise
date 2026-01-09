# Production Dockerfile for Apprise
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml ./
COPY apprise/ ./apprise/
COPY bin/ ./bin/

# Install the package
RUN pip install -e .

# Create a directory for configuration
RUN mkdir -p /config

# Expose port (if running as API server)
EXPOSE 8000

# Set default command
ENTRYPOINT ["apprise"]
CMD ["--help"]
