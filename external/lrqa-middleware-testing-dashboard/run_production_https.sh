#!/bin/bash
# Production server runner using Gunicorn with HTTPS support

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run with Gunicorn (production-grade WSGI server) with HTTPS
gunicorn --bind 0.0.0.0:8080 \
         --workers 8 \
         --worker-class gevent \
         --worker-connections 2000 \
         --timeout 300 \
         --certfile=ssl/cert.pem \
         --keyfile=ssl/key.pem \
         --access-logfile - \
         --error-logfile - \
         --log-level info \
         app:app
