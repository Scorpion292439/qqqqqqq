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
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# ========== FLASK UYGULAMASI - WASMER BUNU GÖRECEK ==========
app = Flask(__name__)

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

# ========== WEB SİTESİ SAYFALARI ==========
@app.route('/')
def index():
    """Ana sayfa - herkese açık"""
    return render_template('index.html', 
                         host_ip=HOST_IP, 
                         port=PORT)

# ========== API ENDPOINTS ==========
@app.route('/health')
def health():
    """Sağlık kontrolü"""
    return jsonify({
        'status': 'healthy',
        'app': 'Python & JS Hosting',
        'version': '1.0.0',
        'port': PORT,
        'ip': HOST_IP
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
                running = project_name in DEPLOYMENTS and DEPLOYMENTS[project_name]['process'].poll() is None
                
                projects.append({
                    'id': project_name,
                    'name': project_name,
                    'running': running,
                    'port': DEPLOYMENTS[project_name]['port'] if running else None,
                    'url': f"http://{HOST_IP}:{DEPLOYMENTS[project_name]['port']}" if running else None
                })
    
    return jsonify({'success': True, 'data': projects})

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
        
        return jsonify({
            'success': True, 
            'message': f'{project_name} projesi yüklendi',
            'data': {
                'id': project_id,
                'name': project_name
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
            files = os.listdir(project_path)
            if 'app.py' in files:
                command = f'python app.py'
            elif 'manage.py' in files:
                command = f'python manage.py runserver 0.0.0.0:{port}'
            elif 'server.js' in files:
                command = f'node server.js'
            elif 'index.js' in files:
                command = f'node index.js'
            elif any(f.endswith('.py') for f in files):
                py_file = [f for f in files if f.endswith('.py')][0]
                command = f'python {py_file}'
            elif any(f.endswith('.js') for f in files):
                js_file = [f for f in files if f.endswith('.js')][0]
                command = f'node {js_file}'
            else:
                return jsonify({'success': False, 'error': 'Çalıştırılacak dosya bulunamadı'}), 400
        
        # Ortam değişkenlerini ayarla
        env = os.environ.copy()
        env['PORT'] = str(port)
        env['HOST'] = '0.0.0.0'
        
        # Process'i başlat
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=project_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        DEPLOYMENTS[project_id] = {
            'process': process,
            'port': port,
            'command': command,
            'start_time': time.time(),
            'output': []
        }
        
        # Çıktıları okumak için thread başlat
        threading.Thread(target=read_output, args=(project_id,), daemon=True).start()
        
        return jsonify({
            'success': True,
            'message': f'{project_id} başlatıldı',
            'data': {
                'port': port,
                'url': f'http://{HOST_IP}:{port}'
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
    
    if process.poll() is None:
        process.terminate()
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
        for filename in filenames[:20]:
            file_path = os.path.join(root, filename)
            rel_path = os.path.relpath(file_path, project_path)
            files.append({
                'name': rel_path,
                'size': os.path.getsize(file_path)
            })
    
    return jsonify({'success': True, 'data': files})

# ========== YARDIMCI FONKSİYONLAR ==========
def read_output(project_id):
    """Proje çıktısını oku (arka planda)"""
    if project_id not in DEPLOYMENTS:
        return
    
    process = DEPLOYMENTS[project_id]['process']
    
    while process.poll() is None:
        try:
            if process.stdout:
                line = process.stdout.readline()
                if line:
                    DEPLOYMENTS[project_id]['output'].append(line)
                    print(f"[{project_id}] {line.strip()}")
        except:
            pass
        
        if len(DEPLOYMENTS[project_id]['output']) > 500:
            DEPLOYMENTS[project_id]['output'] = DEPLOYMENTS[project_id]['output'][-500:]
        
        time.sleep(0.1)

# ========== TEMPLATES OLUŞTUR ==========
def create_template_files():
    """Template dosyalarını otomatik oluştur"""
    
    index_html = '''<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Python & JS Hosting</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', monospace; background: #0a0a0a; color: #fff; }
        .navbar { background: #1a1a1a; padding: 15px 30px; border-bottom: 3px solid #ff6b00; }
        .logo { font-size: 24px; font-weight: bold; color: #ff6b00; text-align: center; }
        .container { max-width: 1200px; margin: 30px auto; padding: 0 20px; }
        .upload-section { background: #1a1a1a; padding: 20px; margin-bottom: 30px; border-left: 4px solid #ff6b00; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #ff6b00; }
        .form-group input, .form-group select { width: 100%; padding: 10px; background: #0a0a0a; border: 1px solid #333; color: white; }
        .form-group input:focus { border-color: #ff6b00; outline: none; }
        .btn { background: #ff6b00; color: black; border: none; padding: 8px 16px; cursor: pointer; margin: 0 5px; font-weight: bold; }
        .btn:hover { background: #ff8533; }
        .projects { background: #1a1a1a; padding: 20px; }
        .project-item { display: flex; justify-content: space-between; padding: 15px; border-bottom: 1px solid #333; align-items: center; }
        .project-item:hover { background: #252525; }
        .status-badge { padding: 3px 10px; border-radius: 3px; font-size: 12px; }
        .status-running { background: #00aa00; color: white; }
        .status-stopped { background: #666; color: white; }
        .output-box { background: #0a0a0a; padding: 15px; font-family: monospace; height: 200px; overflow: auto; border: 1px solid #333; margin-top: 15px; }
        .footer { text-align: center; padding: 20px; color: #666; margin-top: 50px; }
        .stats { display: flex; gap: 20px; margin-bottom: 20px; }
        .stat-card { background: #1a1a1a; padding: 15px; flex: 1; text-align: center; border-left: 4px solid #ff6b00; }
        .stat-value { font-size: 28px; font-weight: bold; color: #ff6b00; }
    </style>
</head>
<body>
    <div class="navbar">
        <div class="logo">🚀 PYTHON & JS HOSTING</div>
    </div>
    
    <div class="container">
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="projectCount">0</div>
                <div>Toplam Proje</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="runningCount">0</div>
                <div>Çalışan Proje</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="serverIp">{{ host_ip }}</div>
                <div>Sunucu IP</div>
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
        
        <div class="projects">
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
            <div id="output" class="output-box">Konsol çıktısı burada...</div>
            
            <div style="margin-top: 15px; display: flex; gap: 10px;">
                <input type="text" id="commandInput" placeholder="komut girin..." style="flex: 1; padding: 10px; background: #0a0a0a; border: 1px solid #333; color: white;">
                <button class="btn" onclick="sendCommand()">GÖNDER</button>
            </div>
        </div>
    </div>
    
    <div class="footer">
        Python & JS Hosting | Port: {{ port }} | Herkese Açık
    </div>
    
    <script>
        let consoleInterval = null;
        
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
                        <div><strong>${p.name}</strong></div>
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
                        </div>
                    </div>
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
        
        window.stopProject = async (id) => {
            if (confirm('Projeyi durdurmak istediğinize emin misiniz?')) {
                await fetch(`/api/stop/${id}`, {method: 'POST'});
                loadProjects();
            }
        };
        
        window.deleteProject = async (id) => {
            if (confirm('Projeyi silmek istediğinize emin misiniz?')) {
                await fetch(`/api/delete/${id}`, {method: 'DELETE'});
                loadProjects();
            }
        };
        
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
        
        window.stopConsole = () => {
            if (consoleInterval) {
                clearInterval(consoleInterval);
                consoleInterval = null;
            }
        };
        
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
        
        loadProjects();
    </script>
</body>
</html>'''
    
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)

# Template'leri oluştur
create_template_files()

# ========== WASMER İÇİN ==========
application = app

# ========== BAŞLAT ==========
if __name__ == '__main__':
    print("="*60)
    print("🚀 PYTHON & JS HOSTING - GİRİŞSİZ")
    print("="*60)
    print(f"Port: {PORT}")
    print(f"IP: {HOST_IP}")
    print(f"URL: http://{HOST_IP}:{PORT}")
    print("="*60)
    print("📁 Projeler: uploads/projects/")
    print("👤 Giriş: GEREK YOK - Herkese açık")
    print("="*60)
    
    app.run(host=HOST, port=PORT, debug=False)
