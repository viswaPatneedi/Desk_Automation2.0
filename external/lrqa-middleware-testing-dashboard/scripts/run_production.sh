#!/bin/bash
# Production server runner using Gunicorn (recommended for better performance)

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run with Gunicorn (production-grade WSGI server)
gunicorn --bind 0.0.0.0:5000 \
         --workers 4 \
         --timeout 300 \
         --access-logfile - \
         --error-logfile - \
         --log-level info \
         app:app
