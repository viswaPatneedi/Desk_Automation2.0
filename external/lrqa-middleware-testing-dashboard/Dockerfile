# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    FLASK_ENV=production \
    VIRTUAL_ENV=/app/venv \
    PATH="/app/venv/bin:$PATH"

# Install system dependencies
# Tesseract OCR is needed for AI vision/OCR functionality
# python3-venv is needed for virtual environment
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    gcc \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /app/venv

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies in virtual environment
RUN /app/venv/bin/pip install --upgrade pip && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy application code (excludes via .dockerignore: logs, screenshots, old_code, etc.)
COPY . .

# Create mount points for external data (will be mounted as volumes at runtime)
RUN mkdir -p /app/data \
    /app/data/screenshots \
    /app/data/iteration_logs \
    /app/data/execution_logs \
    /app/data/device_logs \
    /app/data/app_logs \
    /app/data/sessions

# Email service environment variables (can be overridden at runtime)
# Default: Gmail SMTP (requires app password)
ENV SMTP_HOST=smtp.gmail.com \
    SMTP_PORT=587 \
    SENDER_EMAIL=cperdkemiddleware@gmail.com \
    SENDER_PASSWORD=""

# Expose port 5000 for Flask application
EXPOSE 5000

# Health check to ensure container is running properly
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /app/venv/bin/python -c "import requests; requests.get('http://localhost:5000/health', timeout=5)" || exit 1

# Run the application with Gunicorn (production-grade WSGI server) using virtual environment
CMD ["/app/venv/bin/gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "300", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "app:app"]
