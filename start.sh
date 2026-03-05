#!/bin/bash
echo "=========================================="
echo "🚀 PYTHON & JS HOSTING BAŞLATILIYOR"
echo "=========================================="
echo "PORT: $PORT"
echo "PWD: $(pwd)"
echo "Python: $(python --version)"
echo "=========================================="

# Klasörleri oluştur
mkdir -p uploads/projects
mkdir -p uploads/temp
mkdir -p templates
mkdir -p static

# Gunicorn ile başlat
gunicorn --bind 0.0.0.0:$PORT \
         --workers 2 \
         --threads 4 \
         --timeout 120 \
         --access-logfile - \
         --error-logfile - \
         --log-level info \
         server:app
