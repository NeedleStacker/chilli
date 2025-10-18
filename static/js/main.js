/* main.js - Unificirana JS logika za cijelu aplikaciju */

document.addEventListener("DOMContentLoaded", () => {
    // ------- Globalni Chart.js Setup -------
    let chartInstances = {}; // Objekt za praćenje svih instanci grafikona

    // Funkcija za dohvaćanje boja iz CSS varijabli
    const getCssVar = (varName) => getComputedStyle(document.documentElement).getPropertyValue(varName).trim();

    // Defaultne opcije za sve grafikone
    const getDefaultChartOptions = () => ({
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
            legend: { labels: { color: getCssVar('--text-color') } }
        },
        scales: {
            y: {
                ticks: { color: getCssVar('--text-color'), stepSize: 10 },
                grid: { color: getCssVar('--card-border-color') },
                min: 0, // Default min vrijednost
                max: 100 // Default max vrijednost
            },
            x: {
                ticks: { color: getCssVar('--text-color') },
                grid: { color: getCssVar('--card-border-color') }
            }
        }
    });

    // Kreira ili ažurira grafikon s novim podacima i opcijama
    function createOrUpdateChart(canvasId, type, data, options) {
        if (chartInstances[canvasId]) {
            chartInstances[canvasId].data = data;
            chartInstances[canvasId].options = options;
            chartInstances[canvasId].update();
        } else {
            const ctx = document.getElementById(canvasId).getContext('2d');
            chartInstances[canvasId] = new Chart(ctx, { type, data, options });
        }
    }

    // Ponovno iscrtava sve grafikone (korisno kod promjene teme)
    function redrawAllCharts() {
        for (const canvasId in chartInstances) {
            const chart = chartInstances[canvasId];
            chart.options = getDefaultChartOptions(); // Ponovno primijeni opcije
            // Specifične opcije po grafikonu se moraju ponovno postaviti ako je potrebno
            if (canvasId === 'tempChart' || canvasId === 'soilTempChart') chart.options.scales.y.max = 50;
            chart.update();
        }
    }

    // ------- Theme Switcher Logic -------
    function initThemeSwitcher() {
        const themeSelect = document.getElementById('theme-select');
        const currentTheme = localStorage.getItem('theme') || 'light';

        function applyTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
            themeSelect.value = theme;
            // Daj CSS-u trenutak da primijeni varijable prije iscrtavanja
            setTimeout(redrawAllCharts, 50);
        }

        themeSelect.addEventListener('change', (e) => applyTheme(e.target.value));
        applyTheme(currentTheme);
    }

    // ------- Glavni Router -------
    function init() {
        initThemeSwitcher();
        if (document.getElementById('tempChart')) initIndexPage();
        if (document.getElementById('whereInput')) initAllDataPage();
    }

    // ------- Pomoćne (Helper) Funkcije -------
    function formatTime(ts) {
        if (!ts) return "";
        const [date, timeDetails] = ts.split('_');
        if (!date || !timeDetails) return ts;
        const [y, m, d] = date.split('-');
        const [hh, mm] = timeDetails.split('-');
        return `${d}.${m}.${y.slice(-2)} ${hh}:${mm}`;
    }

    async function fetchJSON(url, opts) {
        const r = await fetch(url, opts);
        if (!r.ok) throw new Error(`HTTP error! status: ${r.status}`);
        return await r.json();
    }

    // ------- Logika za Brisanje Redova (zajednička) -------
    async function setupDeleteRowsHandler(callbackOnSuccess) {
        const btn = document.getElementById('btnDeleteRows');
        if (!btn) return;
        btn.addEventListener('click', async () => {
            const inputEl = document.getElementById('deleteIdsInput');
            const statusEl = document.getElementById('deleteStatus');
            const input = inputEl.value.trim();
            if (!input) {
                statusEl.innerText = "Unesite ID-eve za brisanje ili 'all'.";
                return;
            }
            const payload = { ids: input.toLowerCase() === "all" ? "all" : input };
            const confirmDelete = confirm(`Jeste li sigurni da želite obrisati ${input === "all" ? "SVE redove" : "ove redove: " + input}?`);
            if (!confirmDelete) return;
            try {
                const data = await fetchJSON('/api/logs/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (data.ok) {
                    statusEl.innerText = `Obrisano: ${data.deleted === "all" ? "svi redovi" : data.deleted + " redova."}`;
                    if (callbackOnSuccess) await callbackOnSuccess();
                } else {
                    statusEl.innerText = `Greška: ${data.msg || data.error}`;
                }
            } catch (e) {
                statusEl.innerText = "Greška pri brisanju: " + e.message;
            }
        });
    }

    // ====================================================================
    // INICIJALIZACIJA ZA INDEX.HTML
    // ====================================================================
    function initIndexPage() {
        async function updateIndexPageData() {
            const rows = await fetchJSON('/api/logs?limit=100');
            const labels = rows.map(r => formatTime(r.timestamp));

            // Ažuriranje tablice
            const tbody = document.getElementById('logsBody');
            tbody.innerHTML = "";
            rows.slice().reverse().forEach(r => {
                const tr = document.createElement('tr');
                if (r.stable === 0) tr.classList.add('unstable');
                tr.innerHTML = `<td>${r.id}</td><td>${formatTime(r.timestamp)}</td><td>${r.air_temp ?? ''}</td><td>${r.air_humidity ?? ''}</td><td>${r.soil_temp ?? ''}</td><td>${r.soil_percent ?? ''}</td><td>${r.lux ?? ''}</td>`;
                tbody.appendChild(tr);
            });

            // Ažuriranje grafikona
            const tempOptions = getDefaultChartOptions();
            tempOptions.scales.y.max = 50;
            createOrUpdateChart('tempChart', 'line', {
                labels,
                datasets: [
                    { label: 'Air Temp °C', data: rows.map(r => r.air_temp), borderColor: 'rgba(0,123,255,1)', tension: 0.2, fill: false },
                    { label: 'Soil Temp °C', data: rows.map(r => r.soil_temp), borderColor: 'rgba(40,167,69,1)', tension: 0.2, fill: false }
                ]
            }, tempOptions);

            createOrUpdateChart('humChart', 'line', {
                labels,
                datasets: [{ label: 'Air Humidity %', data: rows.map(r => r.air_humidity), borderColor: 'rgba(255,165,0,1)', tension: 0.2, fill: false }]
            }, getDefaultChartOptions());

            createOrUpdateChart('soilChart', 'line', {
                labels,
                datasets: [{ label: 'Soil %', data: rows.map(r => r.soil_percent), borderColor: 'rgba(139,69,19,1)', tension: 0.2, fill: false }]
            }, getDefaultChartOptions());

            const luxOptions = getDefaultChartOptions();
            luxOptions.scales.y.max = undefined; // Ukloni max za Lux
            createOrUpdateChart('luxChart', 'line', {
                labels,
                datasets: [{ label: 'Lux (lx)', data: rows.map(r => r.lux), borderColor: 'rgba(128,0,128,1)', tension: 0.2, fill: false }]
            }, luxOptions);
        }

        async function readSensor(type) {
            const r = await fetchJSON(`/api/sensor/read?type=${type}`);
            document.getElementById('sensorOutput').innerText = JSON.stringify(r, null, 2);
        }

        async function toggleRelay(relay) {
            const stateEl = document.getElementById(`relay${relay}State`);
            const target = stateEl.innerText !== 'ON';
            await fetchJSON('/api/relay/toggle', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ relay, state: target }) });
            stateEl.innerText = target ? 'ON' : 'OFF';
            loadRelayLogTable();
        }

        async function loadRelayLogTable() {
            const data = await fetchJSON('/relay_log_data');
            const tbody = document.querySelector('#relayLogTable tbody');
            tbody.innerHTML = '';
            (data || []).forEach(entry => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${entry.t}</td><td>${entry.relay}</td><td><span class="badge ${entry.v ? 'bg-success' : 'bg-secondary'}">${entry.action}</span></td><td>${entry.source || 'button'}</td>`;
                tbody.appendChild(tr);
            });
        }

        async function updateLoggerStatus() {
            try {
                const data = await fetchJSON('/api/status');
                const el = document.getElementById('loggerStatusTXT');
                el.innerText = data.status;
                el.style.color = data.status.includes(" u ") ? "green" : "red";
            } catch (e) {
                const el = document.getElementById('loggerStatusTXT');
                el.innerText = "Greška pri dohvaćanju statusa";
                el.style.color = "red";
            }
        }

        // Event Listeners
        document.getElementById('btnStartFirst').addEventListener('click', async () => {
            const res = await fetchJSON('/api/run/start_first', { method: 'POST' });
            document.getElementById('loggerStatus').innerText = res.running ? "AKTIVAN" : "STOPIRAN";
        });
        document.getElementById('btnStop').addEventListener('click', async () => {
            const res = await fetchJSON('/api/run/stop', { method: 'POST' });
            document.getElementById('loggerStatus').innerText = res.running ? "AKTIVAN" : "STOPIRAN";
        });
        ['ads', 'dht', 'ds18b20', 'bh1750'].forEach(id => document.getElementById(`btn-${id}`).addEventListener('click', () => readSensor(id)));
        [1, 2].forEach(num => document.getElementById(`btn-relay${num}`).addEventListener('click', () => toggleRelay(num)));
        setupDeleteRowsHandler(updateIndexPageData);

        // Inicijalno učitavanje
        updateLoggerStatus();
        updateIndexPageData();
        loadRelayLogTable();
    }

    // ====================================================================
    // INICIJALIZACIJA ZA ALL_DATA.HTML
    // ====================================================================
    function initAllDataPage() {
        const whereInput = document.getElementById('whereInput');
        const daysInput = document.getElementById('days-input');

        const generateDateFilter = (days) => {
            const endDate = new Date();
            const startDate = new Date();
            startDate.setDate(endDate.getDate() - days);
            const formatDate = d => d.toISOString().split('T')[0];
            return `timestamp BETWEEN '${formatDate(startDate)}' AND '${formatDate(endDate)}'`;
        };

        async function loadAllData() {
            const where = whereInput.value.trim();
            const url = where ? `/api/logs/all?where=${encodeURIComponent(where)}` : '/api/logs/all';
            const data = await fetchJSON(url);

            const labels = data.map(r => formatTime(r.timestamp));

            const tempOptions = getDefaultChartOptions(); tempOptions.scales.y.max = 50;
            const luxOptions = getDefaultChartOptions(); luxOptions.scales.y.max = undefined;

            createOrUpdateChart('airTempChart', 'line', { labels, datasets: [{ label: 'Air Temperature (°C)', data: data.map(r => r.air_temp), borderColor: 'blue', tension: 0.2, fill: false }] }, tempOptions);
            createOrUpdateChart('airHumidityChart', 'line', { labels, datasets: [{ label: 'Air Humidity (%)', data: data.map(r => r.air_humidity), borderColor: 'skyblue', tension: 0.2, fill: false }] }, getDefaultChartOptions());
            createOrUpdateChart('soilTempChart', 'line', { labels, datasets: [{ label: 'Soil Temperature (°C)', data: data.map(r => r.soil_temp), borderColor: 'orange', tension: 0.2, fill: false }] }, tempOptions);
            createOrUpdateChart('soilMoistureChart', 'line', { labels, datasets: [{ label: 'Soil Moisture (%)', data: data.map(r => r.soil_percent), borderColor: 'green', tension: 0.2, fill: false }] }, getDefaultChartOptions());
            createOrUpdateChart('luxChart', 'line', { labels, datasets: [{ label: 'Lux', data: data.map(r => r.lux), borderColor: 'purple', tension: 0.2, fill: false }] }, luxOptions);

            const tbody = document.getElementById('logsBody');
            tbody.innerHTML = "";
            data.slice().reverse().forEach(r => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${r.id}</td><td>${formatTime(r.timestamp)}</td><td>${r.air_temp ?? ''}</td><td>${r.air_humidity ?? ''}</td><td>${r.soil_temp ?? ''}</td><td>${r.soil_percent ?? ''}</td><td>${r.lux ?? ''}</td><td>${r.stable ? 'DA' : 'NE'}</td>`;
                tbody.appendChild(tr);
            });

            const stats = (data => ({
                air_temp: (arr => arr.reduce((a, b) => a + b, 0) / arr.length)(data.map(r => r.air_temp).filter(v => v !== null)),
                air_humidity: (arr => arr.reduce((a, b) => a + b, 0) / arr.length)(data.map(r => r.air_humidity).filter(v => v !== null)),
                soil_temp: (arr => arr.reduce((a, b) => a + b, 0) / arr.length)(data.map(r => r.soil_temp).filter(v => v !== null)),
                soil_percent: (arr => arr.reduce((a, b) => a + b, 0) / arr.length)(data.map(r => r.soil_percent).filter(v => v !== null)),
                lux: (arr => arr.reduce((a, b) => a + b, 0) / arr.length)(data.map(r => r.lux).filter(v => v !== null)),
            }))(data);
            document.getElementById('stats').innerText = JSON.stringify(stats, (key, value) => (typeof value === 'number' ? value.toFixed(2) : value), 2);
        }

        const updateDaysAndReload = (change) => {
            let currentDays = parseInt(daysInput.value, 10) || 30;
            currentDays += change;
            if (currentDays < 1) currentDays = 1;
            daysInput.value = currentDays;
            whereInput.value = generateDateFilter(currentDays);
            loadAllData();
        };

        // Event Listeners
        document.getElementById('filterBtn').addEventListener('click', loadAllData);
        document.getElementById('btn-days-minus-5').addEventListener('click', () => updateDaysAndReload(-5));
        document.getElementById('btn-days-plus-5').addEventListener('click', () => updateDaysAndReload(5));
        daysInput.addEventListener('change', () => {
            const days = parseInt(daysInput.value, 10) || 30;
            if (days < 1) daysInput.value = 1;
            whereInput.value = generateDateFilter(days);
            loadAllData();
        });

        setupDeleteRowsHandler(loadAllData);

        // Inicijalno učitavanje
        whereInput.value = generateDateFilter(30);
        loadAllData();
    }

    // Pokreni aplikaciju
    init();
});
