FROM python:3.9-alpine

WORKDIR /app

# Install system dependencies including curl for health checks
RUN apk update && apk add --no-cache \
    curl \
    sqlite \
    podman \
    sudo \
    shadow \
    && rm -rf /var/cache/apk/*

# Create a non-root user and add to sudoers (for Podman operations)
RUN adduser -D -s /bin/sh podmanuser && \
    echo 'podmanuser ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs database

# Change ownership of the app directory to podmanuser
RUN chown -R podmanuser:podmanuser /app

# Switch to non-root user
USER podmanuser

EXPOSE 5000

ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV FLASK_RUN_HOST=0.0.0.0

CMD ["python", "app.py"]