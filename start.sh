#!/bin/bash
echo "========================================"
echo "🚀 Python Hosting Başlatılıyor"
echo "========================================"
echo "PORT: $PORT"
echo "PWD: $(pwd)"
echo "========================================"

# Gerekli klasörleri oluştur
mkdir -p uploads/projects
mkdir -p uploads/temp

# Gunicorn ile başlat
gunicorn --bind 0.0.0.0:$PORT \
         --workers 1 \
         --threads 2 \
         --timeout 120 \
         --access-logfile - \
         --error-logfile - \
         server:app