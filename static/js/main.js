/* main.js - glavni JS logika za index.html */
/* Ovaj fajl mora se učitati nakon Chart.js (CDN) i nakon što su HTML elementi u DOM-u. */

document.addEventListener("DOMContentLoaded", () => {
    // ------- THEME SWITCHER LOGIC -------
    const themeDropdown = document.getElementById('themeDropdown');
    const currentTheme = localStorage.getItem('theme') || 'dark';

    const applyTheme = (theme) => {
        document.documentElement.setAttribute('data-theme', theme);
        if (themeDropdown) {
            themeDropdown.textContent = theme.charAt(0).toUpperCase() + theme.slice(1);
        }
    };

    applyTheme(currentTheme);

    document.querySelectorAll('.theme-select').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const theme = item.getAttribute('data-theme');
            applyTheme(theme);
            localStorage.setItem('theme', theme);
        });
    });

	// ------- helperi -------
	function formatTime(ts) {
		if (!ts) return "";
		const [date, time] = ts.split('_');
		if (!date || !time) return ts;
		const [y, m, d] = date.split('-');
		const [hh, mm] = time.split('-');
		return `${d}.${m}.${y.slice(-2)} ${hh}:${mm}`;
	}

	async function fetchJSON(url, opts) {
		const r = await fetch(url, opts);
		return await r.json();
	}

	// ------- Chart Theming -------
	const getThemeColors = () => {
		const theme = document.documentElement.getAttribute('data-theme') || 'dark';
		if (theme === 'dark') {
			return {
				backgroundColor: '#2a2a2a',
				borderColor: '#0dcaf0',
				gridColor: 'rgba(255, 255, 255, 0.1)',
				textColor: '#e0e0e0'
			};
		}
		return {
			backgroundColor: '#f8f9fa',
			borderColor: '#0d6efd',
			gridColor: 'rgba(0, 0, 0, 0.1)',
			textColor: '#212529'
		};
	};

	// ------- inicijalizacija chartova -------
	const ctxTemp = document.getElementById('tempChart').getContext('2d');
	const createChartOptions = () => {
		const themeColors = getThemeColors();
		return {
			responsive: true,
			maintainAspectRatio: false,
			interaction: { mode: 'index', intersect: false },
			scales: {
				y: {
					ticks: { color: themeColors.textColor },
					grid: { color: themeColors.gridColor }
				},
				x: {
					ticks: { color: themeColors.textColor },
					grid: { color: themeColors.gridColor }
				}
			},
			plugins: {
				legend: { labels: { color: themeColors.textColor } }
			}
		};
	};

	const tempChart = new Chart(ctxTemp, {
		type: 'line',
		data: {
			labels: [],
			datasets: [
				{
					label: 'Air Temp °C',
					borderColor: 'rgba(0,123,255,1)',
					backgroundColor: 'rgba(0,123,255,0.1)',
					data: [],
					fill: true,
					tension: 0.2
				},
				{
					label: 'Soil Temp °C',
					borderColor: 'rgba(40,167,69,1)',
					backgroundColor: 'rgba(40,167,69,0.1)',
					data: [],
					fill: true,
					tension: 0.2
				}
			]
		},
		options: createChartOptions()
	});

	const ctxHum = document.getElementById('humChart').getContext('2d');
	const humChart = new Chart(ctxHum, {
		type: 'line',
		data: {
			labels: [],
			datasets: [{
				label: 'Air Humidity %',
				borderColor: 'rgba(255,165,0,1)',
				backgroundColor: 'rgba(255,165,0,0.15)',
				data: [],
				fill: true,
				tension: 0.2
			}]
		},
		options: createChartOptions()
	});

	const ctxSoil = document.getElementById('soilChart').getContext('2d');
	const soilChart = new Chart(ctxSoil, {
		type: 'line',
		data: {
			labels: [],
			datasets: [{
				label: 'Soil %',
				borderColor: 'rgba(139,69,19,1)',
				backgroundColor: 'rgba(139,69,19,0.15)',
				data: [],
				fill: true,
				tension: 0.2
			}]
		},
		options: createChartOptions()
	});

	const ctxLux = document.getElementById('luxChart').getContext('2d');
	const luxChart = new Chart(ctxLux, {
		type: 'line',
		data: {
			labels: [],
			datasets: [{
				label: 'Lux (lx)',
				borderColor: 'rgba(128,0,128,1)',
				backgroundColor: 'rgba(128,0,128,0.1)',
				data: [],
				fill: true,
				tension: 0.2
			}]
		},
		options: createChartOptions()
	});

    const allCharts = [tempChart, humChart, soilChart, luxChart];
    const updateAllChartsTheme = () => {
        const newOptions = createChartOptions();
        allCharts.forEach(chart => {
            chart.options = newOptions;
            chart.update();
        });
    };

    // Update charts when theme changes
    document.querySelectorAll('.theme-select').forEach(item => {
        item.addEventListener('click', () => {
            // timeout to allow theme to apply before redrawing
            setTimeout(updateAllChartsTheme, 50);
        });
    });


	// ------- Grafikon paljenja/gasenja releja (signal) -------
	let relayChart = null;
	async function loadRelayChart() {
		const res = await fetch('/relay_log_data');
		const data = await res.json();

		if (!data || (!data.RELAY1?.length && !data.RELAY2?.length)) return;

		const labels = [...new Set([
			...data.RELAY1.map(x => x.t),
			...data.RELAY2.map(x => x.t)
		])].sort();

		const relay1 = data.RELAY1.map(d => d.v);
		const relay2 = data.RELAY2.map(d => d.v);

		const offset = 0.05;
		const relay1Display = relay1.map(v => v ? 1 : offset);
		const relay2Display = relay2.map(v => v ? 0.5 : 0.5 - offset);

		// calc durations for last ON period (best-effort)
		const calcDuration = (arr) => {
			if (!arr || !arr.length) return null;
			// find latest ON index and last OFF before it
			let lastOnIdx = -1,
				lastOffIdx = -1;
			for (let i = arr.length - 1; i >= 0; i--) {
				if (arr[i].v === 1 && lastOnIdx === -1) lastOnIdx = i;
				if (arr[i].v === 0 && lastOnIdx !== -1) {
					lastOffIdx = i;
					break;
				}
			}
			if (lastOnIdx === -1) return null;
			// compute seconds difference using today date (HH:MM:SS -> Date)
			const onTime = arr[lastOnIdx].t;
			const offTime = lastOffIdx === -1 ? null : arr[lastOffIdx].t;
			try {
				const nowDate = new Date();
				const parseT = (hhmmss) => {
					const parts = hhmmss.split(':');
					if (parts.length < 3) return null;
					const dt = new Date(nowDate.getFullYear(), nowDate.getMonth(), nowDate.getDate(),
						parseInt(parts[0]), parseInt(parts[1]), parseInt(parts[2]));
					return dt;
				};
				const tOn = parseT(onTime);
				const tOff = offTime ? parseT(offTime) : null;
				if (!tOn) return null;
				const diff = tOff ? (tOn - tOff) / 1000 : (Date.now() - tOn.getTime()) / 1000;
				return Math.max(0, diff).toFixed(1);
			} catch (e) {
				return null;
			}
		};

		const d1 = calcDuration(data.RELAY1);
		const d2 = calcDuration(data.RELAY2);

		const durEl = document.getElementById('relayDurations');
		if (durEl) {
			let html = "";
			if (d1) html += `Relej 1 bio uključen <b>${d1}s</b>`;
			if (d2) html += (html ? " &nbsp;&nbsp;|&nbsp;&nbsp; " : "") + `Relej 2 bio uključen <b>${d2}s</b>`;
			durEl.innerHTML = html;
		}

		if (!relayChart) {
			const ctx = document.getElementById('relayChart').getContext('2d');
			relayChart = new Chart(ctx, {
				type: 'line',
				data: {
					labels: labels,
					datasets: [{
							label: 'Relej 1',
							data: relay1Display,
							borderColor: 'rgb(255, 99, 132)',
							backgroundColor: 'rgba(255, 99, 132, 0.25)',
							fill: true,
							stepped: true,
							tension: 0,
							borderWidth: 3
						},
						{
							label: 'Relej 2',
							data: relay2Display,
							borderColor: 'rgb(54, 162, 235)',
							backgroundColor: 'rgba(54, 162, 235, 0.25)',
							fill: true,
							stepped: true,
							tension: 0,
							borderWidth: 3
						}
					]
				},
				options: {
					responsive: true,
					maintainAspectRatio: true,
					aspectRatio: 3,
					scales: {
						y: {
							min: 0,
							max: 1.2,
							ticks: {
								stepSize: 0.5,
								callback: v => {
									if (v === 1) return 'Relej 1 ON';
									if (v === 0.5) return 'Relej 2 ON';
									return '';
								}
							},
							grid: {
								color: 'rgba(180,180,180,0.2)'
							},
							title: {
								display: true,
								text: 'Stanja releja'
							}
						},
						x: {
							title: {
								display: true,
								text: 'Vrijeme'
							},
							grid: {
								color: 'rgba(180,180,180,0.1)'
							}
						}
					},
					plugins: {
						legend: {
							position: 'top'
						},
						title: {
							display: false
						}
					}
				}
			});
		} else {
			relayChart.data.labels = labels;
			relayChart.data.datasets[0].data = relay1Display;
			relayChart.data.datasets[1].data = relay2Display;
			relayChart.update();
		}
	} // loadRelayChart


	// ------- tablica relej logova (sada očekuje array sorted by time) -------
	async function loadRelayLogTable() {
		const res = await fetch('/relay_log_data');
		const data = await res.json();

		const tbody = document.querySelector('#relayLogTable tbody');
		tbody.innerHTML = '';

		(data || []).forEach(entry => {
			const tr = document.createElement('tr');
			tr.innerHTML = `
        <td>${entry.t}</td>
        <td>${entry.relay}</td>
        <td>
          <span class="badge ${entry.v ? 'bg-success' : 'bg-secondary'}">
            ${entry.action}
          </span>
        </td>
        <td>${entry.source || 'button'}</td>
      `;
			tbody.appendChild(tr);
		});
	}

	window.loadRelayLogTable = loadRelayLogTable; // exposable if needed

	// ------- ostali handleri i funkcije -------
	async function updateChartAndTable() {
		const rows = await fetchJSON('/api/logs?limit=100');

		const labels = rows.map(r => formatTime(r.timestamp));
		const airT = rows.map(r => r.air_temp !== null ? Number(r.air_temp) : null);
		const airH = rows.map(r => r.air_humidity !== null ? Number(r.air_humidity) : null);
		const soilT = rows.map(r => r.soil_temp !== null ? Number(r.soil_temp) : null);
		const soilP = rows.map(r => r.soil_percent !== null ? Number(r.soil_percent) : null);
		const lux = rows.map(r => r.lux !== null ? Number(r.lux) / 100.0 : null);

		// tablica logs
		const tbody = document.getElementById('logsBody');
		tbody.innerHTML = "";

		for (let i = rows.length - 1; i >= 0; i--) {
			const r = rows[i];
			const tr = document.createElement('tr');
			if (r.stable === 0) tr.classList.add('unstable');
			tr.innerHTML = `
        <td>${r.id}</td>
        <td>${formatTime(r.timestamp)}</td>
        <td>${r.air_temp ?? ''}</td>
        <td>${r.air_humidity ?? ''}</td>
        <td>${r.soil_temp ?? ''}</td>
        <td>${r.soil_percent ?? ''}</td>
        <td>${r.lux ?? ''}</td>`;
			tbody.appendChild(tr);
		}

		tempChart.data.labels = labels;
		tempChart.data.datasets[0].data = airT;
		tempChart.data.datasets[1].data = soilT;
		tempChart.update();

		humChart.data.labels = labels;
		humChart.data.datasets[0].data = airH;
		humChart.update();

		soilChart.data.labels = labels;
		soilChart.data.datasets[0].data = soilP;
		soilChart.update();

		luxChart.data.labels = labels;
		luxChart.data.datasets[0].data = lux.map(v => v !== null ? v * 100 : null);
		luxChart.update();
	}

	async function readSensor(type) {
		const r = await fetch(`/api/sensor/read?type=${type}`).then(r => r.json());
		document.getElementById('sensorOutput').innerText = JSON.stringify(r, null, 2);
	}

	async function toggleRelay(relay) {
		const cur = relay === 1 ? document.getElementById('relay1State').innerText === 'ON' : document.getElementById('relay2State').innerText === 'ON';
		const target = !cur;
		await fetch('/api/relay/toggle', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				relay: relay,
				state: target
			})
		});
		document.getElementById('relay1State').innerText = relay === 1 ? (target ? 'ON' : 'OFF') : document.getElementById('relay1State').innerText;
		document.getElementById('relay2State').innerText = relay === 2 ? (target ? 'ON' : 'OFF') : document.getElementById('relay2State').innerText;
		loadRelayLogTable();
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

	// event listeners (button events)
	document.getElementById('btnStartFirst').addEventListener('click', async () => {
		const res = await fetch('/api/run/start_first', {
			method: 'POST'
		}).then(r => r.json());
		document.getElementById('loggerStatus').innerText = res.running ? "AKTIVAN" : "STOPIRAN";
	});
	document.getElementById('btnStop').addEventListener('click', async () => {
		const res = await fetch('/api/run/stop', {
			method: 'POST'
		}).then(r => r.json());
		document.getElementById('loggerStatus').innerText = res.running ? "AKTIVAN" : "STOPIRAN";
	});

	document.getElementById('btnDeleteRows').addEventListener('click', async () => {
		const input = document.getElementById('deleteIdsInput').value.trim();
		const statusEl = document.getElementById('deleteStatus');

		if (!input) {
			statusEl.innerText = "Unesite ID-eve za brisanje ili 'all'.";
			return;
		}

		const payload = input.toLowerCase() === "all" ? {
			ids: "all"
		} : {
			ids: input
		};

		const confirmDelete = confirm(`Jeste li sigurni da želite obrisati ${input === "all" ? "SVE redove" : "ove redove: " + input}?`);
		if (!confirmDelete) return;

		try {
			const res = await fetch('/api/logs/delete', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(payload)
			});
			const data = await res.json();

			if (data.ok) {
				statusEl.innerText = `Obrisano: ${data.deleted === "all" ? "svi redovi" : data.deleted + " redova."}`;
				await updateChartAndTable(); // osvježi tablicu i grafove
			} else {
				statusEl.innerText = `Greška: ${data.msg || data.error}`;
			}
		} catch (e) {
			statusEl.innerText = "Greška pri brisanju: " + e.message;
		}
	});

	document.getElementById('btn-ads').addEventListener('click', function() {
        readSensor('ads');
    });
    document.getElementById('btn-dht').addEventListener('click', function() {
        readSensor('dht');
    });
    document.getElementById('btn-ds18b20').addEventListener('click', function() {
        readSensor('ds18b20');
    });
    document.getElementById('btn-bh1750').addEventListener('click', function() {
        readSensor('bh1750');
    });
	document.getElementById('btn-relay1').addEventListener('click', function () {
	toggleRelay(1);
	});

	document.getElementById('btn-relay2').addEventListener('click', function () {
		toggleRelay(2);
	});

	// učitaj stvari jednom nakon DOMContentLoaded
	updateLoggerStatus();

	updateChartAndTable();
	window.loadRelayLogTable();
	if (document.getElementById('relayChart')) {
		loadRelayChart();
	}
}); /* DOMContentLoaded */