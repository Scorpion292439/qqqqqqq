#!/bin/bash
echo "=========================================="
echo "🚀 BAŞLATILIYOR - GİRİŞSİZ MOD"
echo "PORT: $PORT"
echo "=========================================="
gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 2 server:app
