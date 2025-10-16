/* main.js - globalna JS logika */
document.addEventListener("DOMContentLoaded", () => {

    // ------- Globalni pomoćnici -------
    window.formatTime = function(ts) {
        if (!ts) return "";
        const parts = ts.split('_');
        if (parts.length < 2) return ts;
        const [date, time] = parts;
        const [y, m, d] = date.split('-');
        const [hh, mm] = time.split('-');
        return `${d}.${m}.${y.slice(-2)} ${hh}:${mm}`;
    }

    async function fetchJSON(url, opts) {
        const r = await fetch(url, opts);
        return await r.json();
    }

    // ------- Logika za promjenu teme -------
    const themeSwitcher = document.getElementById('theme-switcher');
    const docHtml = document.documentElement;
    let registeredCharts = [];

    // Funkcija za registraciju novog grafa
    window.registerChart = (chart) => {
        if (chart) {
            registeredCharts.push(chart);
        }
    }

    // Funkcija za ažuriranje boja SVIH registriranih grafova
    window.updateAllChartColors = () => {
        const theme = docHtml.getAttribute('data-theme') || 'light';
        const isDark = theme === 'dark';

        const gridColor = getComputedStyle(docHtml).getPropertyValue('--chart-grid-color').trim();
        const labelColor = getComputedStyle(docHtml).getPropertyValue('--chart-label-color').trim();

        const chartColors = {
            // Definicije boja ostaju iste...
            airTemp: { border: isDark ? '#58a6ff' : '#0d6efd', bg: isDark ? 'rgba(88, 166, 255, 0.2)' : 'rgba(0,123,255,0.1)'},
            soilTemp: { border: isDark ? '#56d364' : '#198754', bg: isDark ? 'rgba(86, 211, 100, 0.2)' : 'rgba(40,167,69,0.1)'},
            airHum: { border: isDark ? '#e3b341' : '#ffc107', bg: isDark ? 'rgba(227, 179, 65, 0.2)' : 'rgba(255,165,0,0.15)'},
            soilPercent: { border: isDark ? '#d2a679' : '#8B4513', bg: isDark ? 'rgba(210, 166, 121, 0.2)' : 'rgba(139,69,19,0.15)'},
            lux: { border: isDark ? '#c991e1' : '#800080', bg: isDark ? 'rgba(201, 145, 225, 0.2)' : 'rgba(128,0,128,0.1)'},
            relay1: { border: isDark ? '#f87171' : '#dc3545', bg: isDark ? 'rgba(248, 113, 113, 0.25)' : 'rgba(255, 99, 132, 0.25)'},
            relay2: { border: isDark ? '#60a5fa' : '#0d6efd', bg: isDark ? 'rgba(96, 165, 250, 0.25)' : 'rgba(54, 162, 235, 0.25)'},
        };

        // Funkcija za mapiranje labela na boje
        const getColor = (label) => {
            if (label.includes('Air Temp')) return chartColors.airTemp;
            if (label.includes('Soil Temp')) return chartColors.soilTemp;
            if (label.includes('Air Humidity')) return chartColors.airHum;
            if (label.includes('Soil Moisture') || label.includes('Soil %')) return chartColors.soilPercent;
            if (label.includes('Lux')) return chartColors.lux;
            if (label.includes('Relej 1')) return chartColors.relay1;
            if (label.includes('Relej 2')) return chartColors.relay2;
            return { border: 'gray', bg: 'rgba(128,128,128,0.1)' }; // Fallback
        };

        registeredCharts.forEach(chart => {
            // Ažuriranje općih opcija
            if (chart.options.scales.x) {
                chart.options.scales.x.grid.color = gridColor;
                chart.options.scales.x.ticks.color = labelColor;
            }
            if (chart.options.scales.y) {
                chart.options.scales.y.grid.color = gridColor;
                chart.options.scales.y.ticks.color = labelColor;
            }
            if (chart.options.plugins.legend) {
                chart.options.plugins.legend.labels.color = labelColor;
            }

            // Ažuriranje boja dataseta
            chart.data.datasets.forEach(dataset => {
                const colors = getColor(dataset.label);
                dataset.borderColor = colors.border;
                dataset.backgroundColor = colors.bg;
            });

            chart.update();
        });
    }

    function setTheme(theme) {
        docHtml.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        if (themeSwitcher) {
            themeSwitcher.textContent = theme === 'dark' ? '☀️' : '🌙';
        }
        window.updateAllChartColors();
    }

    if (themeSwitcher) {
        themeSwitcher.addEventListener('click', () => {
            const currentTheme = docHtml.getAttribute('data-theme') || 'light';
            setTheme(currentTheme === 'light' ? 'dark' : 'light');
        });
    }

    // ------- Logika specifična za glavnu stranicu (index.html) -------
    function initIndexPage() {
        // Pokreni samo na glavnoj stranici
        if (!document.getElementById('chart-wrap')) return;

        const commonChartOptions = {
            responsive: true, maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: { y: { min: 0 } }
        };

        const tempChart = new Chart(document.getElementById('tempChart').getContext('2d'), {
            type: 'line', data: { labels: [], datasets: [
                { label: 'Air Temp °C', data: [], fill: true, tension: 0.2 },
                { label: 'Soil Temp °C', data: [], fill: true, tension: 0.2 }
            ]},
            options: { ...commonChartOptions, scales: { y: { min: 0, max: 50 } } }
        });
        const humChart = new Chart(document.getElementById('humChart').getContext('2d'), {
             type: 'line', data: { labels: [], datasets: [{ label: 'Air Humidity %', data: [], fill: true, tension: 0.2 }] },
             options: { ...commonChartOptions, scales: { y: { min: 0, max: 100 } } }
        });
        const soilChart = new Chart(document.getElementById('soilChart').getContext('2d'), {
            type: 'line', data: { labels: [], datasets: [{ label: 'Soil %', data: [], fill: true, tension: 0.2 }] },
            options: { ...commonChartOptions, scales: { y: { min: 0, max: 100 } } }
        });
        const luxChart = new Chart(document.getElementById('luxChart').getContext('2d'), {
            type: 'line', data: { labels: [], datasets: [{ label: 'Lux (lx)', data: [], fill: true, tension: 0.2 }] },
            options: { ...commonChartOptions }
        });

        // Registriraj grafikone za praćenje teme
        [tempChart, humChart, soilChart, luxChart].forEach(window.registerChart);

        let relayChart = null; // Specifično za ovu stranicu

        async function updateChartAndTable() {
            const rows = await fetchJSON('/api/logs?limit=100');
            const labels = rows.map(r => window.formatTime(r.timestamp));

            // Ažuriranje podataka grafikona
            tempChart.data.labels = labels;
            tempChart.data.datasets[0].data = rows.map(r => r.air_temp);
            tempChart.data.datasets[1].data = rows.map(r => r.soil_temp);

            humChart.data.labels = labels;
            humChart.data.datasets[0].data = rows.map(r => r.air_humidity);

            soilChart.data.labels = labels;
            soilChart.data.datasets[0].data = rows.map(r => r.soil_percent);

            luxChart.data.labels = labels;
            luxChart.data.datasets[0].data = rows.map(r => r.lux);

            [tempChart, humChart, soilChart, luxChart].forEach(c => c.update());

            // Ažuriranje tablice
            const tbody = document.getElementById('logsBody');
            if (tbody) {
                tbody.innerHTML = "";
                rows.slice().reverse().forEach(r => {
                    const tr = document.createElement('tr');
                    if (r.stable === 0) tr.classList.add('unstable');
                    tr.innerHTML = `<td>${r.id}</td><td>${window.formatTime(r.timestamp)}</td><td>${r.air_temp ?? ''}</td><td>${r.air_humidity ?? ''}</td><td>${r.soil_temp ?? ''}</td><td>${r.soil_percent ?? ''}</td><td>${r.lux ?? ''}</td>`;
                    tbody.appendChild(tr);
                });
            }
             window.updateAllChartColors();
        }

        // ... ostale funkcije i event listeneri za index.html
         // ------- Ovdje idu ostale funkcije i event listeneri specifični za index.html -------
        // (npr. loadRelayLogTable, toggleRelay, updateLoggerStatus, readSensor, itd.)
        // Važno je da svaka od njih provjerava postojanje elemenata s kojima radi.

        async function loadRelayLogTable() {
            const tbody = document.querySelector('#relayLogTable tbody');
            if (!tbody) return;
            const data = await fetchJSON('/relay_log_data');
            tbody.innerHTML = '';
            (data || []).forEach(entry => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${entry.t}</td><td>${entry.relay}</td><td><span class="badge ${entry.v ? 'bg-success' : 'bg-secondary'}">${entry.action}</span></td><td>${entry.source || 'button'}</td>`;
                tbody.appendChild(tr);
            });
        }

        async function toggleRelay(relay) {
            const stateEl = document.getElementById(`relay${relay}State`);
            if (!stateEl) return;
            const cur = stateEl.innerText === 'ON';
            await fetch('/api/relay/toggle', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ relay: relay, state: !cur })
            });
            stateEl.innerText = !cur ? 'ON' : 'OFF';
            loadRelayLogTable();
        }

        async function updateLoggerStatus() {
            const el = document.getElementById('loggerStatusTXT');
            if (!el) return;
            try {
                const data = await fetchJSON('/api/status');
                el.innerText = data.status;
                el.style.color = data.status.includes(" u ") ? "green" : "red";
            } catch (e) {
                el.innerText = "Greška pri dohvaćanju statusa";
                el.style.color = "red";
            }
        }

        // Event listeneri
        const btnStartFirst = document.getElementById('btnStartFirst');
        if (btnStartFirst) btnStartFirst.addEventListener('click', async () => {
            const res = await fetchJSON('/api/run/start_first', { method: 'POST' });
            const statusEl = document.getElementById('loggerStatus');
            if (statusEl) statusEl.innerText = res.running ? "AKTIVAN" : "STOPIRAN";
        });

        const btnStop = document.getElementById('btnStop');
        if (btnStop) btnStop.addEventListener('click', async () => {
            const res = await fetchJSON('/api/run/stop', { method: 'POST' });
            const statusEl = document.getElementById('loggerStatus');
            if(statusEl) statusEl.innerText = res.running ? "AKTIVAN" : "STOPIRAN";
        });

        // Ostali listeneri...
        ['ads', 'dht', 'ds18b20', 'bh1750'].forEach(type => {
            const btn = document.getElementById(`btn-${type}`);
            if (btn) btn.addEventListener('click', () => {
                const outputEl = document.getElementById('sensorOutput');
                if (outputEl) fetchJSON(`/api/sensor/read?type=${type}`).then(r => outputEl.innerText = JSON.stringify(r, null, 2));
            });
        });

        const btnRelay1 = document.getElementById('btn-relay1');
        if (btnRelay1) btnRelay1.addEventListener('click', () => toggleRelay(1));

        const btnRelay2 = document.getElementById('btn-relay2');
        if (btnRelay2) btnRelay2.addEventListener('click', () => toggleRelay(2));

        // Inicijalno učitavanje
        updateLoggerStatus();
        updateChartAndTable();
        loadRelayLogTable();
    }

    // ------- Logika za brisanje (zajednička za obje stranice) -------
    const btnDeleteRows = document.getElementById('btnDeleteRows');
    if (btnDeleteRows) {
        btnDeleteRows.addEventListener('click', async () => {
            const inputEl = document.getElementById('deleteIdsInput');
            const statusEl = document.getElementById('deleteStatus');
            if (!inputEl || !statusEl) return;

            const input = inputEl.value.trim();
            if (!input) {
                statusEl.innerText = "Unesite ID-eve za brisanje ili 'all'.";
                return;
            }

            if (!confirm(`Jeste li sigurni da želite obrisati ${input === "all" ? "SVE redove" : "ove redove: " + input}?`)) return;

            try {
                const res = await fetchJSON('/api/logs/delete', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ids: input })
                });
                statusEl.innerText = res.ok ? `Obrisano: ${res.deleted === "all" ? "svi redovi" : res.deleted + " redova."}` : `Greška: ${res.msg || res.error}`;
                // Ako postoji globalna funkcija za ponovno učitavanje podataka, pozovi je
                if (res.ok && window.loadData) {
                    window.loadData();
                } else if (res.ok && window.updateChartAndTable) {
                    window.updateChartAndTable();
                }
            } catch (e) {
                statusEl.innerText = "Greška pri brisanju: " + e.message;
            }
        });
    }

    // ------- Inicijalizacija -------
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);

    // Pokreni logiku specifičnu za stranicu
    initIndexPage();
});
