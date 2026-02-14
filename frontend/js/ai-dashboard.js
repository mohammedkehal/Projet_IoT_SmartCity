// js/ai-dashboard.js (VERSION FINALE - ACTIONS + CONSO + TRAFIC)

// --- VARIABLES GLOBALES ---
const API_URL = "http://127.0.0.1:8000/api";
let globalLamps = [];
let globalAlerts = [];
let globalConso = 0;
let isNightMode = false;

// --- GRAPHIQUE ---
let consoData = [];
let labels = [];
let consoChart; 

// --- NAVIGATION ---
function showSection(sectionId) {
    document.querySelectorAll('.main-content').forEach(el => el.classList.remove('active-section'));
    document.querySelectorAll('.nav-link').forEach(el => {
        el.classList.remove('active');
        el.classList.add('text-white-50');
    });

    const section = document.getElementById(`section-${sectionId}`);
    if (section) section.classList.add('active-section');

    const navId = sectionId === 'dashboard' ? 'nav-dashboard' : 'nav-ai';
    const activeNav = document.getElementById(navId);
    if (activeNav) {
        activeNav.classList.add('active', 'text-white');
        activeNav.classList.remove('text-white-50');
    }
}

// --- DATA FETCHING ---
async function fetchData() {
    try {
        const resLamps = await fetch(`${API_URL}/lampadaires`);
        globalLamps = await resLamps.json(); 
        
        const resAlerts = await fetch(`${API_URL}/alertes`);
        globalAlerts = await resAlerts.json(); 
        
        const resEnv = await fetch(`${API_URL}/environnement`);
        const envData = await resEnv.json();
        isNightMode = envData.is_night;

        updateDashboard(globalLamps);
        updateAlerts(globalAlerts);
        updateEnvBadge(isNightMode);
        
    } catch (e) { console.error("Erreur API", e); }
}

function updateEnvBadge(isNight) {
    const badge = document.getElementById("env-badge");
    if(badge) {
        if(isNight) {
            badge.className = "badge fs-6 ms-2 bg-dark text-warning border border-warning";
            badge.innerHTML = '<i class="bi bi-moon-stars-fill"></i> MODE NUIT';
        } else {
            badge.className = "badge fs-6 ms-2 bg-light text-primary border border-primary";
            badge.innerHTML = '<i class="bi bi-sun-fill"></i> MODE JOUR';
        }
    }
}

function updateDashboard(lamps) {
    const tbody = document.getElementById("lamp-table-body");
    if (!tbody) return;
    
    tbody.innerHTML = "";
    let activeCount = 0;
    globalConso = 0;

    lamps.forEach(lamp => {
        if(lamp.is_on) activeCount++;
        globalConso += lamp.consumption;
        const statusDot = lamp.is_on ? "dot-on" : "dot-off";
        
        const trafficVal = lamp.traffic_level || 0;
        const trafficBadge = trafficVal > 50 ? 
            `<span class="badge bg-warning text-dark"><i class="bi bi-car-front-fill"></i> Intense (${trafficVal})</span>` : 
            `<span class="badge bg-info text-dark"><i class="bi bi-bicycle"></i> Fluide (${trafficVal})</span>`;

        let healthBadge = '<span class="badge bg-success"><i class="bi bi-check-circle"></i> OK</span>';
        if (lamp.health_status && lamp.health_status !== "OK") {
                let color = "bg-danger";
                if(lamp.health_status === "ANOMALIE_IA") color = "bg-warning text-dark";
                if(lamp.health_status === "SURTENSION") color = "bg-warning text-dark";
                healthBadge = `<span class="badge ${color}"><i class="bi bi-exclamation-triangle"></i> ${lamp.health_status}</span>`;
        } else if (lamp.is_on && lamp.consumption < 5) {
            healthBadge = '<span class="badge bg-danger"><i class="bi bi-lightbulb-off"></i> AMPOULE GRILLÉE</span>';
        }

        tbody.innerHTML += `
            <tr>
                <td><span class="fw-bold">${lamp.id}</span><br><small class="text-muted">${lamp.zone}</small></td>
                <td><span class="status-dot ${statusDot}"></span> ${lamp.is_on ? "ON" : "OFF"} <span class="badge bg-secondary">${lamp.intensity}%</span></td>
                <td>${lamp.consumption.toFixed(1)} W</td>
                <td>${trafficBadge}</td>
                <td>${healthBadge}</td>
            </tr>`;
    });

    const activeLampsEl = document.getElementById("active-lamps");
    const totalConsoEl = document.getElementById("total-conso");
    if (activeLampsEl) activeLampsEl.innerText = activeCount;
    if (totalConsoEl) totalConsoEl.innerText = globalConso.toFixed(1);

    labels.push(new Date().toLocaleTimeString());
    consoData.push(globalConso);
    if (labels.length > 20) { labels.shift(); consoData.shift(); }
    if (consoChart) consoChart.update();
}

function updateAlerts(alerts) {
    const container = document.getElementById("alerts-container");
    const alertsCountEl = document.getElementById("ai-alerts");
    if (alertsCountEl) alertsCountEl.innerText = alerts.length;
    
    if (container && alerts.length > 0) {
        container.innerHTML = alerts.slice(0, 5).map(alert => `
            <div class="alert-box alert-card p-2 mb-2 bg-dark border border-secondary rounded">
                <strong class="text-danger">⚠️ ${alert.type}</strong><br>
                <small class="text-white">${alert.message}</small><br>
                <small class="text-muted">${alert.device_id} - ${new Date(alert.timestamp).toLocaleTimeString()}</small>
            </div>
        `).join('');
    }
}

function manualRefresh() {
    const icon = document.getElementById("refresh-icon");
    if (icon) {
        icon.classList.add("spin-anim");
        fetchData().then(() => {
            setTimeout(() => icon.classList.remove("spin-anim"), 500);
        });
    } else { fetchData(); }
}

// --- INTELLIGENCE ARTIFICIELLE & CHATBOT ---

function sendQuickMsg(msg) {
    const userInput = document.getElementById("user-input");
    if (userInput) { userInput.value = msg; sendMessage(); }
}

function handleEnter(e) { if(e.key === 'Enter') sendMessage(); }

function sendMessage() {
    const input = document.getElementById("user-input");
    const msg = input.value.trim();
    if(!msg) return;

    const chatBox = document.getElementById("chat-messages");
    if (chatBox) {
        chatBox.innerHTML += `<div class="message user-msg">${msg}</div>`;
        input.value = "";
        chatBox.scrollTop = chatBox.scrollHeight;

        setTimeout(async () => {
            const botResponse = await generateAIResponse(msg);
            chatBox.innerHTML += `<div class="message bot-msg">${botResponse}</div>`;
            chatBox.scrollTop = chatBox.scrollHeight;
        }, 600);
    }
}

// --- CERVEAU DE L'ASSISTANT ---
async function generateAIResponse(query) {
    query = query.toLowerCase();

    // 1. ACTION : ALLUMER / ÉTEINDRE
    if (query.includes("allume") || query.includes("active")) {
        if (query.includes("zone a")) {
            await controlZone("Zone_A", 100);
            return "✅ <strong>Commande exécutée :</strong> J'ai envoyé l'ordre d'allumage (100%) pour toute la <strong>Zone A</strong>.";
        }
        if (query.includes("zone b")) {
            await controlZone("Zone_B", 100);
            return "✅ <strong>Commande exécutée :</strong> J'ai envoyé l'ordre d'allumage (100%) pour toute la <strong>Zone B</strong>.";
        }
        return "Quelle zone voulez-vous allumer ? (Zone A ou Zone B)";
    }
    
    if (query.includes("éteins") || query.includes("désactive") || query.includes("stop")) {
         if (query.includes("zone a")) {
            await controlZone("Zone_A", 0);
            return "🌑 <strong>Commande exécutée :</strong> Extinction de la <strong>Zone A</strong> (Mode économie totale).";
        }
        if (query.includes("zone b")) {
            await controlZone("Zone_B", 0);
            return "🌑 <strong>Commande exécutée :</strong> Extinction de la <strong>Zone B</strong> (Mode économie totale).";
        }
    }

    // 2. ANALYSE SPÉCIFIQUE PAR ZONE
    if (query.includes("zone a")) { return analyzeZone("Zone_A"); }
    if (query.includes("zone b")) { return analyzeZone("Zone_B"); }

    // 3. DIAGNOSTICS & PANNES
    if(query.includes("panne") || query.includes("problème") || query.includes("alerte") || query.includes("état")) {
        const faultyLamps = globalLamps.filter(l => l.health_status && l.health_status !== "OK");
        if(faultyLamps.length > 0) {
            let txt = `⚠️ <strong>Diagnostic : ${faultyLamps.length} anomalie(s) détectée(s)</strong> :`;
            faultyLamps.forEach(l => {
                let icon = "🔴"; 
                if(l.health_status.includes("IA")) icon = "🟠";
                txt += `<br>${icon} ${l.id} : ${l.health_status}`;
            });
            return txt;
        }
        return "✅ <strong>Système Nominal.</strong> Tous les indicateurs sont au vert.";
    }

    // 4. CONSOMMATION (LE BLOC MANQUANT A ÉTÉ RAJOUTÉ ICI !)
    if(query.includes("conso") || query.includes("énergie") || query.includes("watt")) {
        let status = "modérée";
        if(globalConso > 100) status = "élevée (Pic de charge)";
        if(globalConso < 10) status = "basse (Mode Éco)";
        
        return `⚡ La consommation totale est de <strong>${globalConso.toFixed(1)} W</strong>.<br>C'est une consommation ${status}.`;
    }

    // 5. TRAFIC
    if(query.includes("trafic") || query.includes("circulation")) {
        const highTraffic = globalLamps.filter(l => l.traffic_level > 50);
        const mediumTraffic = globalLamps.filter(l => l.traffic_level > 10 && l.traffic_level <= 50);
        
        if(highTraffic.length > 0) return `🚗 <strong>ALERTE TRAFIC !</strong> Circulation dense sur ${highTraffic.length} zone(s). Éclairage forcé.`;
        if(mediumTraffic.length > 0) {
            let maxVal = Math.max(...mediumTraffic.map(l => l.traffic_level));
            return `🚙 <strong>Trafic Modéré (Max: ${maxVal}).</strong> Circulation fluide mais active.`;
        }
        return "🚲 <strong>Circulation Calme.</strong> Aucun véhicule détecté.";
    }

    return "Je peux : <br>- <strong>Allumer la Zone A</strong><br>- Analyser une <strong>Zone</strong><br>- Vérifier les <strong>pannes</strong><br>- Donner la <strong>consommation</strong>";
}

// --- FONCTIONS AUXILIAIRES ---

function analyzeZone(zoneName) {
    const zoneLamps = globalLamps.filter(l => l.zone === zoneName);
    if (zoneLamps.length === 0) return `❌ Je ne trouve aucune donnée pour la ${zoneName}.`;

    const activeCount = zoneLamps.filter(l => l.is_on).length;
    const avgConso = zoneLamps.reduce((acc, l) => acc + l.consumption, 0);
    const hasIssue = zoneLamps.some(l => l.health_status !== "OK");

    let statusIcon = hasIssue ? "⚠️" : "✅";
    return `📊 <strong>Rapport ${zoneName} :</strong><br>
    - Statut : ${statusIcon} ${hasIssue ? "Problèmes détectés" : "Opérationnel"}<br>
    - Lampadaires : ${activeCount}/${zoneLamps.length} actifs<br>
    - Conso Totale : ${avgConso.toFixed(1)} W`;
}

// Fonction pour contrôler physiquement les lampes (Appelle ton API Backend)
async function controlZone(zoneName, intensity) {
    const targetLamps = globalLamps.filter(l => l.zone === zoneName);
    for (const lamp of targetLamps) {
        try {
            await fetch(`${API_URL}/lampadaires/${lamp.id}/switch?intensity=${intensity}`, {
                method: 'POST'
            });
        } catch (e) {
            console.error(`Erreur commande ${lamp.id}`, e);
        }
    }
}

// Initialisation
document.addEventListener('DOMContentLoaded', () => {
    const ctx = document.getElementById('consoChart').getContext('2d');
    consoChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Consommation Totale (W)',
                data: consoData,
                borderColor: '#0d6efd',
                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: { responsive: true, scales: { y: { beginAtZero: true }, x: { display: false } } }
    });

    fetchData();
    setInterval(fetchData, 2000);
});