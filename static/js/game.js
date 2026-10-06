// CYBER DEFENSE INCIDENT RESPONSE DRILL SCRIPT

let gameState = 'IDLE'; // IDLE, WAITING, TRIGGERED, FINISHED
let startTime = 0;
let waitTimeout = null;
let currentScore = null;

const THREAT_ALERTS = [
    "🚨 RANSOMWARE ENCRYPTION COMMENCING ON DC-03! ISOLATE NOW!",
    "🚨 UNAUTHORIZED ROOT SSH INTRUSION DETECTED! SEVER CONNECTION!",
    "🚨 MALWARE C2 BEACONING FROM SANDBOX LAB! KILL PROCESS!",
    "🚨 ACTIVE KERBEROASTING ATTACK DETECTED! BLOCK IP ADDRESS!",
    "🚨 DDOS SYN FLOOD INUNDATING LAB ROUTER! ENGAGE RATE LIMITER!"
];

function setDrillState(state, customText = '', subtitle = '') {
    gameState = state;
    const arena = document.getElementById('drill-arena');
    const titleEl = document.getElementById('drill-title');
    const subEl = document.getElementById('drill-subtitle');

    arena.classList.remove('waiting', 'ready');

    if (state === 'IDLE') {
        titleEl.textContent = 'READY TO INITIATE DRILL';
        subEl.textContent = 'Click here or press SPACE to begin threat detection surveillance.';
    } else if (state === 'WAITING') {
        arena.classList.add('waiting');
        titleEl.textContent = '⚠️ STANDBY... SCANNING NETWORK...';
        subEl.textContent = 'Wait for the breach alert to flash green. DO NOT CLICK EARLY!';
        cyberSfx.beep(300, 'sine', 0.15);
    } else if (state === 'TRIGGERED') {
        arena.classList.add('ready');
        titleEl.textContent = customText;
        subEl.textContent = '⚡ CLICK IMMEDIATELY TO NEUTRALIZE!';
        cyberSfx.beep(950, 'sawtooth', 0.25);
    } else if (state === 'EARLY') {
        arena.classList.add('waiting');
        titleEl.textContent = '❌ FALSE POSITIVE TRIGGER!';
        subEl.textContent = 'You reacted before the threat occurred. Click to reset.';
        cyberSfx.warn();
    } else if (state === 'FINISHED') {
        titleEl.textContent = `🎯 THREAT NEUTRALIZED!`;
        subEl.textContent = `Reaction logged: ${currentScore} ms. Click to drill again.`;
    }
}

function handleArenaClick() {
    if (gameState === 'IDLE') {
        startDrill();
    } else if (gameState === 'WAITING') {
        clearTimeout(waitTimeout);
        setDrillState('EARLY');
    } else if (gameState === 'TRIGGERED') {
        const endTime = performance.now();
        const reactionTime = Math.round((endTime - startTime) * 10) / 10;
        currentScore = reactionTime;
        setDrillState('FINISHED');
        recordScore(reactionTime);
    } else if (gameState === 'EARLY' || gameState === 'FINISHED') {
        setDrillState('IDLE');
    }
}

function startDrill() {
    setDrillState('WAITING');
    // Random wait between 1.8s and 4.8s
    const delay = Math.floor(Math.random() * 3000) + 1800;

    waitTimeout = setTimeout(() => {
        const randomAlert = THREAT_ALERTS[Math.floor(Math.random() * THREAT_ALERTS.length)];
        startTime = performance.now();
        setDrillState('TRIGGERED', randomAlert);
    }, delay);
}

function recordScore(reactionTime) {
    const nameInput = document.getElementById('operator-name');
    const fullName = (nameInput && nameInput.value.trim()) ? nameInput.value.trim() : 'Operator_' + Math.floor(Math.random() * 900 + 100);

    const scoreDisplay = document.getElementById('last-score-val');
    const badgeDisplay = document.getElementById('operator-rank-badge');
    if (scoreDisplay) scoreDisplay.textContent = `${reactionTime} ms`;

    // Calculate Cyber Rank Badge
    let rank = 'Cyber Elite (Tier 0)';
    let badgeClass = 'running';
    if (reactionTime < 220) {
        rank = '⚡ CYBER APEX PREDATOR (< 220ms)';
        badgeClass = 'running';
    } else if (reactionTime < 320) {
        rank = '🛡️ TIER-1 INCIDENT RESPONDER';
        badgeClass = 'running';
    } else if (reactionTime < 450) {
        rank = '🔎 SOC DEFENSE ANALYST';
        badgeClass = 'paused';
    } else {
        rank = '⚠️ BREACH DELAYED (Training Required)';
        badgeClass = 'stopped';
    }

    if (badgeDisplay) {
        badgeDisplay.textContent = rank;
        badgeDisplay.className = `status-badge ${badgeClass}`;
    }

    // Call user's exact Flask route /save_result
    fetch('/save_result', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            fullName: fullName,
            reactionTime: reactionTime
        })
    })
    .then(res => res.json())
    .then(data => {
        showToast(`Score registered for ${fullName}: ${reactionTime} ms`, 'success');
        updateLeaderboardTable(data.leaderboard);
    })
    .catch(err => {
        showToast(`Failed saving result: ${err}`, 'error');
    });
}

function updateLeaderboardTable(list) {
    const tbody = document.getElementById('leaderboard-tbody');
    if (!tbody || !list) return;

    tbody.innerHTML = '';
    list.forEach((item, index) => {
        const tr = document.createElement('tr');
        const isCurrent = (item.reactionTime === currentScore);
        if (isCurrent) tr.style.backgroundColor = 'rgba(0, 240, 255, 0.15)';

        let medal = `#${index + 1}`;
        if (index === 0) medal = '🥇 #1';
        else if (index === 1) medal = '🥈 #2';
        else if (index === 2) medal = '🥉 #3';

        tr.innerHTML = `
            <td class="mono">${medal}</td>
            <td style="font-weight: 600; color: #fff;">${item.fullName}</td>
            <td class="mono" style="color: var(--neon-cyan);">${item.reactionTime} ms</td>
            <td><span class="status-badge ${item.reactionTime < 300 ? 'running' : 'paused'}">Active</span></td>
        `;
        tbody.appendChild(tr);
    });
}

// Support Spacebar
document.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && e.target.tagName !== 'INPUT') {
        e.preventDefault();
        handleArenaClick();
    }
});
