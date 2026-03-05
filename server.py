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
from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename

# ========== FLASK UYGULAMASI ==========
app = Flask(__name__)
app.secret_key = "gizli-anahtar-buraya"

# ========== KONFİGÜRASYON ==========
UPLOAD_FOLDER = 'uploads'
PROCESSES = {}
DEPLOYMENTS = {}
PORT = int(os.environ.get('PORT', 8080))
HOST = '0.0.0.0'

# Klasörleri oluştur
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'projects'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'temp'), exist_ok=True)

# IP adresini bul
def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return 'wasmer.io'

HOST_IP = get_ip()

# ========== ANA SAYFA ==========
@app.route('/')
def index():
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Python Hosting</title>
        <style>
            body {{ font-family: Arial; background: #1a1a1a; color: white; padding: 20px; }}
            .container {{ max-width: 800px; margin: 0 auto; background: #2d2d2d; padding: 30px; border-radius: 5px; border-left: 5px solid #ff6b00; }}
            h1 {{ color: #ff6b00; }}
            .status {{ color: #0f0; }}
            .endpoint {{ background: #000; padding: 10px; margin: 5px 0; font-family: monospace; color: #0f0; }}
            button {{ background: #ff6b00; color: black; border: none; padding: 10px 20px; cursor: pointer; margin: 5px; }}
            input, textarea {{ width: 100%; padding: 10px; margin: 5px 0; background: #000; color: #0f0; border: 1px solid #ff6b00; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 PYTHON HOSTING</h1>
            <p class="status">✅ SİSTEM AKTİF</p>
            <p>IP: {HOST_IP}</p>
            <p>PORT: {PORT}</p>
            <hr>
            
            <h2>📦 YENİ PROJE YÜKLE</h2>
            <form id="uploadForm" enctype="multipart/form-data">
                <input type="text" id="projectName" placeholder="Proje Adı">
                <input type="file" id="zipFile" accept=".zip">
                <button type="submit">YÜKLE</button>
            </form>
            
            <h2>📋 PROJELER</h2>
            <div id="projects"></div>
            
            <h2>📟 CANLI ÇIKTI</h2>
            <select id="projectSelect"></select>
            <button onclick="startOutput()">İZLE</button>
            <pre id="output" style="background: #000; color: #0f0; padding: 10px; height: 200px; overflow: auto;"></pre>
            
            <h2>📨 KOMUT GÖNDER</h2>
            <input type="text" id="commandInput" placeholder="komut girin">
            <button onclick="sendCommand()">GÖNDER</button>
        </div>
        
        <script>
            const API = '';
            
            // Projeleri yükle
            async function loadProjects() {{
                const res = await fetch('/api/projects');
                const projects = await res.json();
                
                let html = '';
                const select = document.getElementById('projectSelect');
                select.innerHTML = '<option value="">Seçiniz</option>';
                
                projects.forEach(p => {{
                    const status = p.running ? '🟢 ÇALIŞIYOR' : '⚪ DURDU';
                    html += `<div style="border:1px solid #ff6b00; padding:10px; margin:5px;">
                        <b>${{p.name}}</b> - ${{status}}<br>
                        <button onclick="deploy('${{p.name}}')">BAŞLAT</button>
                        <button onclick="stop('${{p.name}}')">DURDUR</button>
                        <button onclick="del('${{p.name}}')">SİL</button>
                        <button onclick="files('${{p.name}}')">DOSYALAR</button>
                        <div id="files-${{p.name}}" style="display:none; background:#000; padding:5px; margin-top:5px;"></div>
                    </div>`;
                    
                    if (p.running) {{
                        select.innerHTML += `<option value="${{p.name}}">${{p.name}} (port ${{p.port}})</option>`;
                    }}
                }});
                
                document.getElementById('projects').innerHTML = html;
            }}
            
            // Proje başlat
            window.deploy = async (name) => {{
                const cmd = prompt('Başlangıç komutu (boş bırak otomatik):');
                const res = await fetch(`/api/deploy/${{name}}`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{command: cmd}})
                }});
                const data = await res.json();
                alert(data.message || data.error);
                loadProjects();
            }};
            
            // Proje durdur
            window.stop = async (name) => {{
                await fetch(`/api/stop/${{name}}`, {{method: 'POST'}});
                loadProjects();
            }};
            
            // Proje sil
            window.del = async (name) => {{
                if(confirm('SİL?')) {{
                    await fetch(`/api/delete/${{name}}`, {{method: 'DELETE'}});
                    loadProjects();
                }}
            }};
            
            // Dosya listele
            window.files = async (name) => {{
                const div = document.getElementById(`files-${{name}}`);
                if(div.style.display === 'none') {{
                    const res = await fetch(`/api/files/${{name}}`);
                    const files = await res.json();
                    div.innerHTML = files.map(f => `📄 ${{f.name}} (${{(f.size/1024).toFixed(1)} KB)`).join('<br>');
                    div.style.display = 'block';
                }} else {{
                    div.style.display = 'none';
                }}
            }};
            
            // Yükleme formu
            document.getElementById('uploadForm').onsubmit = async (e) => {{
                e.preventDefault();
                const formData = new FormData();
                formData.append('file', document.getElementById('zipFile').files[0]);
                formData.append('project_name', document.getElementById('projectName').value);
                
                const res = await fetch('/api/upload', {{method: 'POST', body: formData}});
                const data = await res.json();
                alert(data.message || data.error);
                loadProjects();
            }};
            
            // Çıktı izle
            let interval;
            window.startOutput = () => {{
                const project = document.getElementById('projectSelect').value;
                if(!project) return;
                
                if(interval) clearInterval(interval);
                
                const getOutput = async () => {{
                    const res = await fetch(`/api/output/${{project}}`);
                    const data = await res.json();
                    document.getElementById('output').innerText = data.stdout;
                }};
                
                getOutput();
                interval = setInterval(getOutput, 2000);
            }};
            
            // Komut gönder
            window.sendCommand = async () => {{
                const project = document.getElementById('projectSelect').value;
                const cmd = document.getElementById('commandInput').value;
                if(!project || !cmd) return;
                
                await fetch(`/api/command/${{project}}`, {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{command: cmd}})
                }});
                document.getElementById('commandInput').value = '';
            }};
            
            // Sayfa açılınca yükle
            loadProjects();
        </script>
    </body>
    </html>
    '''

# ========== API ENDPOINTS ==========
@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'port': PORT})

@app.route('/api/projects')
def get_projects():
    projects = []
    dirs = os.listdir(os.path.join(UPLOAD_FOLDER, 'projects'))
    for d in dirs:
        path = os.path.join(UPLOAD_FOLDER, 'projects', d)
        if os.path.isdir(path):
            projects.append({
                'name': d,
                'running': d in DEPLOYMENTS and DEPLOYMENTS[d]['process'].poll() is None,
                'port': DEPLOYMENTS[d]['port'] if d in DEPLOYMENTS else None,
                'command': DEPLOYMENTS[d]['command'] if d in DEPLOYMENTS else None
            })
    return jsonify(projects)

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'Dosya yok'}), 400
    
    file = request.files['file']
    name = request.form.get('project_name', '') or file.filename.replace('.zip', '')
    
    temp = os.path.join(UPLOAD_FOLDER, 'temp', file.filename)
    file.save(temp)
    
    target = os.path.join(UPLOAD_FOLDER, 'projects', name)
    os.makedirs(target, exist_ok=True)
    
    with zipfile.ZipFile(temp, 'r') as z:
        z.extractall(target)
    
    os.remove(temp)
    return jsonify({'success': True, 'message': f'{name} yüklendi'})

@app.route('/api/deploy/<name>', methods=['POST'])
def deploy(name):
    data = request.json
    cmd = data.get('command', '')
    
    path = os.path.join(UPLOAD_FOLDER, 'projects', name)
    if not os.path.exists(path):
        return jsonify({'error': 'Proje yok'}), 404
    
    if name in DEPLOYMENTS:
        return jsonify({'error': 'Zaten çalışıyor'}), 400
    
    # Port bul
    port = 8000
    used = [d['port'] for d in DEPLOYMENTS.values()]
    while port in used:
        port += 1
    
    # Komut yoksa otomatik bul
    if not cmd:
        files = os.listdir(path)
        if 'app.py' in files:
            cmd = f'python app.py'
        elif 'manage.py' in files:
            cmd = f'python manage.py runserver 0.0.0.0:{port}'
        elif 'server.js' in files:
            cmd = f'node server.js'
        elif any(f.endswith('.py') for f in files):
            py = [f for f in files if f.endswith('.py')][0]
            cmd = f'python {py}'
        else:
            cmd = f'python -m http.server {port}'
    
    # Çalıştır
    env = os.environ.copy()
    env['PORT'] = str(port)
    
    proc = subprocess.Popen(
        cmd, shell=True, cwd=path,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    
    DEPLOYMENTS[name] = {
        'process': proc,
        'port': port,
        'command': cmd,
        'output': []
    }
    
    return jsonify({
        'success': True,
        'message': f'{name} başladı',
        'port': port,
        'url': f'http://{HOST_IP}:{port}'
    })

@app.route('/api/stop/<name>', methods=['POST'])
def stop(name):
    if name not in DEPLOYMENTS:
        return jsonify({'error': 'Çalışmıyor'}), 404
    
    DEPLOYMENTS[name]['process'].terminate()
    time.sleep(1)
    if DEPLOYMENTS[name]['process'].poll() is None:
        DEPLOYMENTS[name]['process'].kill()
    
    del DEPLOYMENTS[name]
    return jsonify({'success': True})

@app.route('/api/delete/<name>', methods=['DELETE'])
def delete(name):
    if name in DEPLOYMENTS:
        DEPLOYMENTS[name]['process'].kill()
        del DEPLOYMENTS[name]
    
    path = os.path.join(UPLOAD_FOLDER, 'projects', name)
    if os.path.exists(path):
        shutil.rmtree(path)
    
    return jsonify({'success': True})

@app.route('/api/output/<name>')
def output(name):
    if name not in DEPLOYMENTS:
        return jsonify({'stdout': 'Proje çalışmıyor'})
    
    proc = DEPLOYMENTS[name]['process']
    
    try:
        line = proc.stdout.readline()
        if line:
            DEPLOYMENTS[name]['output'].append(line)
    except:
        pass
    
    if len(DEPLOYMENTS[name]['output']) > 50:
        DEPLOYMENTS[name]['output'] = DEPLOYMENTS[name]['output'][-50:]
    
    return jsonify({
        'stdout': ''.join(DEPLOYMENTS[name]['output']),
        'running': proc.poll() is None
    })

@app.route('/api/command/<name>', methods=['POST'])
def command(name):
    if name not in DEPLOYMENTS:
        return jsonify({'error': 'Çalışmıyor'}), 404
    
    data = request.json
    cmd = data.get('command', '')
    
    if DEPLOYMENTS[name]['process'].stdin:
        DEPLOYMENTS[name]['process'].stdin.write(cmd + '\n')
        DEPLOYMENTS[name]['process'].stdin.flush()
        return jsonify({'success': True})
    
    return jsonify({'error': 'Stdin yok'}), 400

@app.route('/api/files/<name>')
def files(name):
    path = os.path.join(UPLOAD_FOLDER, 'projects', name)
    if not os.path.exists(path):
        return jsonify([])
    
    files = []
    for root, dirs, filenames in os.walk(path):
        for f in filenames[:20]:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, path)
            files.append({'name': rel, 'size': os.path.getsize(full)})
    
    return jsonify(files)

# ========== WASMER İÇİN ==========
application = app

# ========== BAŞLAT ==========
if __name__ == '__main__':
    print('='*50)
    print('🚀 PYTHON HOSTING BAŞLIYOR')
    print('='*50)
    print(f'PORT: {PORT}')
    print(f'IP: {HOST_IP}')
    print('='*50)
    app.run(host=HOST, port=PORT, debug=False)
