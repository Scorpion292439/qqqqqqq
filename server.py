import os
import sys
import subprocess
import threading
import time
import signal
import socket
import zipfile
import shutil
import json
import uuid
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename

# ========== FLASK UYGULAMASI ==========
app = Flask(__name__)
app.secret_key = "gizli-anahtar-buraya-gelmiş-geçmiş-en-gizli-anahtar"

# ========== KONFİGÜRASYON ==========
UPLOAD_FOLDER = 'uploads'
PROCESSES = {}
DEPLOYMENTS = {}
PORT = int(os.environ.get('PORT', 8080))
HOST = '0.0.0.0'
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Klasörleri oluştur
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'projects'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'temp'), exist_ok=True)
os.makedirs('templates', exist_ok=True)
os.makedirs('static', exist_ok=True)

# IP adresini bul
def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return socket.gethostname()

HOST_IP = get_ip()

# ========== VERİTABANI BAĞLANTISI (MySQL - Wasmer Edge) ==========
DB_AVAILABLE = False
db = None

# Wasmer Edge'in otomatik verdiği environment variable'lar
DB_HOST = os.environ.get('DB_HOST')
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USERNAME')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_PORT = os.environ.get('DB_PORT', '3306')

if DB_HOST and DB_NAME and DB_USER and DB_PASSWORD:
    try:
        import pymysql
        import pymysql.cursors
        DB_AVAILABLE = True
        print("✅ MySQL veritabanı bağlantısı kuruldu")
    except ImportError:
        print("⚠️ pymysql kurulu değil, veritabanı olmadan çalışıyor")
        print("   pip install pymysql ile kurabilirsiniz")
else:
    print("ℹ️ Veritabanı environment variable'ları bulunamadı, veritabanısız modda çalışıyor")

# ========== WEB SİTESİ SAYFALARI ==========
@app.route('/')
def index():
    """Ana sayfa - web arayüzü"""
    return render_template('index.html', 
                         host_ip=HOST_IP, 
                         port=PORT,
                         db_status=DB_AVAILABLE)

@app.route('/dashboard')
def dashboard():
    """Dashboard sayfası"""
    return render_template('dashboard.html', 
                         host_ip=HOST_IP, 
                         port=PORT)

@app.route('/projects')
def projects_page():
    """Projeler sayfası"""
    return render_template('projects.html', 
                         host_ip=HOST_IP, 
                         port=PORT)

@app.route('/console')
def console_page():
    """Konsol sayfası"""
    return render_template('console.html', 
                         host_ip=HOST_IP, 
                         port=PORT)

@app.route('/settings')
def settings_page():
    """Ayarlar sayfası"""
    return render_template('settings.html', 
                         host_ip=HOST_IP, 
                         port=PORT)

# ========== STATİK DOSYALAR ==========
@app.route('/static/<path:path>')
def static_files(path):
    """Statik dosyaları serve et"""
    return send_from_directory('static', path)

# ========== API ENDPOINTS ==========
@app.route('/health')
def health():
    """Sağlık kontrolü"""
    return jsonify({
        'status': 'healthy',
        'app': 'Python & JS Hosting',
        'version': '2.0.0',
        'port': PORT,
        'ip': HOST_IP,
        'database': DB_AVAILABLE,
        'projects': len(os.listdir(os.path.join(UPLOAD_FOLDER, 'projects')))
    })

@app.route('/api/status')
def api_status():
    """API durumu"""
    return jsonify({
        'success': True,
        'data': {
            'server': 'active',
            'database': DB_AVAILABLE,
            'port': PORT,
            'ip': HOST_IP,
            'uptime': time.time() - start_time if 'start_time' in globals() else 0
        }
    })

@app.route('/api/projects')
def get_projects():
    """Tüm projeleri listele"""
    projects = []
    projects_dir = os.path.join(UPLOAD_FOLDER, 'projects')
    
    if os.path.exists(projects_dir):
        for project_name in os.listdir(projects_dir):
            project_path = os.path.join(projects_dir, project_name)
            if os.path.isdir(project_path):
                # Proje bilgilerini topla
                running = project_name in DEPLOYMENTS and DEPLOYMENTS[project_name]['process'].poll() is None
                
                project_info = {
                    'id': project_name,
                    'name': project_name,
                    'path': project_path,
                    'created': os.path.getctime(project_path),
                    'modified': os.path.getmtime(project_path),
                    'running': running,
                    'port': DEPLOYMENTS[project_name]['port'] if running else None,
                    'url': f"http://{HOST_IP}:{DEPLOYMENTS[project_name]['port']}" if running else None,
                    'command': DEPLOYMENTS[project_name]['command'] if running else None,
                    'type': get_project_type(project_path),
                    'size': get_project_size(project_path)
                }
                projects.append(project_info)
    
    return jsonify({'success': True, 'data': projects})

@app.route('/api/projects/<project_id>')
def get_project(project_id):
    """Tek bir projenin detaylarını getir"""
    project_path = os.path.join(UPLOAD_FOLDER, 'projects', secure_filename(project_id))
    
    if not os.path.exists(project_path):
        return jsonify({'success': False, 'error': 'Proje bulunamadı'}), 404
    
    running = project_id in DEPLOYMENTS and DEPLOYMENTS[project_id]['process'].poll() is None
    
    project_info = {
        'id': project_id,
        'name': project_id,
        'path': project_path,
        'created': os.path.getctime(project_path),
        'modified': os.path.getmtime(project_path),
        'running': running,
        'port': DEPLOYMENTS[project_id]['port'] if running else None,
        'url': f"http://{HOST_IP}:{DEPLOYMENTS[project_id]['port']}" if running else None,
        'command': DEPLOYMENTS[project_id]['command'] if running else None,
        'type': get_project_type(project_path),
        'files': get_project_files_list(project_path)
    }
    
    return jsonify({'success': True, 'data': project_info})

@app.route('/api/upload', methods=['POST'])
def upload_project():
    """Proje yükle (ZIP)"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Dosya yok'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Dosya seçilmedi'}), 400
    
    if not file.filename.endswith('.zip'):
        return jsonify({'success': False, 'error': 'Sadece ZIP dosyaları yüklenebilir'}), 400
    
    # Proje adını al
    project_name = request.form.get('project_name', '')
    if not project_name:
        project_name = secure_filename(file.filename.replace('.zip', ''))
    
    # Benzersiz ID oluştur
    project_id = f"{project_name}_{uuid.uuid4().hex[:8]}"
    
    # Geçici dosyayı kaydet
    temp_path = os.path.join(UPLOAD_FOLDER, 'temp', secure_filename(file.filename))
    file.save(temp_path)
    
    # Proje klasörünü oluştur
    project_path = os.path.join(UPLOAD_FOLDER, 'projects', project_id)
    os.makedirs(project_path, exist_ok=True)
    
    try:
        # ZIP'i aç
        with zipfile.ZipFile(temp_path, 'r') as zip_ref:
            zip_ref.extractall(project_path)
        
        # Geçici dosyayı sil
        os.remove(temp_path)
        
        # Veritabanına kaydet (varsa)
        if DB_AVAILABLE:
            save_project_to_db(project_id, project_name, project_path)
        
        return jsonify({
            'success': True, 
            'message': f'{project_name} projesi yüklendi',
            'data': {
                'id': project_id,
                'name': project_name,
                'path': project_path
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'ZIP açılamadı: {str(e)}'}), 500

@app.route('/api/deploy/<project_id>', methods=['POST'])
def deploy_project(project_id):
    """Projeyi başlat"""
    data = request.json or {}
    command = data.get('command', '')
    
    project_path = os.path.join(UPLOAD_FOLDER, 'projects', secure_filename(project_id))
    
    if not os.path.exists(project_path):
        return jsonify({'success': False, 'error': 'Proje bulunamadı'}), 404
    
    # Zaten çalışıyor mu kontrol et
    if project_id in DEPLOYMENTS and DEPLOYMENTS[project_id]['process'].poll() is None:
        return jsonify({'success': False, 'error': 'Proje zaten çalışıyor'}), 400
    
    try:
        # Boş port bul
        used_ports = [p['port'] for p in DEPLOYMENTS.values() if p['process'].poll() is None]
        port = 8000
        while port in used_ports:
            port += 1
        
        # Komutu hazırla
        if not command:
            command = detect_start_command(project_path, port)
        
        if not command:
            return jsonify({'success': False, 'error': 'Çalıştırılacak komut bulunamadı'}), 400
        
        # Ortam değişkenlerini ayarla
        env = os.environ.copy()
        env['PORT'] = str(port)
        env['HOST'] = '0.0.0.0'
        env['PROJECT_ID'] = project_id
        env['PROJECT_PATH'] = project_path
        
        # Process'i başlat
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=project_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            bufsize=1,
            universal_newlines=True
        )
        
        DEPLOYMENTS[project_id] = {
            'process': process,
            'port': port,
            'command': command,
            'start_time': time.time(),
            'path': project_path,
            'output': [],
            'error': []
        }
        
        # Çıktıları okumak için thread başlat
        threading.Thread(target=read_output, args=(project_id,), daemon=True).start()
        
        return jsonify({
            'success': True,
            'message': f'{project_id} başlatıldı',
            'data': {
                'port': port,
                'url': f'http://{HOST_IP}:{port}',
                'command': command
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stop/<project_id>', methods=['POST'])
def stop_project(project_id):
    """Projeyi durdur"""
    if project_id not in DEPLOYMENTS:
        return jsonify({'success': False, 'error': 'Proje çalışmıyor'}), 404
    
    process = DEPLOYMENTS[project_id]['process']
    
    # Process'i sonlandır
    if process.poll() is None:
        process.terminate()
        
        # 2 saniye bekle, hala çalışıyorsa zorla kapat
        time.sleep(2)
        if process.poll() is None:
            process.kill()
    
    del DEPLOYMENTS[project_id]
    
    return jsonify({'success': True, 'message': f'{project_id} durduruldu'})

@app.route('/api/output/<project_id>')
def get_output(project_id):
    """Proje çıktısını getir"""
    if project_id not in DEPLOYMENTS:
        return jsonify({'success': False, 'error': 'Proje çalışmıyor'}), 404
    
    return jsonify({
        'success': True,
        'data': {
            'output': ''.join(DEPLOYMENTS[project_id]['output'][-50:]),
            'running': DEPLOYMENTS[project_id]['process'].poll() is None
        }
    })

@app.route('/api/command/<project_id>', methods=['POST'])
def send_command(project_id):
    """Projeye komut gönder"""
    if project_id not in DEPLOYMENTS:
        return jsonify({'success': False, 'error': 'Proje çalışmıyor'}), 404
    
    data = request.json
    command = data.get('command', '')
    
    if not command:
        return jsonify({'success': False, 'error': 'Komut gerekli'}), 400
    
    process = DEPLOYMENTS[project_id]['process']
    
    try:
        if process.stdin:
            process.stdin.write(command + '\n')
            process.stdin.flush()
            return jsonify({'success': True})
    except:
        pass
    
    return jsonify({'success': False, 'error': 'Komut gönderilemedi'}), 400

@app.route('/api/delete/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Projeyi sil"""
    # Önce durdur
    if project_id in DEPLOYMENTS:
        stop_project(project_id)
    
    project_path = os.path.join(UPLOAD_FOLDER, 'projects', secure_filename(project_id))
    
    if os.path.exists(project_path):
        shutil.rmtree(project_path)
        return jsonify({'success': True, 'message': f'{project_id} silindi'})
    
    return jsonify({'success': False, 'error': 'Proje bulunamadı'}), 404

@app.route('/api/files/<project_id>')
def list_files(project_id):
    """Proje dosyalarını listele"""
    project_path = os.path.join(UPLOAD_FOLDER, 'projects', secure_filename(project_id))
    
    if not os.path.exists(project_path):
        return jsonify({'success': False, 'error': 'Proje bulunamadı'}), 404
    
    files = []
    for root, dirs, filenames in os.walk(project_path):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            rel_path = os.path.relpath(file_path, project_path)
            files.append({
                'name': rel_path,
                'size': os.path.getsize(file_path),
                'modified': os.path.getmtime(file_path)
            })
    
    return jsonify({'success': True, 'data': files})

# ========== YARDIMCI FONKSİYONLAR ==========
def get_project_type(project_path):
    """Proje tipini belirle"""
    files = os.listdir(project_path)
    
    if 'requirements.txt' in files:
        return 'python'
    elif 'package.json' in files:
        return 'node'
    elif any(f.endswith('.py') for f in files):
        return 'python'
    elif any(f.endswith('.js') for f in files):
        return 'node'
    else:
        return 'unknown'

def get_project_size(project_path):
    """Proje boyutunu hesapla"""
    total = 0
    for root, dirs, files in os.walk(project_path):
        for f in files:
            fp = os.path.join(root, f)
            total += os.path.getsize(fp)
    return total

def get_project_files_list(project_path, limit=20):
    """Proje dosyalarının listesini al"""
    files = []
    for root, dirs, filenames in os.walk(project_path):
        for filename in filenames[:limit]:
            file_path = os.path.join(root, filename)
            rel_path = os.path.relpath(file_path, project_path)
            files.append({
                'name': rel_path,
                'size': os.path.getsize(file_path)
            })
    return files

def detect_start_command(project_path, port):
    """Başlangıç komutunu otomatik belirle"""
    files = os.listdir(project_path)
    
    # Python projeleri
    if 'requirements.txt' in files:
        if 'manage.py' in files:
            return f'python manage.py runserver 0.0.0.0:{port}'
        elif 'app.py' in files:
            return f'python app.py'
        elif 'main.py' in files:
            return f'python main.py'
        elif 'bot.py' in files:
            return f'python bot.py'
    
    # Node.js projeleri
    if 'package.json' in files:
        if 'server.js' in files:
            return f'node server.js'
        elif 'index.js' in files:
            return f'node index.js'
        elif 'app.js' in files:
            return f'node app.js'
        else:
            return f'npm start'
    
    # Python dosyaları
    py_files = [f for f in files if f.endswith('.py')]
    if py_files:
        return f'python {py_files[0]}'
    
    # JavaScript dosyaları
    js_files = [f for f in files if f.endswith('.js')]
    if js_files:
        return f'node {js_files[0]}'
    
    return None

def save_project_to_db(project_id, project_name, project_path):
    """Projeyi veritabanına kaydet (opsiyonel)"""
    if not DB_AVAILABLE:
        return
    
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=int(DB_PORT),
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with connection:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO projects (id, name, path, created_at) 
                VALUES (%s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                path = VALUES(path)
                """
                cursor.execute(sql, (project_id, project_name, project_path))
            connection.commit()
    except Exception as e:
        print(f"Veritabanı hatası: {e}")

def read_output(project_id):
    """Proje çıktısını oku (arka planda)"""
    if project_id not in DEPLOYMENTS:
        return
    
    process = DEPLOYMENTS[project_id]['process']
    
    while process.poll() is None:
        try:
            # stdout oku
            if process.stdout:
                line = process.stdout.readline()
                if line:
                    DEPLOYMENTS[project_id]['output'].append(line)
                    print(f"[{project_id}] {line.strip()}")
            
            # stderr oku
            if process.stderr:
                line = process.stderr.readline()
                if line:
                    DEPLOYMENTS[project_id]['error'].append(line)
                    DEPLOYMENTS[project_id]['output'].append(f"ERROR: {line}")
                    
        except:
            pass
        
        # Çok fazla çıktı birikmesini engelle
        if len(DEPLOYMENTS[project_id]['output']) > 1000:
            DEPLOYMENTS[project_id]['output'] = DEPLOYMENTS[project_id]['output'][-500:]
        
        time.sleep(0.1)

# ========== TEMPLATES OLUŞTUR ==========
def create_template_files():
    """Template dosyalarını otomatik oluştur"""
    
    # index.html
    index_html = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Python & JS Hosting</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', monospace; background: #0a0a0a; color: #fff; }
        .navbar { background: #1a1a1a; padding: 15px 30px; border-bottom: 3px solid #ff6b00; display: flex; justify-content: space-between; }
        .logo { font-size: 24px; font-weight: bold; color: #ff6b00; }
        .nav-links a { color: #fff; text-decoration: none; margin-left: 20px; }
        .nav-links a:hover { color: #ff6b00; }
        .container { max-width: 1400px; margin: 30px auto; padding: 0 20px; }
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: #1a1a1a; padding: 20px; border-left: 4px solid #ff6b00; }
        .stat-value { font-size: 32px; font-weight: bold; color: #ff6b00; }
        .stat-label { color: #888; margin-top: 5px; }
        .projects { background: #1a1a1a; padding: 20px; }
        .project-item { display: flex; justify-content: space-between; padding: 15px; border-bottom: 1px solid #333; }
        .project-item:hover { background: #252525; }
        .status-badge { padding: 3px 10px; border-radius: 3px; font-size: 12px; }
        .status-running { background: #00aa00; color: white; }
        .status-stopped { background: #666; color: white; }
        .btn { background: #ff6b00; color: black; border: none; padding: 8px 16px; cursor: pointer; margin: 0 5px; }
        .btn:hover { background: #ff8533; }
        .upload-section { background: #1a1a1a; padding: 20px; margin-top: 30px; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #ff6b00; }
        .form-group input, .form-group select { width: 100%; padding: 10px; background: #0a0a0a; border: 1px solid #333; color: white; }
        .form-group input:focus { border-color: #ff6b00; outline: none; }
        .output-box { background: #0a0a0a; padding: 15px; font-family: monospace; height: 200px; overflow: auto; border: 1px solid #333; }
        .footer { text-align: center; padding: 20px; color: #666; margin-top: 50px; }
    </style>
</head>
<body>
    <div class="navbar">
        <div class="logo">🚀 PYTHON & JS HOSTING</div>
        <div class="nav-links">
            <a href="/">Ana Sayfa</a>
            <a href="/projects">Projeler</a>
            <a href="/console">Konsol</a>
            <a href="/settings">Ayarlar</a>
        </div>
    </div>
    
    <div class="container">
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="projectCount">0</div>
                <div class="stat-label">Toplam Proje</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="runningCount">0</div>
                <div class="stat-label">Çalışan Proje</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="freePort">8000</div>
                <div class="stat-label">Boş Port</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="serverIp">{{ host_ip }}</div>
                <div class="stat-label">Sunucu IP</div>
            </div>
        </div>
        
        <div class="upload-section">
            <h2>📦 Yeni Proje Yükle</h2>
            <form id="uploadForm" enctype="multipart/form-data">
                <div class="form-group">
                    <label>Proje Adı</label>
                    <input type="text" id="projectName" placeholder="proje-adi">
                </div>
                <div class="form-group">
                    <label>ZIP Dosyası</label>
                    <input type="file" id="zipFile" accept=".zip">
                </div>
                <button type="submit" class="btn">YÜKLE</button>
            </form>
        </div>
        
        <div class="projects" style="margin-top: 30px;">
            <h2>📋 Projeler</h2>
            <div id="projectsList"></div>
        </div>
        
        <div class="upload-section" style="margin-top: 30px;">
            <h2>📟 Canlı Konsol</h2>
            <div class="form-group">
                <select id="projectSelect">
                    <option value="">Proje Seçin</option>
                </select>
            </div>
            <button class="btn" onclick="startConsole()">Konsolu Başlat</button>
            <button class="btn" onclick="stopConsole()">Durdur</button>
            <div id="output" class="output-box" style="margin-top: 15px;">Konsol çıktısı burada görünecek...</div>
            
            <div style="margin-top: 15px; display: flex; gap: 10px;">
                <input type="text" id="commandInput" placeholder="komut girin..." style="flex: 1; padding: 10px; background: #0a0a0a; border: 1px solid #333; color: white;">
                <button class="btn" onclick="sendCommand()">GÖNDER</button>
            </div>
        </div>
    </div>
    
    <div class="footer">
        Python & JS Hosting v2.0 | Port: {{ port }} | Database: {{ '✅ Aktif' if db_status else '❌ Pasif' }}
    </div>
    
    <script>
        const API = '';
        let consoleInterval = null;
        
        // İstatistikleri güncelle
        async function loadStats() {
            const res = await fetch('/api/status');
            const data = await res.json();
            if (data.success) {
                document.getElementById('freePort').innerText = data.data.port + 1;
            }
        }
        
        // Projeleri yükle
        async function loadProjects() {
            const res = await fetch('/api/projects');
            const data = await res.json();
            
            if (!data.success) return;
            
            const projects = data.data;
            let html = '';
            let selectHtml = '<option value="">Proje Seçin</option>';
            let running = 0;
            
            projects.forEach(p => {
                if (p.running) running++;
                
                html += `
                    <div class="project-item">
                        <div>
                            <strong>${p.name}</strong><br>
                            <small>${p.type || 'unknown'} | ${new Date(p.created * 1000).toLocaleString()}</small>
                        </div>
                        <div>
                            <span class="status-badge ${p.running ? 'status-running' : 'status-stopped'}">
                                ${p.running ? 'ÇALIŞIYOR' : 'DURDU'}
                            </span>
                            ${p.running ? `<small style="margin-left: 10px;">Port: ${p.port}</small>` : ''}
                        </div>
                        <div>
                            ${!p.running ? 
                                `<button class="btn" onclick="deployProject('${p.id}')">BAŞLAT</button>` : 
                                `<button class="btn" onclick="stopProject('${p.id}')">DURDUR</button>`
                            }
                            <button class="btn" onclick="deleteProject('${p.id}')">SİL</button>
                            <button class="btn" onclick="showFiles('${p.id}')">DOSYALAR</button>
                        </div>
                    </div>
                    <div id="files-${p.id}" style="display: none; background: #0a0a0a; padding: 10px;"></div>
                `;
                
                if (p.running) {
                    selectHtml += `<option value="${p.id}">${p.name} (port ${p.port})</option>`;
                }
            });
            
            document.getElementById('projectsList').innerHTML = html || '<div style="padding: 20px; text-align: center;">Henüz proje yok</div>';
            document.getElementById('projectSelect').innerHTML = selectHtml;
            document.getElementById('projectCount').innerText = projects.length;
            document.getElementById('runningCount').innerText = running;
        }
        
        // Proje başlat
        window.deployProject = async (id) => {
            const cmd = prompt('Başlangıç komutu (boş bırak otomatik):');
            const res = await fetch(`/api/deploy/${id}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command: cmd})
            });
            const data = await res.json();
            alert(data.message || data.error);
            loadProjects();
        };
        
        // Proje durdur
        window.stopProject = async (id) => {
            if (confirm('Projeyi durdurmak istediğinize emin misiniz?')) {
                await fetch(`/api/stop/${id}`, {method: 'POST'});
                loadProjects();
                if (consoleInterval) stopConsole();
            }
        };
        
        // Proje sil
        window.deleteProject = async (id) => {
            if (confirm('Projeyi silmek istediğinize emin misiniz? Tüm dosyalar silinecek!')) {
                await fetch(`/api/delete/${id}`, {method: 'DELETE'});
                loadProjects();
                if (consoleInterval) stopConsole();
            }
        };
        
        // Dosyaları göster
        window.showFiles = async (id) => {
            const div = document.getElementById(`files-${id}`);
            if (div.style.display === 'none') {
                const res = await fetch(`/api/files/${id}`);
                const data = await res.json();
                if (data.success) {
                    div.innerHTML = '<h4>Dosyalar:</h4>' + data.data.map(f => 
                        `<div>📄 ${f.name} (${(f.size/1024).toFixed(2)} KB)</div>`
                    ).join('');
                    div.style.display = 'block';
                }
            } else {
                div.style.display = 'none';
            }
        };
        
        // Konsol başlat
        window.startConsole = () => {
            const project = document.getElementById('projectSelect').value;
            if (!project) return alert('Proje seçin');
            
            if (consoleInterval) clearInterval(consoleInterval);
            
            const getOutput = async () => {
                const res = await fetch(`/api/output/${project}`);
                const data = await res.json();
                if (data.success) {
                    document.getElementById('output').innerText = data.data.output;
                }
            };
            
            getOutput();
            consoleInterval = setInterval(getOutput, 2000);
        };
        
        // Konsol durdur
        window.stopConsole = () => {
            if (consoleInterval) {
                clearInterval(consoleInterval);
                consoleInterval = null;
            }
        };
        
        // Komut gönder
        window.sendCommand = async () => {
            const project = document.getElementById('projectSelect').value;
            const cmd = document.getElementById('commandInput').value;
            if (!project || !cmd) return;
            
            await fetch(`/api/command/${project}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command: cmd})
            });
            document.getElementById('commandInput').value = '';
        };
        
        // Yükleme formu
        document.getElementById('uploadForm').onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData();
            formData.append('file', document.getElementById('zipFile').files[0]);
            formData.append('project_name', document.getElementById('projectName').value);
            
            const res = await fetch('/api/upload', {method: 'POST', body: formData});
            const data = await res.json();
            alert(data.message || data.error);
            loadProjects();
        };
        
        // Sayfa açılınca yükle
        loadStats();
        loadProjects();
        setInterval(loadStats, 5000);
    </script>
</body>
</html>'''
    
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    # Diğer template'ler
    with open('templates/dashboard.html', 'w') as f:
        f.write('{% extends "index.html" %}{% block content %}Dashboard{% endblock %}')
    
    with open('templates/projects.html', 'w') as f:
        f.write('{% extends "index.html" %}{% block content %}Projects{% endblock %}')
    
    with open('templates/console.html', 'w') as f:
        f.write('{% extends "index.html" %}{% block content %}Console{% endblock %}')
    
    with open('templates/settings.html', 'w') as f:
        f.write('{% extends "index.html" %}{% block content %}Settings{% endblock %}')

# Template'leri oluştur
create_template_files()

# ========== WASMER İÇİN ==========
# Bu satır WASMER'IN GÖRMESİ İÇİN ÇOK ÖNEMLİ
application = app

# Başlangıç zamanı
start_time = time.time()

# ========== ANA FONKSİYON ==========
if __name__ == '__main__':
    print("="*70)
    print("🚀 PYTHON & JS HOSTING - TAM WEB SİTESİ")
    print("="*70)
    print(f"Port: {PORT}")
    print(f"IP: {HOST_IP}")
    print(f"URL: http://{HOST_IP}:{PORT}")
    print(f"Database: {'✅ Aktif' if DB_AVAILABLE else '❌ Pasif'}")
    print("="*70)
    print("Projeler klasörü:", os.path.join(UPLOAD_FOLDER, 'projects'))
    print("Template'ler:", os.path.abspath('templates'))
    print("="*70)
    
    app.run(host=HOST, port=PORT, debug=False)
