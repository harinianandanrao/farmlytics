document.addEventListener('DOMContentLoaded', () => {
  initSidebar();
  initProfileMenu();
  initGlobalSearch();
});

function initSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  const mobileBtn = document.getElementById('mobileMenuBtn');
  const toggleBtn = document.getElementById('sidebarToggle');

  if (!sidebar) return;

  function openSidebar() {
    sidebar.classList.add('open');
    overlay?.classList.add('visible');
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    overlay?.classList.remove('visible');
    document.body.style.overflow = '';
  }

  mobileBtn?.addEventListener('click', openSidebar);
  overlay?.addEventListener('click', closeSidebar);

  toggleBtn?.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
    localStorage.setItem('sidebar-collapsed', sidebar.classList.contains('collapsed'));
  });

  // Restore collapsed state on desktop
  if (window.innerWidth > 768) {
    const collapsed = localStorage.getItem('sidebar-collapsed') === 'true';
    if (collapsed) sidebar.classList.add('collapsed');
  }
}

function initProfileMenu() {
  const btn = document.getElementById('profileBtn');
  const dropdown = document.getElementById('profileDropdown');
  if (!btn || !dropdown) return;

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    dropdown.classList.toggle('visible');
  });

  document.addEventListener('click', () => {
    dropdown.classList.remove('visible');
  });
}

function initGlobalSearch() {
  const input = document.getElementById('globalSearch');
  if (!input) return;
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && input.value.trim()) {
      window.location.href = `/explorer?search=${encodeURIComponent(input.value.trim())}`;
    }
  });
}

// Utility: format currency
function formatCurrency(val) {
  const n = parseFloat(val);
  if (isNaN(n)) return val;
  return '$' + n.toFixed(2);
}

// Utility: debounce
function debounce(fn, delay) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), delay);
  };
}

// Utility: chart color palette
const CHART_COLORS = [
  '#2ECC71', '#3498DB', '#E74C3C', '#F39C12', '#9B59B6',
  '#1ABC9C', '#E67E22', '#34495E', '#E91E63', '#00BCD4'
];

function getChartOptions(label) {
  const theme = document.documentElement.getAttribute('data-theme') || 'dark';
  const textColor = theme === 'dark' ? '#FFFFFF' : '#1A1A1A';
  const gridColor = theme === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.08)';
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: { color: textColor, font: { family: 'Inter', size: 12 } }
      },
      tooltip: {
        callbacks: {
          label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y ?? ctx.parsed}`
        }
      }
    },
    scales: label !== 'pie' ? {
      x: {
        ticks: { color: textColor, font: { family: 'Inter', size: 11 } },
        grid: { color: gridColor }
      },
      y: {
        ticks: { color: textColor, font: { family: 'Inter', size: 11 } },
        grid: { color: gridColor }
      }
    } : undefined
  };
}
