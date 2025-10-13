/* main.js - Main JS logic for index.html */
/* This file must be loaded after Chart.js (CDN) and after the HTML elements are in the DOM. */

document.addEventListener("DOMContentLoaded", () => {

	// ------- Helpers -------
	function formatTime(ts) {
		if (!ts) return "";
		const [date, time] = ts.split(' ');
		if (!date || !time) return ts;
		const [y, m, d] = date.split('-');
		const [hh, mm, ss] = time.split(':');
		return `${d}.${m}.${y.slice(-2)} ${hh}:${mm}`;
	}

	async function fetchJSON(url, opts) {
		const r = await fetch(url, opts);
		return await r.json();
	}

	// ------- Chart background plugin -------
	const chartAreaBackgroundPlugin = {
		id: 'chartAreaBackground',
		beforeDraw(chart, args, options) {
			const {
				ctx,
				chartArea
			} = chart;
			ctx.save();
			ctx.fillStyle = options.color || 'white';
			ctx.fillRect(chartArea.left, chartArea.top, chartArea.width, chartArea.height);
			ctx.restore();
		}
	};

	// ------- Chart initialization -------
	const ctxTemp = document.getElementById('tempChart').getContext('2d');
	const tempChart = new Chart(ctxTemp, {
		type: 'line',
		data: {
			labels: [],
			datasets: [{
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
		options: {
			responsive: true,
			maintainAspectRatio: false,
			interaction: {
				mode: 'index',
				intersect: false
			},
			scales: {
				y: {
					min: 0,
					max: 50
				}
			},
			plugins: {
				chartAreaBackground: {
					color: 'lavender'
				}
			}
		},
		plugins: [chartAreaBackgroundPlugin]
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
		options: {
			responsive: true,
			maintainAspectRatio: false,
			interaction: {
				mode: 'index',
				intersect: false
			},
			scales: {
				y: {
					min: 0,
					max: 100
				}
			},
			plugins: {
				chartAreaBackground: {
					color: 'honeydew'
				}
			}
		},
		plugins: [chartAreaBackgroundPlugin]
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
		options: {
			responsive: true,
			maintainAspectRatio: false,
			interaction: {
				mode: 'index',
				intersect: false
			},
			scales: {
				y: {
					min: 0,
					max: 100
				}
			},
			plugins: {
				chartAreaBackground: {
					color: 'mistyrose'
				}
			}
		},
		plugins: [chartAreaBackgroundPlugin]
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
		options: {
			responsive: true,
			maintainAspectRatio: false,
			interaction: {
				mode: 'index',
				intersect: false
			},
			scales: {
				y: {
					beginAtZero: true
				}
			},
			plugins: {
				chartAreaBackground: {
					color: 'lavender'
				}
			}
		},
		plugins: [chartAreaBackgroundPlugin]
	});


	// ------- Relay Signal Chart -------
	let relayChart = null;
	async function loadRelayChart() {
		const data = await fetchJSON('/relay_log_data');

		if (!data || !data.length) return;

		// Separate data for each relay
		const relay1Data = data.filter(d => d.relay === 'RELAY1');
		const relay2Data = data.filter(d => d.relay === 'RELAY2');

		const labels = [...new Set(data.map(x => x.t.split(' ')[1]))].sort();

		const relay1 = relay1Data.map(d => d.v);
		const relay2 = relay2Data.map(d => d.v);

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
			const onTime = arr[lastOnIdx].t.split(' ')[1];
			const offTime = lastOffIdx === -1 ? null : arr[lastOffIdx].t.split(' ')[1];
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

		const d1 = calcDuration(relay1Data);
		const d2 = calcDuration(relay2Data);

		const durEl = document.getElementById('relayDurations');
		if (durEl) {
			let html = "";
			if (d1) html += `Relay 1 was on for <b>${d1}s</b>`;
			if (d2) html += (html ? " &nbsp;&nbsp;|&nbsp;&nbsp; " : "") + `Relay 2 was on for <b>${d2}s</b>`;
			durEl.innerHTML = html;
		}

		if (!relayChart) {
			const ctx = document.getElementById('relayChart').getContext('2d');
			relayChart = new Chart(ctx, {
				type: 'line',
				data: {
					labels: labels,
					datasets: [{
							label: 'Relay 1',
							data: relay1Display,
							borderColor: 'rgb(255, 99, 132)',
							backgroundColor: 'rgba(255, 99, 132, 0.25)',
							fill: true,
							stepped: true,
							tension: 0,
							borderWidth: 3
						},
						{
							label: 'Relay 2',
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
									if (v === 1) return 'Relay 1 ON';
									if (v === 0.5) return 'Relay 2 ON';
									return '';
								}
							},
							grid: {
								color: 'rgba(180,180,180,0.2)'
							},
							title: {
								display: true,
								text: 'Relay States'
							}
						},
						x: {
							title: {
								display: true,
								text: 'Time'
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


	// ------- Relay Log Table -------
	async function loadRelayLogTable() {
		const data = await fetchJSON('/relay_log_data');

		const tbody = document.querySelector('#relayLogTable tbody');
		tbody.innerHTML = '';

		(data || []).forEach(entry => {
			const tr = document.createElement('tr');
			tr.innerHTML = `
        <td>${formatTime(entry.t)}</td>
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

	// ------- Other handlers and functions -------
	async function updateChartAndTable() {
		const rows = await fetchJSON('/api/logs?limit=100');

		const labels = rows.map(r => formatTime(r.timestamp));
		const airT = rows.map(r => r.dht22_air_temp !== null ? Number(r.dht22_air_temp) : null);
		const airH = rows.map(r => r.dht22_humidity !== null ? Number(r.dht22_humidity) : null);
		const soilT = rows.map(r => r.ds18b20_soil_temp !== null ? Number(r.ds18b20_soil_temp) : null);
		const soilP = rows.map(r => r.soil_percent !== null ? Number(r.soil_percent) : null);
		const lux = rows.map(r => r.lux !== null ? Number(r.lux) / 100.0 : null);

		// logs table
		const tbody = document.getElementById('logsBody');
		tbody.innerHTML = "";

		for (let i = 0; i < rows.length; i++) {
			const r = rows[i];
			const tr = document.createElement('tr');
			tr.innerHTML = `
        <td>${r.id}</td>
        <td>${formatTime(r.timestamp)}</td>
        <td>${r.dht22_air_temp ?? ''}</td>
        <td>${r.dht22_humidity ?? ''}</td>
        <td>${r.ds18b20_soil_temp ?? ''}</td>
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
	}

	async function updateLoggerStatus() {
		try {
			const data = await fetchJSON('/api/status');
			const el = document.getElementById('loggerStatusTXT');
			el.innerText = data.status;
			el.style.color = data.status.includes("RUNNING") ? "green" : "red";
		} catch (e) {
			const el = document.getElementById('loggerStatusTXT');
			el.innerText = "Error fetching status";
			el.style.color = "red";
		}
	}

	// event listeners (button events)
	document.getElementById('btnStartFirst').addEventListener('click', async () => {
		const res = await fetch('/api/run/start_first', {
			method: 'POST'
		}).then(r => r.json());
		document.getElementById('loggerStatus').innerText = res.running ? "ACTIVE" : "STOPPED";
	});
	document.getElementById('btnStop').addEventListener('click', async () => {
		const res = await fetch('/api/run/stop', {
			method: 'POST'
		}).then(r => r.json());
		document.getElementById('loggerStatus').innerText = res.running ? "ACTIVE" : "STOPPED";
	});

	document.getElementById('btnDeleteRows').addEventListener('click', async () => {
		const input = document.getElementById('deleteIdsInput').value.trim();
		const statusEl = document.getElementById('deleteStatus');

		if (!input) {
			statusEl.innerText = "Enter IDs to delete or 'all'.";
			return;
		}

		const payload = input.toLowerCase() === "all" ? {
			ids: "all"
		} : {
			ids: input
		};

		const confirmDelete = confirm(`Are you sure you want to delete ${input === "all" ? "ALL rows" : "these rows: " + input}?`);
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
				statusEl.innerText = `Deleted: ${data.deleted === "all" ? "all rows" : data.deleted + " rows."}`;
				await updateChartAndTable(); // refresh table and charts
			} else {
				statusEl.innerText = `Error: ${data.msg || data.error}`;
			}
		} catch (e) {
			statusEl.innerText = "Error deleting: " + e.message;
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

	// Load things once after DOMContentLoaded
	updateLoggerStatus();

	updateChartAndTable();
	window.loadRelayLogTable();
	loadRelayChart();
}); /* DOMContentLoaded */