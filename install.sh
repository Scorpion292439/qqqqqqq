#!/bin/bash
echo "=========================================="
echo "📦 BAĞIMLILIKLAR YÜKLENİYOR"
echo "=========================================="

# Pip'i güncelle
pip install --upgrade pip

# Ana bağımlılıkları yükle
pip install flask gunicorn psutil dnslib

# requirements.txt varsa yükle
if [ -f requirements.txt ]; then
    echo "requirements.txt bulundu, yükleniyor..."
    pip install -r requirements.txt
fi

echo "=========================================="
echo "✅ KURULUM TAMAMLANDI"
echo "=========================================="
