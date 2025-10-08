/* main.js - Vraćena i ispravljena verzija */
document.addEventListener("DOMContentLoaded", () => {

    // ------- DOM Elementi -------
    const loggerStatusEl = document.getElementById('loggerStatusTXT');
    const relay1StateEl = document.getElementById('relay1State');
    const relay2StateEl = document.getElementById('relay2State');
    const sensorOutputEl = document.getElementById('sensorOutput');
    const logsTableBody = document.getElementById('logsBody');
    const relayLogTableBody = document.querySelector('#relayLogTable tbody');

    // ------- HELPERI -------
    function formatTime(ts) {
        if (!ts) return "";
        const [date, time] = ts.split('_');
        if (!date || !time) return ts.replace('_', ' ');
        return `${date.split('-').reverse().join('.')} ${time.replace(/-/g, ':')}`;
    }

    async function fetchJSON(url, opts = {}) {
        try {
            const response = await fetch(url, opts);
            if (!response.ok) {
                console.error(`Greška pri dohvaćanju ${url}: ${response.status}`);
                return null;
            }
            return await response.json();
        } catch (error) {
            console.error(`Mrežna greška za ${url}:`, error);
            return null;
        }
    }

    // ------- Inicijalizacija Chartova -------
    function createChart(elementId, datasets, yAxisOptions = {}) {
        const ctx = document.getElementById(elementId).getContext('2d');
        return new Chart(ctx, {
            type: 'line',
            data: { labels: [], datasets: datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: { y: yAxisOptions },
            }
        });
    }

    const tempChart = createChart('tempChart', [
        { label: 'Temp. Zraka (°C)', borderColor: '#007bff', data: [] },
        { label: 'Temp. Zemlje (°C)', borderColor: '#28a745', data: [] }
    ]);
    const humChart = createChart('humChart', [{ label: 'Vlaga Zraka (%)', borderColor: '#ffc107', data: [] }]);
    const soilChart = createChart('soilChart', [{ label: 'Vlaga Zemlje (%)', borderColor: '#8B4513', data: [] }]);
    const luxChart = createChart('luxChart', [{ label: 'Svjetlost (lx)', borderColor: '#800080', data: [] }]);
    let relayChart = null;


    // ------- Funkcije za Ažuriranje Sučelja -------

    function updateSensorCharts(logs) {
        const labels = logs.map(r => formatTime(r.timestamp));
        tempChart.data.labels = labels;
        humChart.data.labels = labels;
        soilChart.data.labels = labels;
        luxChart.data.labels = labels;

        tempChart.data.datasets[0].data = logs.map(r => r.dht22_air_temp);
        tempChart.data.datasets[1].data = logs.map(r => r.ds18b20_soil_temp);
        humChart.data.datasets[0].data = logs.map(r => r.dht22_humidity);
        soilChart.data.datasets[0].data = logs.map(r => r.soil_percent);
        luxChart.data.datasets[0].data = logs.map(r => r.lux);

        [tempChart, humChart, soilChart, luxChart].forEach(c => c.update());
    }

    function updateLogsTable(logs) {
        logsTableBody.innerHTML = "";
        for (let i = logs.length - 1; i >= 0; i--) {
            const r = logs[i];
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${r.id}</td>
                <td>${formatTime(r.timestamp)}</td>
                <td>${r.dht22_air_temp ?? ''}</td>
                <td>${r.dht22_humidity ?? ''}</td>
                <td>${r.ds18b20_soil_temp ?? ''}</td>
                <td>${r.soil_percent ?? ''}</td>
                <td>${r.lux ?? ''}</td>`;
            logsTableBody.appendChild(tr);
        }
    }

    function updateRelayUI(data) {
        if (!data) return;

        // Ažuriranje tablice
        relayLogTableBody.innerHTML = '';
        (data.table_data || []).forEach(entry => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${entry.t}</td>
                <td>${entry.relay}</td>
                <td><span class="badge ${entry.v ? 'bg-success' : 'bg-secondary'}">${entry.action}</span></td>
                <td>${entry.source || 'button'}</td>`;
            relayLogTableBody.appendChild(tr);
        });

        // Ažuriranje grafikona
        const chartData = data.chart_data;
        if (!chartData || (!chartData.RELAY1?.length && !chartData.RELAY2?.length)) return;

		const labels = [...new Set([...chartData.RELAY1.map(x => x.t), ...chartData.RELAY2.map(x => x.t)])].sort();
		const relay1Display = chartData.RELAY1.map(d => d.v ? 1 : 0.05);
		const relay2Display = chartData.RELAY2.map(d => d.v ? 0.5 : 0.5 - 0.05);

        if (!relayChart) {
            relayChart = createChart('relayChart', [
                { label: 'Relej 1', data: relay1Display, borderColor: 'rgb(255, 99, 132)', stepped: true },
                { label: 'Relej 2', data: relay2Display, borderColor: 'rgb(54, 162, 235)', stepped: true }
            ], { min: 0, max: 1.2, ticks: { stepSize: 0.5, callback: v => (v === 1 ? 'R1 ON' : (v === 0.5 ? 'R2 ON' : '')) } });
        }

        relayChart.data.labels = labels;
        relayChart.data.datasets[0].data = relay1Display;
        relayChart.data.datasets[1].data = relay2Display;
        relayChart.update();
    }

    async function toggleRelay(relayNum) {
        const stateEl = document.getElementById(`relay${relayNum}State`);
        const currentState = stateEl.innerText.trim().toUpperCase() === 'ON';
        const newState = !currentState;

        const response = await fetchJSON('/api/relay/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ relay: relayNum, state: newState })
        });

        if (response && response.ok) {
            stateEl.innerText = newState ? 'ON' : 'OFF';
            refreshAllData();
        }
    }

    async function updateLoggerStatus() {
        const data = await fetchJSON('/api/status');
        if (data && data.status) {
            loggerStatusEl.innerText = data.status;
            loggerStatusEl.style.color = data.status.toUpperCase().includes("RUNNING") ? "green" : "red";
        } else {
            loggerStatusEl.innerText = "Greška pri dohvaćanju statusa";
            loggerStatusEl.style.color = "red";
        }
    }

    // ------- GLAVNA FUNKCIJA ZA OSVJEŽAVANJE -------
    async function refreshAllData() {
        const logs = await fetchJSON('/api/logs?limit=100');
        if (logs) {
            updateSensorCharts(logs);
            updateLogsTable(logs);
        }

        const relayData = await fetchJSON('/relay_log_data');
        if (relayData) {
            updateRelayUI(relayData);
        }

        updateLoggerStatus();
    }

    // ------- Event Listeners -------
    document.getElementById('btnDeleteRows').addEventListener('click', async () => {
        const deleteStatusEl = document.getElementById('deleteStatus');
        const idsInput = document.getElementById('deleteIdsInput').value.trim();
        if (!idsInput) {
            deleteStatusEl.textContent = "Molimo unesite ID-eve za brisanje.";
            return;
        }

        const ids = (idsInput.toLowerCase() === 'all') ? ['all'] : idsInput.split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id));

        if (ids.length === 0 && idsInput.toLowerCase() !== 'all') {
            deleteStatusEl.textContent = "Nisu pronađeni ispravni ID-evi.";
            return;
        }

        const res = await fetchJSON('/api/logs/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids: ids })
        });

        if (res) {
            deleteStatusEl.textContent = res.msg;
            if (res.ok) {
                refreshAllData();
            }
        }
    });

    document.getElementById('btnStartFirst').addEventListener('click', async () => {
        const res = await fetchJSON('/api/run/start_first', { method: 'POST' });
        if (res) updateLoggerStatus();
    });

    document.getElementById('btnStop').addEventListener('click', async () => {
        const res = await fetchJSON('/api/run/stop', { method: 'POST' });
        if (res) updateLoggerStatus();
    });

    document.getElementById('btn-relay1').addEventListener('click', () => toggleRelay(1));
    document.getElementById('btn-relay2').addEventListener('click', () => toggleRelay(2));

    ['ads', 'dht', 'ds18b20', 'bh1750'].forEach(type => {
        document.getElementById(`btn-${type}`).addEventListener('click', async () => {
            const r = await fetchJSON(`/api/sensor/read?type=${type}`);
            sensorOutputEl.innerText = JSON.stringify(r, null, 2);
        });
    });

    // ------- Inicijalno učitavanje i periodično osvježavanje -------
    refreshAllData();
    // setInterval(refreshAllData, 15000); // Uklonjeno automatsko osvježavanje na zahtjev
});