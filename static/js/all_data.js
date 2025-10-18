let charts = [];

async function fetchData() {
  const where = document.getElementById('whereInput').value.trim();
  const url = where ? `/api/logs/all?where=${encodeURIComponent(where)}` : '/api/logs/all';
  const r = await fetch(url);
  return await r.json();
}

function clearCharts() {
  charts.forEach(chart => chart.destroy());
  charts = [];
}

function calcStats(data) {
  const avg = arr => arr.reduce((a,b)=>a+b,0)/arr.length;
  return {
    air_temp: avg(data.map(r => r.air_temp).filter(v => v!==null)),
    air_humidity: avg(data.map(r => r.air_humidity).filter(v => v!==null)),
    soil_temp: avg(data.map(r => r.soil_temp).filter(v => v!==null)),
    soil_percent: avg(data.map(r => r.soil_percent).filter(v => v!==null)),
    lux: avg(data.map(r => r.lux).filter(v => v!==null))
  };
}

function formatTime(ts) {
  if (!ts) return "";
  const [date, time] = ts.split('_');
  const [y, m, d] = date.split('-');
  const [hh, mm] = time.split('-'); // Split time properly
  return `${d}.${m}.${y.slice(-2)} ${hh}:${mm}`;
}

function makeChart(id, label, labels, data, color) {
  const ctx = document.getElementById(id).getContext('2d');
  const chart = new Chart(ctx, {
    type:'line',
    data:{
      labels:labels,
      datasets:[{label:label, data:data, borderColor:color, tension:0.2, fill:false}]
    },
    options:{ responsive:true, maintainAspectRatio:false }
  });
  charts.push(chart);
}

async function loadData() {
  const data = await fetchData();
  clearCharts();

  const labels = data.map(r => formatTime(r.timestamp));

  makeChart('airTempChart', 'Air Temperature (°C)', labels, data.map(r => r.air_temp), 'blue');
  makeChart('airHumidityChart', 'Air Humidity (%)', labels, data.map(r => r.air_humidity), 'skyblue');
  makeChart('soilTempChart', 'Soil Temperature (°C)', labels, data.map(r => r.soil_temp), 'orange');
  makeChart('soilMoistureChart', 'Soil Moisture (%)', labels, data.map(r => r.soil_percent), 'green');
  makeChart('luxChart', 'Lux', labels, data.map(r => r.lux), 'purple');

  // Tablica
  const tbody = document.getElementById('logsBody');
  tbody.innerHTML = "";
  data.slice().reverse().forEach(r => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${r.id}</td>
      <td>${formatTime(r.timestamp)}</td>
      <td>${r.air_temp ?? ''}</td>
      <td>${r.air_humidity ?? ''}</td>
      <td>${r.soil_temp ?? ''}</td>
      <td>${r.soil_percent ?? ''}</td>
      <td>${r.lux ?? ''}</td>
      <td>${r.stable ? 'DA' : 'NE'}</td>`;
    tbody.appendChild(tr);
  });

  // Statistika
  const stats = calcStats(data);
  document.getElementById('stats').innerText = JSON.stringify(stats, null, 2);
}

document.getElementById('btnDeleteRows').addEventListener('click', async () => {
  const input = document.getElementById('deleteIdsInput').value.trim();
  const statusEl = document.getElementById('deleteStatus');

  if (!input) {
    statusEl.innerText = "Unesite ID-eve za brisanje ili 'all'.";
    return;
  }

  const payload = input.toLowerCase() === "all" ? { ids: "all" } : { ids: input };
  const confirmDelete = confirm(`Jeste li sigurni da želite obrisati ${input === "all" ? "SVE redove" : "ove redove: " + input}?`);
  if (!confirmDelete) return;

  try {
    const res = await fetch('/api/logs/delete', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (data.ok) {
      statusEl.innerText = `Obrisano: ${data.deleted === "all" ? "svi redovi" : data.deleted + " redova."}`;
      await loadData(); // Osvježi
    } else {
      statusEl.innerText = `Greška: ${data.msg || data.error}`;
    }
  } catch (e) {
    statusEl.innerText = "Greška pri brisanju: " + e.message;
  }
});

// Listener za gumb za primjenu filtera
// Potrebno je osigurati da se `loadData` poziva
// jer je `onclick` atribut uklonjen iz HTML-a
document.getElementById('filterBtn').addEventListener('click', loadData);

document.querySelectorAll('.example-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.getElementById('whereInput').value = btn.innerText;
  });
});

window.onload = loadData;