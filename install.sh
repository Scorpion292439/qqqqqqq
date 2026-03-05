#!/bin/bash
# Tüm bağımlılıkları yükle

echo "📦 Python bağımlılıkları yükleniyor..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Tüm kütüphaneler yüklendi!"
echo "📊 Yüklenen paket sayısı: $(pip list | wc -l)"