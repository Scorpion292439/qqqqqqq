// ========== FIREBASE KONFİGÜRASYONU ==========
const firebaseConfig = {
    apiKey: "AIzaSyAo_b_U0xWD-Lb2A-nhRtE6CBz0q0HUnq4",
    authDomain: "your-project.firebaseapp.com",  // BUNLARI KENDİ BİLGİLERİNİZLE DEĞİŞTİRİN
    projectId: "your-project-id",
    storageBucket: "your-project.appspot.com",
    messagingSenderId: "123456789",
    appId: "1:123:web:abc"
};

// Firebase'i başlat
firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();
const db = firebase.firestore();

// ========== GLOBAL DEĞİŞKENLER ==========
let currentUser = null;
let currentProject = null;
let currentOutputInterval = null;
let projectsListeners = [];

// ========== AUTH FONKSİYONLARI ==========

// Giriş yap
window.handleLogin = function() {
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const errorDiv = document.getElementById('loginError');
    
    errorDiv.classList.remove('show');
    
    if (!email || !password) {
        errorDiv.textContent = 'E-posta ve şifre gerekli';
        errorDiv.classList.add('show');
        return;
    }
    
    auth.signInWithEmailAndPassword(email, password)
        .then(() => {
            // Başarılı giriş
            document.getElementById('loginEmail').value = '';
            document.getElementById('loginPassword').value = '';
            closeAllModals();
        })
        .catch((error) => {
            let message = 'Giriş başarısız';
            switch(error.code) {
                case 'auth/user-not-found':
                    message = 'Bu e-posta ile kayıtlı kullanıcı bulunamadı';
                    break;
                case 'auth/wrong-password':
                    message = 'Şifre yanlış';
                    break;
                case 'auth/invalid-email':
                    message = 'Geçersiz e-posta formatı';
                    break;
                case 'auth/user-disabled':
                    message = 'Bu hesap devre dışı bırakılmış';
                    break;
                default:
                    message = 'Giriş yapılamadı. Lütfen tekrar deneyin';
            }
            errorDiv.textContent = message;
            errorDiv.classList.add('show');
        });
};

// Kayıt ol
window.handleRegister = function() {
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    const confirm = document.getElementById('registerPasswordConfirm').value;
    const errorDiv = document.getElementById('registerError');
    const successDiv = document.getElementById('registerSuccess');
    
    errorDiv.classList.remove('show');
    successDiv.classList.remove('show');
    
    if (!email || !password || !confirm) {
        errorDiv.textContent = 'Tüm alanları doldurun';
        errorDiv.classList.add('show');
        return;
    }
    
    if (password.length < 6) {
        errorDiv.textContent = 'Şifre en az 6 karakter olmalı';
        errorDiv.classList.add('show');
        return;
    }
    
    if (password !== confirm) {
        errorDiv.textContent = 'Şifreler eşleşmiyor';
        errorDiv.classList.add('show');
        return;
    }
    
    auth.createUserWithEmailAndPassword(email, password)
        .then(() => {
            successDiv.textContent = 'Kayıt başarılı! Yönlendiriliyorsunuz...';
            successDiv.classList.add('show');
            
            // Formu temizle
            document.getElementById('registerEmail').value = '';
            document.getElementById('registerPassword').value = '';
            document.getElementById('registerPasswordConfirm').value = '';
            
            // 2 saniye sonra modal'ı kapat
            setTimeout(() => {
                closeAllModals();
            }, 2000);
        })
        .catch((error) => {
            let message = 'Kayıt başarısız';
            switch(error.code) {
                case 'auth/email-already-in-use':
                    message = 'Bu e-posta zaten kayıtlı';
                    break;
                case 'auth/invalid-email':
                    message = 'Geçersiz e-posta formatı';
                    break;
                case 'auth/operation-not-allowed':
                    message = 'Kayıt şu anda kapalı';
                    break;
                case 'auth/weak-password':
                    message = 'Şifre çok zayıf';
                    break;
                default:
                    message = 'Kayıt olunamadı. Lütfen tekrar deneyin';
            }
            errorDiv.textContent = message;
            errorDiv.classList.add('show');
        });
};

// Şifre sıfırlama
window.handleResetPassword = function() {
    const email = document.getElementById('resetEmail').value;
    const errorDiv = document.getElementById('resetError');
    const successDiv = document.getElementById('resetSuccess');
    
    errorDiv.classList.remove('show');
    successDiv.classList.remove('show');
    
    if (!email) {
        errorDiv.textContent = 'E-posta adresinizi girin';
        errorDiv.classList.add('show');
        return;
    }
    
    auth.sendPasswordResetEmail(email)
        .then(() => {
            successDiv.textContent = 'Şifre sıfırlama bağlantısı e-postanıza gönderildi';
            successDiv.classList.add('show');
            document.getElementById('resetEmail').value = '';
            
            // 3 saniye sonra login modal'ına dön
            setTimeout(() => {
                showLogin();
            }, 3000);
        })
        .catch((error) => {
            let message = 'İşlem başarısız';
            switch(error.code) {
                case 'auth/user-not-found':
                    message = 'Bu e-posta ile kayıtlı kullanıcı bulunamadı';
                    break;
                case 'auth/invalid-email':
                    message = 'Geçersiz e-posta formatı';
                    break;
                default:
                    message = 'Şifre sıfırlama e-postası gönderilemedi';
            }
            errorDiv.textContent = message;
            errorDiv.classList.add('show');
        });
};

// Çıkış yap
window.handleLogout = function() {
    auth.signOut();
};

// Modal göster/gizle fonksiyonları
window.showLogin = function() {
    document.getElementById('loginModal').classList.add('active');
    document.getElementById('registerModal').classList.remove('active');
    document.getElementById('resetModal').classList.remove('active');
    
    // Hata mesajlarını temizle
    document.getElementById('loginError').classList.remove('show');
    document.getElementById('loginEmail').value = '';
    document.getElementById('loginPassword').value = '';
};

window.showRegister = function() {
    document.getElementById('loginModal').classList.remove('active');
    document.getElementById('registerModal').classList.add('active');
    document.getElementById('resetModal').classList.remove('active');
    
    // Hata mesajlarını temizle
    document.getElementById('registerError').classList.remove('show');
    document.getElementById('registerSuccess').classList.remove('show');
    document.getElementById('registerEmail').value = '';
    document.getElementById('registerPassword').value = '';
    document.getElementById('registerPasswordConfirm').value = '';
};

window.showResetPassword = function() {
    document.getElementById('loginModal').classList.remove('active');
    document.getElementById('registerModal').classList.remove('active');
    document.getElementById('resetModal').classList.add('active');
    
    // Hata mesajlarını temizle
    document.getElementById('resetError').classList.remove('show');
    document.getElementById('resetSuccess').classList.remove('show');
    document.getElementById('resetEmail').value = '';
};

function closeAllModals() {
    document.getElementById('loginModal').classList.remove('active');
    document.getElementById('registerModal').classList.remove('active');
    document.getElementById('resetModal').classList.remove('active');
}

// ========== AUTH DURUM DİNLEYİCİSİ ==========
auth.onAuthStateChanged(async (user) => {
    if (user) {
        console.log("✅ Kullanıcı giriş yaptı:", user.email);
        currentUser = user;
        
        // UI'ı güncelle
        document.getElementById('userSection').style.display = 'block';
        document.getElementById('userEmail').textContent = user.email;
        document.getElementById('loginPrompt').style.display = 'none';
        document.getElementById('protectedContent').classList.add('visible');
        
        // Modal'ları kapat
        closeAllModals();
        
        // Kullanıcının projelerini yükle
        await loadProjectsFromServer();
        
    } else {
        console.log("🚪 Kullanıcı çıkış yaptı");
        currentUser = null;
        
        // UI'ı güncelle
        document.getElementById('userSection').style.display = 'none';
        document.getElementById('loginPrompt').style.display = 'block';
        document.getElementById('protectedContent').classList.remove('visible');
        
        // Proje listesini temizle
        document.getElementById('projectsContainer').innerHTML = '';
        document.getElementById('outputSelector').innerHTML = '<option value="">Proje seç</option>';
        
        // Çıktı izlemeyi durdur
        if (currentOutputInterval) {
            clearInterval(currentOutputInterval);
            currentOutputInterval = null;
        }
        
        // Login modalını göster
        setTimeout(() => showLogin(), 500);
    }
});

// ========== PROJE İŞLEMLERİ ==========

// Sunucudan projeleri yükle
async function loadProjectsFromServer() {
    if (!currentUser) return;
    
    try {
        const res = await fetch('/api/projects');
        const projects = await res.json();
        
        displayProjects(projects);
        updateOutputSelector(projects);
    } catch (error) {
        showAlert('Projeler yüklenemedi', 'error');
    }
}

// Projeleri ekranda göster
function displayProjects(projects) {
    const container = document.getElementById('projectsContainer');
    
    if (projects.length === 0) {
        container.innerHTML = '<div class="empty-message">📭 Henüz proje yok. Yukarıdan ZIP yükleyin.</div>';
        return;
    }

    let html = '<div class="projects-grid">';
    
    projects.forEach(p => {
        const created = new Date(p.created * 1000).toLocaleString('tr-TR');
        const running = p.running;
        const url = running ? `http://${HOST_IP}:${p.port}` : '#';
        
        html += `
            <div class="project-card" id="project-${p.name}">
                <div class="project-header">
                    <span class="project-name">📁 ${p.name}</span>
                    <span class="project-badge ${running ? 'badge-running' : 'badge-stopped'}">
                        ${running ? '🟢 ÇALIŞIYOR' : '⚪ DURDU'}
                    </span>
                </div>
                <div class="project-body">
                    <div class="project-info">
                        <div class="info-row">
                            <span class="info-label">Tip:</span>
                            <span class="info-value">${p.type}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Yüklenme:</span>
                            <span class="info-value">${created}</span>
                        </div>
                        ${running ? `
                        <div class="info-row">
                            <span class="info-label">Port:</span>
                            <span class="info-value">🔌 ${p.port}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">URL:</span>
                            <span class="info-value">
                                <a href="${url}" target="_blank" class="project-url">🌐 ${url}</a>
                            </span>
                        </div>
                        ` : ''}
                        ${p.command ? `
                        <div class="info-row">
                            <span class="info-label">Komut:</span>
                            <span class="info-value">⚙️ ${p.command}</span>
                        </div>
                        ` : ''}
                    </div>
                    
                    ${!running ? `
                    <div class="command-input">
                        <input type="text" id="cmd-${p.name}" placeholder="Başlangıç komutu (örn: python bot.py)" value="${p.command || ''}">
                    </div>
                    ` : ''}
                    
                    <div class="project-actions">
                        ${!running ? 
                            `<button class="btn-small btn-success" onclick="deployProject('${p.name}')">▶ Başlat</button>` :
                            `<button class="btn-small btn-danger" onclick="stopProject('${p.name}')">⏹ Durdur</button>`
                        }
                        <button class="btn-small" onclick="showProjectFiles('${p.name}')">📁 Dosyalar</button>
                        <button class="btn-small btn-danger" onclick="deleteProject('${p.name}')">🗑 Sil</button>
                        ${running ? `<button class="btn-small btn-warning" onclick="selectProjectForOutput('${p.name}')">📟 Çıktıyı İzle</button>` : ''}
                    </div>
                    
                    <div id="files-${p.name}" class="files-list" style="display: none;"></div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// Output selector'ı güncelle
function updateOutputSelector(projects) {
    const select = document.getElementById('outputSelector');
    let options = '<option value="">📟 Proje seç</option>';
    
    projects.forEach(p => {
        if (p.running) {
            options += `<option value="${p.name}" ${currentProject === p.name ? 'selected' : ''}>${p.name} (port ${p.port})</option>`;
        }
    });
    
    select.innerHTML = options;
}

// Proje başlat
window.deployProject = async function(projectName) {
    if (!currentUser) return;
    
    const cmdInput = document.getElementById(`cmd-${projectName}`);
    const command = cmdInput ? cmdInput.value : '';
    
    try {
        const res = await fetch(`/api/deploy/${projectName}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: command })
        });
        
        const data = await res.json();
        
        if (data.success) {
            showAlert(`✅ ${projectName} başlatıldı: ${data.url}`, 'success');
            await loadProjectsFromServer();
            
            // Çıktıyı otomatik izlemeye başla
            setTimeout(() => {
                selectProjectForOutput(projectName);
            }, 1000);
        } else {
            showAlert(data.error || 'Hata oluştu', 'error');
        }
    } catch (error) {
        showAlert('Proje başlatılamadı', 'error');
    }
};

// Proje durdur
window.stopProject = async function(projectName) {
    if (!currentUser) return;
    
    try {
        const res = await fetch(`/api/stop-project/${projectName}`, { method: 'POST' });
        const data = await res.json();
        
        if (data.success) {
            showAlert(`⏹️ ${projectName} durduruldu`, 'success');
            
            if (currentProject === projectName) {
                stopOutputMonitoring();
            }
            
            await loadProjectsFromServer();
        } else {
            showAlert(data.error || 'Hata oluştu', 'error');
        }
    } catch (error) {
        showAlert('Proje durdurulamadı', 'error');
    }
};

// Proje sil
window.deleteProject = async function(projectName) {
    if (!currentUser) return;
    if (!confirm(`⚠️ ${projectName} projesi silinecek. Emin misiniz?`)) return;
    
    try {
        const res = await fetch(`/api/delete-project/${projectName}`, { method: 'DELETE' });
        const data = await res.json();
        
        if (data.success) {
            showAlert(`🗑️ ${projectName} silindi`, 'success');
            
            if (currentProject === projectName) {
                stopOutputMonitoring();
            }
            
            await loadProjectsFromServer();
        } else {
            showAlert(data.error || 'Hata oluştu', 'error');
        }
    } catch (error) {
        showAlert('Proje silinemedi', 'error');
    }
};

// Proje dosyalarını göster
window.showProjectFiles = async function(projectName) {
    if (!currentUser) return;
    
    const filesDiv = document.getElementById(`files-${projectName}`);
    
    if (filesDiv.style.display === 'none') {
        try {
            const res = await fetch(`/api/project-files/${projectName}`);
            const files = await res.json();
            
            let html = '<div style="margin-top:5px;"><strong>📄 Dosyalar:</strong></div>';
            files.slice(0, 10).forEach(f => {
                html += `<div class="file-item">📄 ${f.name} (${(f.size/1024).toFixed(1)} KB)</div>`;
            });
            if (files.length > 10) {
                html += `<div class="file-item">... ve ${files.length-10} dosya daha</div>`;
            }
            
            filesDiv.innerHTML = html;
            filesDiv.style.display = 'block';
        } catch (error) {
            showAlert('Dosyalar yüklenemedi', 'error');
        }
    } else {
        filesDiv.style.display = 'none';
    }
};

// Proje seç ve çıktıyı izlemeye başla
window.selectProjectForOutput = function(projectName) {
    document.getElementById('outputSelector').value = projectName;
    startOutputMonitoring(projectName);
};

// Çıktı izlemeyi başlat
function startOutputMonitoring(projectName) {
    if (!currentUser) return;
    
    if (currentOutputInterval) {
        clearInterval(currentOutputInterval);
    }
    
    currentProject = projectName;
    
    // Input alanlarını aktif et
    document.getElementById('commandInput').disabled = false;
    document.getElementById('sendCommandBtn').disabled = false;
    document.getElementById('commandInput').focus();
    
    // Hemen bir çıktı al
    fetchOutput(projectName);
    
    // Her saniye çıktıyı güncelle
    currentOutputInterval = setInterval(() => {
        fetchOutput(projectName);
    }, 1000);
}

// Çıktıyı getir
async function fetchOutput(projectName) {
    try {
        const res = await fetch(`/api/project-output/${projectName}`);
        const data = await res.json();
        
        const outputDiv = document.getElementById('output');
        let outputText = `📟 [${projectName}] ${data.url ? `🌐 ${data.url}` : ''}\n`;
        outputText += `⚙️ Komut: ${data.command || 'Belirtilmemiş'}\n`;
        outputText += `${'═'.repeat(60)}\n\n`;
        outputText += data.stdout || '⏳ Çıktı bekleniyor...';
        
        if (data.stderr) {
            outputText += `\n\n❌ HATA:\n${data.stderr}`;
        }
        
        outputDiv.innerHTML = outputText;
        outputDiv.scrollTop = outputDiv.scrollHeight;
        
        if (!data.running) {
            stopOutputMonitoring();
            outputDiv.innerHTML += '\n\n⏹️ PROJE DURDURULDU';
        }
    } catch (error) {
        console.error('Çıktı alınamadı');
    }
}

// Komut gönder
window.sendCommand = async function() {
    if (!currentUser || !currentProject) {
        showAlert('Önce bir proje seçin', 'error');
        return;
    }
    
    const commandInput = document.getElementById('commandInput');
    const command = commandInput.value.trim();
    
    if (!command) return;
    
    try {
        const res = await fetch(`/api/send-command/${currentProject}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: command })
        });
        
        const data = await res.json();
        
        if (data.success) {
            commandInput.value = '';
            // Çıktıya komutu ekle
            const outputDiv = document.getElementById('output');
            outputDiv.innerHTML += `\n> ${command}`;
        } else {
            showAlert(data.error || 'Komut gönderilemedi', 'error');
        }
    } catch (error) {
        showAlert('Komut gönderilemedi', 'error');
    }
};

// Çıktı temizle
window.clearOutput = async function() {
    if (!currentUser || !currentProject) return;
    
    try {
        await fetch(`/api/clear-output/${currentProject}`, { method: 'POST' });
        document.getElementById('output').innerHTML = '🧹 Çıktı temizlendi...';
    } catch (error) {
        showAlert('Çıktı temizlenemedi', 'error');
    }
};

// İzlemeyi durdur
function stopOutputMonitoring() {
    if (currentOutputInterval) {
        clearInterval(currentOutputInterval);
        currentOutputInterval = null;
    }
    
    currentProject = null;
    document.getElementById('commandInput').disabled = true;
    document.getElementById('sendCommandBtn').disabled = true;
}

// ========== YARDIMCI FONKSİYONLAR ==========

function showAlert(message, type) {
    const alert = document.getElementById('alert');
    alert.textContent = message;
    alert.className = `alert alert-${type}`;
    alert.style.display = 'block';
    
    setTimeout(() => {
        alert.style.display = 'none';
    }, 3000);
}

// ========== EVENT LİSTENERS ==========
document.addEventListener('DOMContentLoaded', () => {
    // Upload form
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!currentUser) {
                showAlert('Önce giriş yapmalısınız', 'error');
                showLogin();
                return;
            }
            
            const fileInput = document.getElementById('fileInput');
            const projectName = document.getElementById('projectName').value;
            
            if (!fileInput.files[0]) {
                showAlert('Lütfen bir ZIP dosyası seçin', 'error');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            if (projectName) {
                formData.append('project_name', projectName);
            }
            
            // Yükleme butonunu devre dışı bırak
            const submitBtn = e.target.querySelector('button[type="submit"]');
            const originalText = submitBtn.textContent;
            submitBtn.textContent = '⏳ Yükleniyor...';
            submitBtn.disabled = true;
            
            try {
                const res = await fetch('/api/upload-project', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await res.json();
                
                if (data.success) {
                    showAlert(`📦 ${data.message}`, 'success');
                    fileInput.value = '';
                    document.getElementById('projectName').value = '';
                    await loadProjectsFromServer();
                } else {
                    showAlert(data.error || 'Yükleme hatası', 'error');
                }
            } catch (error) {
                showAlert('Proje yüklenemedi: ' + error.message, 'error');
            } finally {
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
            }
        });
    }

    // Output selector
    const outputSelector = document.getElementById('outputSelector');
    if (outputSelector) {
        outputSelector.addEventListener('change', (e) => {
            const projectName = e.target.value;
            if (projectName) {
                startOutputMonitoring(projectName);
            } else {
                stopOutputMonitoring();
                document.getElementById('output').innerHTML = '📟 Proje seçin ve çıktısını izleyin...';
            }
        });
    }

    // Command input
    const commandInput = document.getElementById('commandInput');
    if (commandInput) {
        commandInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendCommand();
            }
        });
    }

    // Clear output button
    const clearBtn = document.getElementById('clearOutputBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearOutput);
    }

    // Send command button
    const sendBtn = document.getElementById('sendCommandBtn');
    if (sendBtn) {
        sendBtn.addEventListener('click', sendCommand);
    }

    // Modal dışına tıklandığında kapat
    window.onclick = function(event) {
        if (event.target.classList.contains('modal')) {
            if (!currentUser) {
                return; // Kullanıcı giriş yapmamışsa kapatma
            }
            event.target.classList.remove('active');
        }
    };
});