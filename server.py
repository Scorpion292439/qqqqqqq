import os
import sys
import subprocess
import threading
import time
import socket
import zipfile
import shutil
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

# ========== FLASK UYGULAMASI (WASMER BUNU GÖRECEK) ==========
app = Flask(__name__)

# ========== KONFİGÜRASYON ==========
UPLOAD_FOLDER = 'uploads'
PROCESSES = {}
DEPLOYMENTS = {}
PORT = int(os.environ.get('PORT', 8080))
HOST = '0.0.0.0'

# IP adresini bul
def get_ip_address():
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        if local_ip.startswith('127.'):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('8.8.8.8', 80))
                local_ip = s.getsockname()[0]
            finally:
                s.close()
        return local_ip
    except:
        return '0.0.0.0'

HOST_IP = get_ip_address()

# Klasörleri oluştur
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'projects'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'temp'), exist_ok=True)

# ========== ROUTES ==========
@app.route('/')
def index():
    try:
        return render_template('index.html', host_ip=HOST_IP)
    except:
        return jsonify({'status': 'ok', 'message': 'Python Hosting Çalışıyor!', 'ip': HOST_IP})

@app.route('/health')
def health():
    """Wasmer için health check"""
    return jsonify({
        'status': 'healthy',
        'app': 'Python Hosting',
        'port': PORT,
        'ip': HOST_IP
    })

@app.route('/api/test')
def test():
    return jsonify({'success': True, 'message': 'API çalışıyor'})

# ========== ANA FONKSİYON ==========
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 PYTHON HOSTING - WASMER.IO")
    print("=" * 60)
    print(f"Port: {PORT}")
    print(f"IP: {HOST_IP}")
    print(f"Sunucu: http://{HOST_IP}:{PORT}")
    print("=" * 60)
    
    # Debug modu KAPALI olmalı (production için)
    app.run(host=HOST, port=PORT, debug=False)

# WASMER İÇİN: app değişkeni export edildi
application = app