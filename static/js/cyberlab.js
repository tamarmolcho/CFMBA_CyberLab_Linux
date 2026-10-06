// CFMBA CYBERLAB CLIENT SCRIPT

// Cyber Sound Effects via Web Audio API
class CyberAudio {
    constructor() {
        this.ctx = null;
        this.enabled = true;
    }

    init() {
        if (!this.ctx && (window.AudioContext || window.webkitAudioContext)) {
            this.ctx = new (window.AudioContext || window.webkitAudioContext)();
        }
    }

    beep(freq = 800, type = 'sine', duration = 0.08) {
        if (!this.enabled) return;
        try {
            this.init();
            if (!this.ctx) return;
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();
            osc.type = type;
            osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
            gain.gain.setValueAtTime(0.04, this.ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.0001, this.ctx.currentTime + duration);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start();
            osc.stop(this.ctx.currentTime + duration);
        } catch (e) {}
    }

    click() { this.beep(1200, 'triangle', 0.04); }
    success() { 
        this.beep(880, 'sine', 0.06); 
        setTimeout(() => this.beep(1760, 'sine', 0.1), 60); 
    }
    warn() { 
        this.beep(400, 'sawtooth', 0.12); 
    }
}

const cyberSfx = new CyberAudio();

// Toast Notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon = 'ℹ️';
    if (type === 'success') { icon = '🛡️'; cyberSfx.success(); }
    else if (type === 'error') { icon = '⚠️'; cyberSfx.warn(); }
    else { cyberSfx.click(); }

    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.transition = 'all 0.3s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Live Clock - Israel Time (Asia/Jerusalem / שעון ישראל)
function updateClock() {
    const clockEl = document.getElementById('utc-clock-val');
    if (clockEl) {
        const now = new Date();
        try {
            const timeStr = now.toLocaleTimeString('en-GB', {
                timeZone: 'Asia/Jerusalem',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            });
            clockEl.textContent = `${timeStr} (שעון ישראל)`;
        } catch (e) {
            const pad = n => String(n).padStart(2, '0');
            clockEl.textContent = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())} (שעון ישראל)`;
        }
    }
}
setInterval(updateClock, 1000);
updateClock();

// Live Telemetry Poller
function pollTelemetry() {
    fetch('/api/telemetry')
        .then(res => res.json())
        .then(data => {
            // Update HUD ticker
            const cpuEl = document.getElementById('ticker-cpu');
            const ramEl = document.getElementById('ticker-ram');
            const vmRunEl = document.getElementById('ticker-running-vms');
            
            if (cpuEl) cpuEl.textContent = `${data.telemetry.cpu_percent}%`;
            if (ramEl) ramEl.textContent = `${data.telemetry.memory.percent}%`;
            if (vmRunEl) vmRunEl.textContent = `${data.vms.running}/${data.vms.total}`;

            // Update CPU/RAM bar if on dashboard
            const cpuBar = document.getElementById('cpu-progress-bar');
            if (cpuBar) cpuBar.style.width = `${data.telemetry.cpu_percent}%`;

            const ramBar = document.getElementById('ram-progress-bar');
            if (ramBar) ramBar.style.width = `${data.telemetry.memory.percent}%`;
        })
        .catch(() => {});
}
setInterval(pollTelemetry, 3000);

// VM Actions
function controlVm(vmid, action, force = false) {
    cyberSfx.click();
    showToast(`Sending [${action.toUpperCase()}] signal to VM...`, 'info');

    fetch(`/api/vm/${encodeURIComponent(vmid)}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: action, force: force })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast(data.message, 'success');
            setTimeout(() => window.location.reload(), 800);
        } else {
            showToast(`Error: ${data.message || data.error}`, 'error');
        }
    })
    .catch(err => {
        showToast(`Request failed: ${err}`, 'error');
    });
}

function captureScreenshot(vmid) {
    cyberSfx.click();
    showToast(`Triggering VBox surveillance frame capture for [${vmid}]...`, 'info');

    fetch(`/api/vm/${encodeURIComponent(vmid)}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'screenshot' })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showToast(`Frame captured: ${data.filename}`, 'success');
            // If on surveillance page, reload or open modal
            openLightbox(data.url, `Surveillance Snapshot: ${data.vm_name}`);
        } else {
            showToast(`Capture failed: ${data.message}`, 'error');
        }
    })
    .catch(err => {
        showToast(`Capture failed: ${err}`, 'error');
    });
}

function queryVmIp(vmid, targetElementId) {
    cyberSfx.click();
    fetch(`/api/vm/${encodeURIComponent(vmid)}/ip`)
        .then(res => res.json())
        .then(data => {
            const el = document.getElementById(targetElementId);
            if (el) {
                el.textContent = data.ip;
                el.classList.add('ip-highlight');
                showToast(`IP for ${data.name || vmid}: ${data.ip}`, 'success');
            }
        })
        .catch(err => {
            showToast(`Failed querying guest IP: ${err}`, 'error');
        });
}

// Lightbox for Screenshots
function openLightbox(imgUrl, title = 'Cyber Surveillance Frame') {
    let modal = document.getElementById('lightbox-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'lightbox-modal';
        modal.className = 'cyber-modal-backdrop';
        modal.innerHTML = `
            <div class="cyber-modal" style="max-width: 900px;">
                <div class="modal-header">
                    <h3 class="panel-title" id="lightbox-title"></h3>
                    <button class="cyber-btn cyber-btn-outline cyber-btn-sm" onclick="closeLightbox()">✕ CLOSE</button>
                </div>
                <div class="modal-body" style="padding: 10px; background: #020508; text-align: center;">
                    <img id="lightbox-img" src="" style="max-width: 100%; height: auto; border: 1px solid var(--neon-cyan); border-radius: 4px;" />
                </div>
                <div class="modal-footer" style="justify-content: space-between;">
                    <span id="lightbox-meta" style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-muted);"></span>
                    <a id="lightbox-dl" href="#" download class="cyber-btn cyber-btn-primary cyber-btn-sm">💾 DOWNLOAD PNG</a>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    document.getElementById('lightbox-title').textContent = title;
    document.getElementById('lightbox-img').src = imgUrl;
    document.getElementById('lightbox-dl').href = imgUrl;
    document.getElementById('lightbox-meta').textContent = `FEED TIMELOCKED :: ${new Date().toISOString()}`;
    modal.style.display = 'flex';
}

function closeLightbox() {
    const modal = document.getElementById('lightbox-modal');
    if (modal) modal.style.display = 'none';
}

// Copy to Clipboard
function copyText(text, btnEl = null) {
    navigator.clipboard.writeText(text).then(() => {
        showToast(`Copied to clipboard: ${text}`, 'info');
        if (btnEl) {
            const original = btnEl.innerHTML;
            btnEl.innerHTML = '✓ COPIED';
            setTimeout(() => { btnEl.innerHTML = original; }, 1500);
        }
    });
}

// Toggle Demo Range Switch
function toggleDemoMode(checkbox) {
    cyberSfx.click();
    fetch('/api/toggle_demo', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            showToast(`Cyber Range Simulation Mode ${data.demo_enabled ? 'Enabled' : 'Disabled'}.`, 'info');
            setTimeout(() => window.location.reload(), 700);
        });
}

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
    // Play subtle startup blip on first user interaction
    document.addEventListener('click', () => cyberSfx.init(), { once: true });
});

// ============================================================
// AI CYBERCOPILOT / LAB AGENT JAVASCRIPT
// ============================================================

let copilotVoiceRecognizer = null;
let isVoiceDictating = false;

function toggleCopilot(forceState = null) {
    const drawer = document.getElementById('copilot-drawer');
    if (!drawer) return;
    
    cyberSfx.click();
    if (forceState === true) {
        drawer.classList.add('open');
    } else if (forceState === false) {
        drawer.classList.remove('open');
    } else {
        drawer.classList.toggle('open');
    }

    if (drawer.classList.contains('open')) {
        setTimeout(() => {
            const input = document.getElementById('copilot-input');
            if (input) input.focus();
            scrollCopilotToBottom();
        }, 150);
    }
}

function clearCopilotChat() {
    cyberSfx.click();
    const container = document.getElementById('copilot-messages');
    if (!container) return;
    container.innerHTML = `
        <div class="copilot-msg agent">
            <div>👋 <strong>ההיסטוריה אופסה!</strong> במה אוכל לסייע לך עכשיו במעבדה?</div>
            <div style="margin-top: 6px; font-size: 0.8rem; color: var(--text-muted);">
                תוכל לבקש: "תפעיל את קאלי", "כבה הכל", "מצב דיסק", או "איך יוצרים מכונה".
            </div>
        </div>
    `;
}

function sendQuickCopilotPrompt(text) {
    const input = document.getElementById('copilot-input');
    if (input) {
        input.value = text;
        const form = document.getElementById('copilot-form');
        if (form) {
            handleCopilotSubmit(new Event('submit'));
        }
    }
}

function scrollCopilotToBottom() {
    const container = document.getElementById('copilot-messages');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

function formatMarkdown(text) {
    if (!text) return '';
    let out = text;
    // Bold: **text**
    out = out.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Inline code: `text`
    out = out.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Markdown links: [text](url)
    out = out.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
    // Bullet lists: \n- item
    out = out.replace(/(?:^|\n)-\s+(.+)/g, '<br/>• $1');
    // Line breaks
    out = out.replace(/\n\n/g, '<br/><br/>').replace(/\n/g, '<br/>');
    return out;
}

function handleCopilotSubmit(e) {
    if (e && e.preventDefault) e.preventDefault();
    const input = document.getElementById('copilot-input');
    const container = document.getElementById('copilot-messages');
    if (!input || !container) return;

    const userText = input.value.trim();
    if (!userText) return;

    cyberSfx.click();

    // 1. Append user message bubble
    const userMsgEl = document.createElement('div');
    userMsgEl.className = 'copilot-msg user';
    userMsgEl.textContent = userText;
    container.appendChild(userMsgEl);

    input.value = '';
    scrollCopilotToBottom();

    // 2. Append typing indicator
    const typingEl = document.createElement('div');
    typingEl.className = 'copilot-msg agent copilot-typing-wrapper';
    typingEl.innerHTML = `
        <div class="copilot-typing">
            <span></span><span></span><span></span>
        </div>
        <span style="font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono); margin-right: 6px;">מעבד פקודה...</span>
    `;
    container.appendChild(typingEl);
    scrollCopilotToBottom();

    // 3. Post to API
    fetch('/api/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userText })
    })
    .then(res => res.json())
    .then(data => {
        // Remove typing indicator
        if (typingEl && typingEl.parentNode) {
            typingEl.parentNode.removeChild(typingEl);
        }

        const agentMsgEl = document.createElement('div');
        agentMsgEl.className = 'copilot-msg agent';
        
        let contentHtml = `<div>${formatMarkdown(data.reply || 'אין מענה מהשרת.')}</div>`;

        if (data.action && data.action !== 'none' && data.action !== 'help_guidance') {
            contentHtml += `<div class="copilot-action-badge">⚡ Action: ${data.action} ${data.status ? `(${data.status})` : ''}</div>`;
        }

        if (data.action === 'screenshot' && data.image_url) {
            contentHtml += `
                <div style="margin-top: 10px;">
                    <img src="${data.image_url}" onclick="openLightbox('${data.image_url}', 'צילום מסך: ${data.filename || 'סייבר'}')" style="max-width: 100%; border-radius: 6px; border: 1px solid var(--neon-cyan); cursor: pointer;" />
                </div>
            `;
        }

        agentMsgEl.innerHTML = contentHtml;
        container.appendChild(agentMsgEl);
        scrollCopilotToBottom();

        // Trigger effects based on action
        if (data.status === 'success') {
            cyberSfx.success();
            // If action changed VM state, show toast & refresh list if on dashboard
            if (['start_vm', 'stop_vm', 'batch_start', 'batch_stop', 'clone_vm'].includes(data.action)) {
                showToast(`Agent Action Executed: ${data.action}`, 'success');
                setTimeout(() => {
                    if (window.location.pathname === '/') {
                        window.location.reload();
                    }
                }, 1200);
            }
        }
    })
    .catch(err => {
        if (typingEl && typingEl.parentNode) {
            typingEl.parentNode.removeChild(typingEl);
        }
        cyberSfx.error();
        const errEl = document.createElement('div');
        errEl.className = 'copilot-msg agent';
        errEl.innerHTML = `<span style="color: var(--neon-red);">⚠️ שגיאה בתקשורת עם ה-Copilot: ${err.message}</span>`;
        container.appendChild(errEl);
        scrollCopilotToBottom();
    });
}

// Voice Dictation (Speech-to-Text)
function toggleVoiceDictation() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const micBtn = document.getElementById('copilot-mic-btn');
    const input = document.getElementById('copilot-input');

    if (!SpeechRecognition) {
        showToast('דיבור קולי אינו נתמך בדפדפן זה (דרוש Chrome/Edge/Safari)', 'info');
        return;
    }

    if (isVoiceDictating && copilotVoiceRecognizer) {
        copilotVoiceRecognizer.stop();
        isVoiceDictating = false;
        if (micBtn) micBtn.classList.remove('listening');
        return;
    }

    try {
        copilotVoiceRecognizer = new SpeechRecognition();
        copilotVoiceRecognizer.lang = 'he-IL'; // Hebrew speech recognition
        copilotVoiceRecognizer.interimResults = false;
        copilotVoiceRecognizer.maxAlternatives = 1;

        copilotVoiceRecognizer.onstart = () => {
            isVoiceDictating = true;
            if (micBtn) micBtn.classList.add('listening');
            showToast('🎙️ מקשיב... אמור פקודה (למשל: "תפעיל את קאלי")', 'info');
        };

        copilotVoiceRecognizer.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            if (input) {
                input.value = transcript;
                showToast(`זיהוי קולי: "${transcript}"`, 'success');
                handleCopilotSubmit(new Event('submit'));
            }
        };

        copilotVoiceRecognizer.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            showToast(`שגיאת זיהוי קולי: ${event.error}`, 'error');
            isVoiceDictating = false;
            if (micBtn) micBtn.classList.remove('listening');
        };

        copilotVoiceRecognizer.onend = () => {
            isVoiceDictating = false;
            if (micBtn) micBtn.classList.remove('listening');
        };

        copilotVoiceRecognizer.start();
    } catch (err) {
        showToast(`שגיאה בהפעלת מיקרופון: ${err.message}`, 'error');
        isVoiceDictating = false;
        if (micBtn) micBtn.classList.remove('listening');
    }
}

