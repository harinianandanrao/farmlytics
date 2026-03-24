// Theme system – runs before render to prevent flash
(function () {
  const saved = localStorage.getItem('farmlytics-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
})();

function initThemeToggle() {
  const toggle = document.getElementById('themeToggle');
  if (!toggle) return;

  function update(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('farmlytics-theme', theme);
  }

  toggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    update(current === 'dark' ? 'light' : 'dark');
  });
}

document.addEventListener('DOMContentLoaded', initThemeToggle);
