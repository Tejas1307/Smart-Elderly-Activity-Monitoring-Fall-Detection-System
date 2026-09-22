// Caregiver Dashboard Client Logic

let telemetryWs = null;
let accelChart = null;
let summaryPieChart = null;
let currentActiveFallId = null;

// Oscilloscope rolling buffer
const MAX_CHART_POINTS = 35;
const accelLabels = Array(MAX_CHART_POINTS).fill('');
const axData = Array(MAX_CHART_POINTS).fill(0);
const ayData = Array(MAX_CHART_POINTS).fill(0);
const azData = Array(MAX_CHART_POINTS).fill(1);

const ACTIVITY_COLORS = {
    "Walking": "#3b82f6",
    "Walking upstairs": "#a855f7",
    "Walking downstairs": "#ec4899",
    "Sitting": "#f59e0b",
    "Standing": "#10b981",
    "Lying": "#94a3b8"
};

const ACTIVITY_ICONS = {
    "Walking": "footprints",
    "Walking upstairs": "trending-up",
    "Walking downstairs": "trending-down",
    "Sitting": "armchair",
    "Standing": "user",
    "Lying": "bed"
};

// Initialize Dashboard
document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    connectWebSocket();
    fetchInitialData();
    setupSimulatorControls();

    // Refresh summary every 15 seconds
    setInterval(fetchSummaryData, 15000);
});

function initCharts() {
    // 1. Live Accelerometer Chart
    const ctxAccel = document.getElementById("accelChart").getContext("2d");
    accelChart = new Chart(ctxAccel, {
        type: 'line',
        data: {
            labels: accelLabels,
            datasets: [
                {
                    label: 'Ax',
                    data: axData,
                    borderColor: '#f43f5e',
                    borderWidth: 1.8,
                    pointRadius: 0,
                    tension: 0.3
                },
                {
                    label: 'Ay',
                    data: ayData,
                    borderColor: '#10b981',
                    borderWidth: 1.8,
                    pointRadius: 0,
                    tension: 0.3
                },
                {
                    label: 'Az',
                    data: azData,
                    borderColor: '#3b82f6',
                    borderWidth: 1.8,
                    pointRadius: 0,
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            plugins: {
                legend: {
                    labels: { color: '#94a3b8', font: { size: 11 } }
                },
                tooltip: { enabled: false }
            },
            scales: {
                x: { display: false },
                y: {
                    min: -2.5,
                    max: 4.5,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#64748b', font: { size: 10 } }
                }
            }
        }
    });

    // 2. Activity Distribution Donut Chart
    const ctxPie = document.getElementById("summaryPieChart").getContext("2d");
    summaryPieChart = new Chart(ctxPie, {
        type: 'doughnut',
        data: {
            labels: ['Active Movement', 'Sedentary State', 'Resting State'],
            datasets: [{
                data: [40, 45, 15],
                backgroundColor: ['#3b82f6', '#f59e0b', '#94a3b8'],
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#94a3b8', font: { size: 11 }, padding: 12 }
                }
            },
            cutout: '70%'
        }
    });
}

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;

    telemetryWs = new WebSocket(wsUrl);

    telemetryWs.onopen = () => {
        console.log("Connected to Telemetry WebSocket");
        updateConnectionStatus(true);
    };

    telemetryWs.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'initial_state') {
                handleInitialState(data);
            } else if (data.type === 'telemetry') {
                handleTelemetry(data);
            } else if (data.type === 'fall_resolved') {
                handleFallResolvedEvent(data);
            }
        } catch (e) {
            console.error("Error processing WS message:", e);
        }
    };

    telemetryWs.onclose = () => {
        updateConnectionStatus(false);
        console.warn("WebSocket closed. Reconnecting in 2s...");
        setTimeout(connectWebSocket, 2000);
    };

    telemetryWs.onerror = (err) => {
        console.error("WebSocket error:", err);
    };
}

function handleInitialState(data) {
    if (data.activity_state) updateCurrentActivityUI(data.activity_state);
    if (data.system_health) updateSystemHealthUI(data.system_health);
    if (data.durations) updateDurationsUI(data.durations);
    if (data.timeline) updateTimelineUI(data.timeline);
    if (data.recent_falls) updateFallHistoryTable(data.recent_falls);
    if (data.unresolved_falls && data.unresolved_falls.length > 0) {
        triggerFallModal(data.unresolved_falls[0]);
    }
}

function handleTelemetry(data) {
    const { sample, activity_state, system_health, fall_alert } = data;

    // Update real-time waveform chart
    if (sample && accelChart) {
        axData.push(sample.ax);
        axData.shift();
        ayData.push(sample.ay);
        ayData.shift();
        azData.push(sample.az);
        azData.shift();
        accelChart.update('none');

        // Update raw values text
        document.getElementById("liveAccelVal").innerText = 
            `Ax: ${sample.ax.toFixed(2)}g | Ay: ${sample.ay.toFixed(2)}g | Az: ${sample.az.toFixed(2)}g`;
        document.getElementById("liveGyroVal").innerText = 
            `Gx: ${sample.gx.toFixed(0)}°/s | Gy: ${sample.gy.toFixed(0)}°/s | Gz: ${sample.gz.toFixed(0)}°/s`;
    }

    if (activity_state) {
        updateCurrentActivityUI(activity_state);
    }

    if (system_health) {
        updateSystemHealthUI(system_health);
    }

    // High Priority Fall Event
    if (fall_alert) {
        triggerFallModal(fall_alert);
        fetchFallHistory();
        fetchSummaryData();
    }
}

function updateCurrentActivityUI(state) {
    const badge = document.getElementById("currentActivityBadge");
    const nameElem = document.getElementById("currentActivityName");
    const confElem = document.getElementById("currentConfidence");
    const impactElem = document.getElementById("currentImpactG");
    const descElem = document.getElementById("activityDescription");

    nameElem.innerText = state.activity;
    confElem.innerText = `${(state.confidence * 100).toFixed(1)}%`;
    impactElem.innerText = `${state.impact_g.toFixed(2)}g`;

    // Activity description according to Section 6 of Proposal
    const descMap = {
        "Walking": "Active movement • Continuous regular gait detected",
        "Walking upstairs": "High-intensity movement • Vertical step ascension",
        "Walking downstairs": "High-intensity movement • Controlled step descent",
        "Sitting": "Sedentary state • Senior stationary upright in chair/couch",
        "Standing": "Stationary upright state • Low postural movement",
        "Lying": "Resting state • Horizontal body orientation"
    };
    descElem.innerText = descMap[state.activity] || "Monitored movement state";

    // Set badge style classes
    badge.className = "px-3 py-1 rounded-full text-xs font-semibold tracking-wide uppercase flex items-center gap-1.5 ";
    if (state.activity.includes("Walking upstairs") || state.activity.includes("downstairs")) {
        badge.className += "badge-stairs";
    } else if (state.activity === "Walking") {
        badge.className += "badge-walking";
    } else if (state.activity === "Sitting") {
        badge.className += "badge-sitting";
    } else if (state.activity === "Standing") {
        badge.className += "badge-standing";
    } else {
        badge.className += "badge-lying";
    }
}

function updateSystemHealthUI(health) {
    document.getElementById("nodeBatteryVal").innerText = `${health.battery_pct}%`;
    document.getElementById("nodeLatencyVal").innerText = `${health.latency_ms} ms`;
    document.getElementById("nodeRateVal").innerText = `${health.sample_rate_hz} Hz`;
    document.getElementById("nodeRssiVal").innerText = `${health.rssi} dBm`;
    document.getElementById("lastPacketTime").innerText = health.last_packet_time || "Live";

    const batteryBar = document.getElementById("batteryBar");
    if (batteryBar) batteryBar.style.width = `${health.battery_pct}%`;
}

function updateConnectionStatus(isConnected) {
    const statusDot = document.getElementById("statusPulseDot");
    const statusText = document.getElementById("statusText");
    if (isConnected) {
        statusDot.className = "w-2.5 h-2.5 rounded-full bg-emerald-500 pulse-green";
        statusText.innerText = "ESP32 NODE CONNECTED";
        statusText.className = "text-xs font-semibold tracking-wide text-emerald-400";
    } else {
        statusDot.className = "w-2.5 h-2.5 rounded-full bg-rose-500";
        statusText.innerText = "SEARCHING FOR SENSOR NODE...";
        statusText.className = "text-xs font-semibold tracking-wide text-rose-400";
    }
}

function updateDurationsUI(durations) {
    const activities = [
        { key: "Walking", id: "durWalking", barId: "barWalking" },
        { key: "Walking upstairs", id: "durUpstairs", barId: "barUpstairs" },
        { key: "Walking downstairs", id: "durDownstairs", barId: "barDownstairs" },
        { key: "Sitting", id: "durSitting", barId: "barSitting" },
        { key: "Standing", id: "durStanding", barId: "barStanding" },
        { key: "Lying", id: "durLying", barId: "barLying" }
    ];

    const totalSecs = Object.values(durations).reduce((a, b) => a + b, 0) || 1;

    activities.forEach(item => {
        const secs = durations[item.key] || 0;
        const elem = document.getElementById(item.id);
        const bar = document.getElementById(item.barId);

        const hours = Math.floor(secs / 3600);
        const mins = Math.floor((secs % 3600) / 60);
        const timeStr = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;

        if (elem) elem.innerText = timeStr;
        if (bar) {
            const pct = Math.min(100, Math.round((secs / totalSecs) * 100));
            bar.style.width = `${pct}%`;
        }
    });
}

function updateTimelineUI(intervals) {
    const ribbon = document.getElementById("timelineRibbon");
    const list = document.getElementById("timelineLogList");

    if (!intervals || intervals.length === 0) return;

    // 1. Build Ribbon Visual
    ribbon.innerHTML = "";
    const totalSecs = intervals.reduce((acc, cur) => acc + (cur.duration_seconds || 60), 0) || 1;

    intervals.forEach(interval => {
        const color = ACTIVITY_COLORS[interval.activity] || "#64748b";
        const widthPct = Math.max(2, (interval.duration_seconds / totalSecs) * 100);

        const block = document.createElement("div");
        block.className = "h-7 timeline-block relative group first:rounded-l last:rounded-r cursor-pointer";
        block.style.width = `${widthPct}%`;
        block.style.backgroundColor = color;
        block.title = `${interval.activity} (${interval.start_time} - ${interval.end_time})`;

        ribbon.appendChild(block);
    });

    // 2. Build Recent Log Items (last 8)
    list.innerHTML = "";
    intervals.slice(-8).reverse().forEach(interval => {
        const color = ACTIVITY_COLORS[interval.activity] || "#64748b";
        const mins = Math.round(interval.duration_seconds / 60);

        const row = document.createElement("div");
        row.className = "flex items-center justify-between p-2 rounded-lg bg-slate-800/40 hover:bg-slate-800 border border-slate-700/50 text-xs";
        row.innerHTML = `
            <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full" style="background-color: ${color}"></span>
                <span class="font-medium text-slate-200">${interval.activity}</span>
            </div>
            <div class="flex items-center gap-3 text-slate-400">
                <span>${interval.start_time} - ${interval.end_time}</span>
                <span class="px-2 py-0.5 rounded bg-slate-700/60 font-mono text-slate-300">${mins} min</span>
            </div>
        `;
        list.appendChild(row);
    });
}

function updateFallHistoryTable(falls) {
    const tbody = document.getElementById("fallHistoryTableBody");
    if (!tbody) return;

    if (!falls || falls.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-500 text-xs">No fall events recorded today.</td></tr>`;
        return;
    }

    tbody.innerHTML = "";
    falls.forEach(fall => {
        const tr = document.createElement("tr");
        tr.className = "border-b border-slate-800 hover:bg-slate-800/30 text-xs transition";

        let statusBadge = "";
        if (fall.status === "UNRESOLVED") {
            statusBadge = `<span class="px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/40 font-semibold animate-pulse">CRITICAL ALERT</span>`;
        } else if (fall.status === "ACKNOWLEDGED") {
            statusBadge = `<span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 font-medium">Caregiver Assisted</span>`;
        } else {
            statusBadge = `<span class="px-2 py-0.5 rounded-full bg-slate-700 text-slate-300 font-medium">False Alarm</span>`;
        }

        const actions = fall.status === "UNRESOLVED" ? `
            <div class="flex items-center gap-2">
                <button onclick="resolveFall(${fall.id}, 'ACKNOWLEDGED')" class="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-medium">Respond</button>
                <button onclick="resolveFall(${fall.id}, 'FALSE_ALARM')" class="px-2 py-1 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded text-xs">Dismiss</button>
            </div>
        ` : `<span class="text-slate-500 text-[11px]">${fall.resolved_at ? fall.resolved_at.split(' ')[1] : 'Resolved'}</span>`;

        tr.innerHTML = `
            <td class="p-3 font-mono text-slate-300">${fall.timestamp}</td>
            <td class="p-3 text-slate-200">${fall.pre_activity}</td>
            <td class="p-3 font-semibold text-rose-400">${fall.impact_g.toFixed(2)} g</td>
            <td class="p-3">${statusBadge}</td>
            <td class="p-3 text-slate-400 text-[11px] max-w-xs truncate">${fall.notes || '-'}</td>
            <td class="p-3">${actions}</td>
        `;
        tbody.appendChild(tr);
    });
}

function triggerFallModal(fall) {
    currentActiveFallId = fall.id;
    const modal = document.getElementById("fallAlertModal");
    const impactElem = document.getElementById("modalImpactG");
    const timeElem = document.getElementById("modalAlertTime");
    const preActElem = document.getElementById("modalPreActivity");

    impactElem.innerText = `${fall.impact_g.toFixed(2)} g`;
    timeElem.innerText = fall.timestamp;
    preActElem.innerText = fall.pre_activity || "Normal Walking";

    modal.classList.remove("hidden");
    modal.classList.add("flex");

    // Start siren sound via Web Audio API
    if (window.emergencyAudio) {
        window.emergencyAudio.startFallAlarm();
    }
}

function dismissFallModal(status) {
    if (window.emergencyAudio) {
        window.emergencyAudio.stopFallAlarm();
    }
    const modal = document.getElementById("fallAlertModal");
    modal.classList.add("hidden");
    modal.classList.remove("flex");

    if (currentActiveFallId) {
        resolveFall(currentActiveFallId, status);
        currentActiveFallId = null;
    }
}

async function resolveFall(fallId, status) {
    try {
        const res = await fetch(`/api/dashboard/falls/${fallId}/resolve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                status: status,
                notes: status === 'ACKNOWLEDGED' ? "Caregiver confirmed assistance provided." : "Reviewed and marked as non-emergency false alarm."
            })
        });
        if (res.ok) {
            fetchFallHistory();
            fetchSummaryData();
        }
    } catch (e) {
        console.error("Error resolving fall:", e);
    }
}

function handleFallResolvedEvent(data) {
    fetchFallHistory();
    fetchSummaryData();
}

async function fetchInitialData() {
    try {
        await Promise.all([
            fetchSummaryData(),
            fetchTimelineData(),
            fetchFallHistory()
        ]);
    } catch (e) {
        console.error("Error loading initial data:", e);
    }
}

async function fetchSummaryData() {
    try {
        const res = await fetch("/api/dashboard/summary");
        if (!res.ok) return;
        const data = await res.json();

        document.getElementById("summaryActiveMins").innerText = `${data.active_minutes} min`;
        document.getElementById("summarySedentaryMins").innerText = `${data.sedentary_minutes} min`;
        document.getElementById("summaryRestingMins").innerText = `${data.resting_minutes} min`;
        document.getElementById("summaryIntensity").innerText = data.movement_intensity;
        document.getElementById("summaryFallCount").innerText = data.total_falls_today;

        // Update donut chart
        if (summaryPieChart) {
            summaryPieChart.data.datasets[0].data = [
                data.active_minutes || 1,
                data.sedentary_minutes || 1,
                data.resting_minutes || 1
            ];
            summaryPieChart.update();
        }

        if (data.durations) {
            updateDurationsUI(data.durations);
        }
    } catch (e) {
        console.error("Error fetching summary:", e);
    }
}

async function fetchTimelineData() {
    try {
        const res = await fetch("/api/dashboard/timeline");
        if (res.ok) {
            const list = await res.json();
            updateTimelineUI(list);
        }
    } catch (e) {
        console.error("Error fetching timeline:", e);
    }
}

async function fetchFallHistory() {
    try {
        const res = await fetch("/api/dashboard/falls");
        if (res.ok) {
            const falls = await res.json();
            updateFallHistoryTable(falls);
        }
    } catch (e) {
        console.error("Error fetching falls:", e);
    }
}

// Simulator interactive demonstration triggers
function setupSimulatorControls() {
    const activities = [
        "Walking",
        "Walking upstairs",
        "Walking downstairs",
        "Sitting",
        "Standing",
        "Lying"
    ];

    activities.forEach(act => {
        const btn = document.getElementById(`simBtn_${act.replace(/\s+/g, '_')}`);
        if (btn) {
            btn.addEventListener("click", () => setSimulatorActivity(act));
        }
    });

    const triggerFallBtn = document.getElementById("triggerFallBtn");
    if (triggerFallBtn) {
        triggerFallBtn.addEventListener("click", triggerSimulatedFall);
    }
}

async function setSimulatorActivity(activity) {
    try {
        const res = await fetch("/api/simulator/activity", {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ activity })
        });
        if (res.ok) {
            console.log("Simulator activity changed to:", activity);
        }
    } catch (e) {
        console.error("Failed to set simulator activity:", e);
    }
}

async function triggerSimulatedFall() {
    try {
        const res = await fetch("/api/simulator/fall", {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ impact_g: 3.85 })
        });
        if (res.ok) {
            console.log("Simulated fall triggered!");
        }
    } catch (e) {
        console.error("Failed to trigger fall:", e);
    }
}
