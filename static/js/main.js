/* main.js - glavni JS logika za index.html */
document.addEventListener("DOMContentLoaded", () => {

	// ------- Theme Switcher Logic -------
	const themeSwitcher = document.getElementById('theme-switcher');
	const docHtml = document.documentElement;

	function updateChartColors(theme) {
		const isDark = theme === 'dark';
		// Dobivanje vrijednosti boja iz CSS varijabli
		const gridColor = getComputedStyle(docHtml).getPropertyValue('--chart-grid-color').trim();
		const labelColor = getComputedStyle(docHtml).getPropertyValue('--chart-label-color').trim();

		// Definicija boja za svijetlu i tamnu temu
		const chartColors = {
			airTemp: {
				border: isDark ? '#58a6ff' : '#0d6efd',
				bg: isDark ? 'rgba(88, 166, 255, 0.2)' : 'rgba(0,123,255,0.1)'
			},
			soilTemp: {
				border: isDark ? '#56d364' : '#198754',
				bg: isDark ? 'rgba(86, 211, 100, 0.2)' : 'rgba(40,167,69,0.1)'
			},
			airHum: {
				border: isDark ? '#e3b341' : '#ffc107',
				bg: isDark ? 'rgba(227, 179, 65, 0.2)' : 'rgba(255,165,0,0.15)'
			},
			soilPercent: {
				border: isDark ? '#d2a679' : '#8B4513',
				bg: isDark ? 'rgba(210, 166, 121, 0.2)' : 'rgba(139,69,19,0.15)'
			},
			lux: {
				border: isDark ? '#c991e1' : '#800080',
				bg: isDark ? 'rgba(201, 145, 225, 0.2)' : 'rgba(128,0,128,0.1)'
			},
			relay1: {
				border: isDark ? '#f87171' : '#dc3545',
				bg: isDark ? 'rgba(248, 113, 113, 0.25)' : 'rgba(255, 99, 132, 0.25)'
			},
			relay2: {
				border: isDark ? '#60a5fa' : '#0d6efd',
				bg: isDark ? 'rgba(96, 165, 250, 0.25)' : 'rgba(54, 162, 235, 0.25)'
			},
		};

		// Ažuriranje zajedničkih opcija za sve grafikone
		const allCharts = [tempChart, humChart, soilChart, luxChart, relayChart].filter(c => c);
		allCharts.forEach(chart => {
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
		});

		// Ažuriranje boja dataseta
		tempChart.data.datasets[0].borderColor = chartColors.airTemp.border;
		tempChart.data.datasets[0].backgroundColor = chartColors.airTemp.bg;
		tempChart.data.datasets[1].borderColor = chartColors.soilTemp.border;
		tempChart.data.datasets[1].backgroundColor = chartColors.soilTemp.bg;

		humChart.data.datasets[0].borderColor = chartColors.airHum.border;
		humChart.data.datasets[0].backgroundColor = chartColors.airHum.bg;

		soilChart.data.datasets[0].borderColor = chartColors.soilPercent.border;
		soilChart.data.datasets[0].backgroundColor = chartColors.soilPercent.bg;

		luxChart.data.datasets[0].borderColor = chartColors.lux.border;
		luxChart.data.datasets[0].backgroundColor = chartColors.lux.bg;

		if (relayChart) {
			relayChart.data.datasets[0].borderColor = chartColors.relay1.border;
			relayChart.data.datasets[0].backgroundColor = chartColors.relay1.bg;
			relayChart.data.datasets[1].borderColor = chartColors.relay2.border;
			relayChart.data.datasets[1].backgroundColor = chartColors.relay2.bg;
		}

		// Ponovno iscrtavanje svih grafikona
		allCharts.forEach(chart => chart.update());
	}

	function setTheme(theme) {
		docHtml.setAttribute('data-theme', theme);
		localStorage.setItem('theme', theme);
		themeSwitcher.textContent = theme === 'dark' ? '☀️' : '🌙';
		updateChartColors(theme);
	}

	themeSwitcher.addEventListener('click', () => {
		const currentTheme = docHtml.getAttribute('data-theme') || 'light';
		setTheme(currentTheme === 'light' ? 'dark' : 'light');
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

	// ------- inicijalizacija chartova -------
	const commonChartOptions = {
		responsive: true,
		maintainAspectRatio: false,
		interaction: {
			mode: 'index',
			intersect: false
		},
		scales: {
			y: {
				min: 0
			}
		}
	};

	const ctxTemp = document.getElementById('tempChart').getContext('2d');
	const tempChart = new Chart(ctxTemp, {
		type: 'line',
		data: {
			labels: [],
			datasets: [{
				label: 'Air Temp °C',
				data: [],
				fill: true,
				tension: 0.2
			}, {
				label: 'Soil Temp °C',
				data: [],
				fill: true,
				tension: 0.2
			}]
		},
		options: {
			...commonChartOptions,
			scales: {
				y: {
					min: 0,
					max: 50
				}
			}
		}
	});

	const ctxHum = document.getElementById('humChart').getContext('2d');
	const humChart = new Chart(ctxHum, {
		type: 'line',
		data: {
			labels: [],
			datasets: [{
				label: 'Air Humidity %',
				data: [],
				fill: true,
				tension: 0.2
			}]
		},
		options: {
			...commonChartOptions,
			scales: {
				y: {
					min: 0,
					max: 100
				}
			}
		}
	});

	const ctxSoil = document.getElementById('soilChart').getContext('2d');
	const soilChart = new Chart(ctxSoil, {
		type: 'line',
		data: {
			labels: [],
			datasets: [{
				label: 'Soil %',
				data: [],
				fill: true,
				tension: 0.2
			}]
		},
		options: {
			...commonChartOptions,
			scales: {
				y: {
					min: 0,
					max: 100
				}
			}
		}
	});

	const ctxLux = document.getElementById('luxChart').getContext('2d');
	const luxChart = new Chart(ctxLux, {
		type: 'line',
		data: {
			labels: [],
			datasets: [{
				label: 'Lux (lx)',
				data: [],
				fill: true,
				tension: 0.2
			}]
		},
		options: { ...commonChartOptions
		}
	});


	// ------- Grafikon paljenja/gasenja releja (signal) -------
	let relayChart = null;
	async function loadRelayChart() {
		const res = await fetch('/relay_log_data');
		const data = await res.json();

		if (!data || (!data.RELAY1?.length && !data.RELAY2?.length)) return;

		const labels = [...new Set([...data.RELAY1.map(x => x.t), ...data.RELAY2.map(x => x.t)])].sort();
		const relay1Display = data.RELAY1.map(d => d.v ? 1 : 0.05);
		const relay2Display = data.RELAY2.map(d => d.v ? 0.5 : 0.5 - 0.05);

		// Ostatak funkcije ostaje isti...
		const calcDuration = (arr) => {
			if (!arr || !arr.length) return null;
			let lastOnIdx = -1, lastOffIdx = -1;
			for (let i = arr.length - 1; i >= 0; i--) {
				if (arr[i].v === 1 && lastOnIdx === -1) lastOnIdx = i;
				if (arr[i].v === 0 && lastOnIdx !== -1) { lastOffIdx = i; break; }
			}
			if (lastOnIdx === -1) return null;
			const onTime = arr[lastOnIdx].t;
			const offTime = lastOffIdx === -1 ? null : arr[lastOffIdx].t;
			try {
				const nowDate = new Date();
				const parseT = (hhmmss) => new Date(nowDate.getFullYear(), nowDate.getMonth(), nowDate.getDate(), ...hhmmss.split(':').map(Number));
				const tOn = parseT(onTime);
				const tOff = offTime ? parseT(offTime) : null;
				if (!tOn) return null;
				const diff = tOff ? (tOn - tOff) / 1000 : (Date.now() - tOn.getTime()) / 1000;
				return Math.max(0, diff).toFixed(1);
			} catch (e) { return null; }
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
						fill: true,
						stepped: true,
						tension: 0,
						borderWidth: 3
					}, {
						label: 'Relej 2',
						data: relay2Display,
						fill: true,
						stepped: true,
						tension: 0,
						borderWidth: 3
					}]
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
							}
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
		// Inicijalno postavljanje boja i za relay chart
		const currentTheme = docHtml.getAttribute('data-theme') || 'light';
		updateChartColors(currentTheme);
	}


	// ------- tablica relej logova -------
	async function loadRelayLogTable() {
		const data = await fetchJSON('/relay_log_data');
		const tbody = document.querySelector('#relayLogTable tbody');
		tbody.innerHTML = '';

		(data || []).forEach(entry => {
			const tr = document.createElement('tr');
			tr.innerHTML = `
                <td>${entry.t}</td>
                <td>${entry.relay}</td>
                <td><span class="badge ${entry.v ? 'bg-success' : 'bg-secondary'}">${entry.action}</span></td>
                <td>${entry.source || 'button'}</td>
            `;
			tbody.appendChild(tr);
		});
	}
	window.loadRelayLogTable = loadRelayLogTable;


	// ------- ostali handleri i funkcije -------
	async function updateChartAndTable() {
		const rows = await fetchJSON('/api/logs?limit=100');

		const labels = rows.map(r => formatTime(r.timestamp));
		const airT = rows.map(r => r.air_temp !== null ? Number(r.air_temp) : null);
		const airH = rows.map(r => r.air_humidity !== null ? Number(r.air_humidity) : null);
		const soilT = rows.map(r => r.soil_temp !== null ? Number(r.soil_temp) : null);
		const soilP = rows.map(r => r.soil_percent !== null ? Number(r.soil_percent) : null);
		const lux = rows.map(r => r.lux !== null ? Number(r.lux) / 100.0 : null);

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

		humChart.data.labels = labels;
		humChart.data.datasets[0].data = airH;

		soilChart.data.labels = labels;
		soilChart.data.datasets[0].data = soilP;

		luxChart.data.labels = labels;
		luxChart.data.datasets[0].data = lux.map(v => v !== null ? v * 100 : null);

		// Ažuriranje svih grafikona odjednom
		const allCharts = [tempChart, humChart, soilChart, luxChart].filter(c => c);
		allCharts.forEach(chart => chart.update());
	}

	async function readSensor(type) {
		const r = await fetchJSON(`/api/sensor/read?type=${type}`);
		document.getElementById('sensorOutput').innerText = JSON.stringify(r, null, 2);
	}

	async function toggleRelay(relay) {
		const cur = relay === 1 ? document.getElementById('relay1State').innerText === 'ON' : document.getElementById('relay2State').innerText === 'ON';
		await fetch('/api/relay/toggle', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ relay: relay, state: !cur })
		});
		document.getElementById(`relay${relay}State`).innerText = !cur ? 'ON' : 'OFF';
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

	// ------- event listeners -------
	document.getElementById('btnStartFirst').addEventListener('click', async () => {
		const res = await fetchJSON('/api/run/start_first', { method: 'POST' });
		document.getElementById('loggerStatus').innerText = res.running ? "AKTIVAN" : "STOPIRAN";
	});

	document.getElementById('btnStop').addEventListener('click', async () => {
		const res = await fetchJSON('/api/run/stop', { method: 'POST' });
		document.getElementById('loggerStatus').innerText = res.running ? "AKTIVAN" : "STOPIRAN";
	});

	document.getElementById('btnDeleteRows').addEventListener('click', async () => {
		const input = document.getElementById('deleteIdsInput').value.trim();
		const statusEl = document.getElementById('deleteStatus');

		if (!input) {
			statusEl.innerText = "Unesite ID-eve za brisanje ili 'all'.";
			return;
		}

		if (!confirm(`Jeste li sigurni da želite obrisati ${input === "all" ? "SVE redove" : "ove redove: " + input}?`)) return;

		try {
			const res = await fetchJSON('/api/logs/delete', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ ids: input })
			});
			statusEl.innerText = res.ok ? `Obrisano: ${res.deleted === "all" ? "svi redovi" : res.deleted + " redova."}` : `Greška: ${res.msg || res.error}`;
			if (res.ok) await updateChartAndTable();
		} catch (e) {
			statusEl.innerText = "Greška pri brisanju: " + e.message;
		}
	});

	document.getElementById('btn-ads').addEventListener('click', () => readSensor('ads'));
	document.getElementById('btn-dht').addEventListener('click', () => readSensor('dht'));
	document.getElementById('btn-ds18b20').addEventListener('click', () => readSensor('ds18b20'));
	document.getElementById('btn-bh1750').addEventListener('click', () => readSensor('bh1750'));
	document.getElementById('btn-relay1').addEventListener('click', () => toggleRelay(1));
	document.getElementById('btn-relay2').addEventListener('click', () => toggleRelay(2));


	// ------- Inicijalno učitavanje podataka -------
	const savedTheme = localStorage.getItem('theme') || 'light';
	setTheme(savedTheme);

	updateLoggerStatus();
	updateChartAndTable();
	loadRelayLogTable();
	if (document.getElementById('relayChart')) {
		loadRelayChart();
	}
});