document.addEventListener('DOMContentLoaded', () => {
  loadCharts();
  loadIssueTable();
});

async function loadCharts() {
  const [coverage, missing, dept, spread] = await Promise.all([
    fetch('/api/chart/store-coverage').then(r => r.json()),
    fetch('/api/chart/missing-by-store').then(r => r.json()),
    fetch('/api/chart/dept-distribution').then(r => r.json()),
    fetch('/api/chart/price-spread').then(r => r.json()),
  ]);

  const opts = getChartOptions('bar');

  // Store Coverage
  const ctx1 = document.getElementById('storeCoverageChart');
  if (ctx1 && coverage.labels) {
    new Chart(ctx1, {
      type: 'bar',
      data: {
        labels: coverage.labels,
        datasets: [{
          label: 'Products Available',
          data: coverage.values,
          backgroundColor: CHART_COLORS[0],
          borderRadius: 6,
        }]
      },
      options: { ...opts }
    });
  }

  // Missing By Store
  const ctx2 = document.getElementById('missingByStoreChart');
  if (ctx2 && missing.labels) {
    new Chart(ctx2, {
      type: 'bar',
      data: {
        labels: missing.labels,
        datasets: [{
          label: 'Missing Products',
          data: missing.values,
          backgroundColor: '#E74C3C',
          borderRadius: 6,
        }]
      },
      options: { ...opts }
    });
  }

  // Dept Distribution – Doughnut
  const ctx3 = document.getElementById('deptDistChart');
  if (ctx3 && dept.labels) {
    const pieOpts = getChartOptions('pie');
    new Chart(ctx3, {
      type: 'doughnut',
      data: {
        labels: dept.labels,
        datasets: [{
          data: dept.values,
          backgroundColor: CHART_COLORS,
          borderWidth: 2,
          borderColor: document.documentElement.getAttribute('data-theme') === 'dark' ? '#132F4C' : '#F8FAFC',
        }]
      },
      options: {
        ...pieOpts,
        cutout: '60%',
        plugins: {
          legend: {
            position: 'right',
            labels: {
              color: document.documentElement.getAttribute('data-theme') === 'dark' ? '#fff' : '#1A1A1A',
              font: { family: 'Inter', size: 11 },
              boxWidth: 12,
            }
          }
        }
      }
    });
  }

  // Price Spread – Horizontal bar
  const ctx4 = document.getElementById('priceSpreadChart');
  if (ctx4 && spread.labels) {
    new Chart(ctx4, {
      type: 'bar',
      data: {
        labels: spread.labels,
        datasets: [{
          label: 'Price Spread ($)',
          data: spread.values,
          backgroundColor: '#F39C12',
          borderRadius: 6,
        }]
      },
      options: {
        ...opts,
        indexAxis: 'y',
      }
    });
  }
}

async function loadIssueTable() {
  const tbody = document.getElementById('issueTableBody');
  if (!tbody) return;

  try {
    const data = await fetch('/api/missing-products').then(r => r.json());
    if (!data.rows || data.rows.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="empty-row">No missing products detected.</td></tr>';
      return;
    }

    tbody.innerHTML = data.rows.slice(0, 10).map(row => `
      <tr>
        <td>${row.ItemNum}</td>
        <td>${row.ItemName}</td>
        <td><span class="dept-tag">${row.Dept_ID}</span></td>
        <td class="missing-stores">${row.Missing_In}</td>
        <td><span class="badge badge-danger">${row.Missing_Count}</span></td>
      </tr>
    `).join('');
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="5" class="error-row">Failed to load data.</td></tr>';
  }
}
