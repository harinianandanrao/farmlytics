let currentPage = 1;
let currentTab = 'all';
let currentSearch = '';
let currentDept = '';
let totalPages = 1;

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  loadDepartments();
  loadPriceCompare();
  initFilters();
});

function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const panel = document.getElementById('tab-' + btn.dataset.tab);
      if (panel) panel.classList.add('active');

      const tab = btn.dataset.tab;
      if (tab === 'price-compare') { currentPage = 1; loadPriceCompare(); }
      else if (tab === 'missing') loadMissing();
      else if (tab === 'mismatch') loadMismatch();
      else if (tab === 'cigarettes') loadSegmented('cigs');
      else if (tab === 'no-cigarettes') loadSegmented('no_cigs');
    });
  });

  // Subtabs for cigarette filter
  document.querySelectorAll('.subtab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.subtab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentTab = btn.dataset.subtab;
      currentPage = 1;
      loadPriceCompare();
    });
  });
}

function initFilters() {
  const searchInput = document.getElementById('explorerSearch');
  const deptSelect = document.getElementById('deptFilter');
  const clearBtn = document.getElementById('clearFilters');

  if (searchInput) {
    searchInput.addEventListener('input', debounce(() => {
      currentSearch = searchInput.value.trim();
      currentPage = 1;
      loadPriceCompare();
    }, 400));
  }

  if (deptSelect) {
    deptSelect.addEventListener('change', () => {
      currentDept = deptSelect.value;
      currentPage = 1;
      loadPriceCompare();
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      if (deptSelect) deptSelect.value = '';
      currentSearch = '';
      currentDept = '';
      currentPage = 1;
      loadPriceCompare();
    });
  }

  document.getElementById('prevPage')?.addEventListener('click', () => {
    if (currentPage > 1) { currentPage--; loadPriceCompare(); }
  });

  document.getElementById('nextPage')?.addEventListener('click', () => {
    if (currentPage < totalPages) { currentPage++; loadPriceCompare(); }
  });
}

async function loadDepartments() {
  try {
    const depts = await fetch('/api/departments').then(r => r.json());
    const sel = document.getElementById('deptFilter');
    if (!sel) return;
    depts.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d; opt.textContent = d;
      sel.appendChild(opt);
    });
  } catch (e) {}
}

async function loadPriceCompare() {
  const params = new URLSearchParams({
    page: currentPage,
    per_page: 50,
    tab: currentTab,
    search: currentSearch,
    dept: currentDept,
  });

  try {
    const data = await fetch('/api/price-compare?' + params).then(r => r.json());
    if (data.error) return;

    totalPages = data.pages;
    renderDynamicTable('priceCompareHead', 'priceCompareBody', data.columns, data.rows);
    updatePager(data.page, data.pages, data.total);
  } catch (e) {
    document.getElementById('priceCompareBody').innerHTML = '<tr><td colspan="10" class="error-row">Failed to load.</td></tr>';
  }
}

function renderDynamicTable(headId, bodyId, columns, rows) {
  const head = document.getElementById(headId);
  const body = document.getElementById(bodyId);
  if (!head || !body) return;

  head.innerHTML = '<tr>' + columns.map(c => `<th>${c}</th>`).join('') + '</tr>';

  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="${columns.length}" class="empty-row">No data found.</td></tr>`;
    return;
  }

  body.innerHTML = rows.map(row => {
    return '<tr>' + columns.map(col => {
      const val = row[col];
      const isMissing = String(val) === 'PRODUCT MISSING';
      const isPrice = !isNaN(parseFloat(val)) && ['Price', ...columns.filter(c => c !== 'ItemNum' && c !== 'ItemName' && c !== 'Dept_ID' && c !== 'Recommended_Price')].includes(col);
      let display = val;

      if (isMissing) return `<td class="missing-cell">${val}</td>`;
      if (col === 'Recommended_Price' && !isNaN(parseFloat(val))) return `<td class="rec-price">$${parseFloat(val).toFixed(2)}</td>`;
      if (!isNaN(parseFloat(val)) && col !== 'ItemNum') display = `$${parseFloat(val).toFixed(2)}`;
      return `<td>${display}</td>`;
    }).join('') + '</tr>';
  }).join('');
}

function updatePager(page, pages, total) {
  const info = document.getElementById('pagerInfo');
  const prev = document.getElementById('prevPage');
  const next = document.getElementById('nextPage');
  const ind = document.getElementById('pageIndicator');

  if (info) info.textContent = `${total} products`;
  if (ind) ind.textContent = `Page ${page} of ${pages}`;
  if (prev) prev.disabled = page <= 1;
  if (next) next.disabled = page >= pages;
}

async function loadMissing() {
  try {
    const data = await fetch('/api/missing-products').then(r => r.json());
    const tbody = document.getElementById('missingTableBody');
    if (!tbody) return;

    if (!data.rows || !data.rows.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="empty-row">No missing products found.</td></tr>';
      return;
    }

    tbody.innerHTML = data.rows.map(row => `
      <tr>
        <td>${row.ItemNum}</td>
        <td>${row.ItemName}</td>
        <td><span class="dept-tag">${row.Dept_ID}</span></td>
        <td class="missing-stores">${row.Missing_In}</td>
        <td><span class="badge badge-danger">${row.Missing_Count}</span></td>
      </tr>
    `).join('');
  } catch (e) {
    document.getElementById('missingTableBody').innerHTML = '<tr><td colspan="5" class="error-row">Failed to load.</td></tr>';
  }
}

async function loadMismatch() {
  try {
    const data = await fetch('/api/price-mismatch').then(r => r.json());
    const tbody = document.getElementById('mismatchTableBody');
    if (!tbody) return;

    if (!data.rows || !data.rows.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-row">No mismatches found.</td></tr>';
      return;
    }

    tbody.innerHTML = data.rows.map(row => {
      const pricesHtml = Object.entries(row.Prices)
        .map(([store, price]) => price !== null
          ? `<span class="store-price-chip">${store}: $${price.toFixed(2)}</span>`
          : `<span class="store-price-chip missing">${store}: —</span>`)
        .join('');
      return `
        <tr>
          <td>${row.ItemNum}</td>
          <td>${row.ItemName}</td>
          <td><span class="dept-tag">${row.Dept_ID}</span></td>
          <td><div class="price-chips">${pricesHtml}</div></td>
          <td><span class="badge ${row.Spread > 1 ? 'badge-danger' : 'badge-warning'}">$${row.Spread.toFixed(2)}</span></td>
          <td class="rec-price">$${row.Recommended.toFixed(2)}</td>
        </tr>
      `;
    }).join('');
  } catch (e) {
    document.getElementById('mismatchTableBody').innerHTML = '<tr><td colspan="6" class="error-row">Failed to load.</td></tr>';
  }
}

async function loadSegmented(tabCode) {
  const headId = tabCode === 'cigs' ? 'cigsHead' : 'noCigsHead';
  const bodyId = tabCode === 'cigs' ? 'cigsBody' : 'noCigsBody';

  const params = new URLSearchParams({ page: 1, per_page: 200, tab: tabCode });
  try {
    const data = await fetch('/api/price-compare?' + params).then(r => r.json());
    renderDynamicTable(headId, bodyId, data.columns, data.rows);
  } catch (e) {
    document.getElementById(bodyId).innerHTML = '<tr><td class="error-row">Failed to load.</td></tr>';
  }
}
