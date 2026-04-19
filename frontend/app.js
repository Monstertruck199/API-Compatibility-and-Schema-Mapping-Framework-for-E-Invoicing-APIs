let lastComparison = null;
const API_BASE_URL = 'http://localhost:5050';

function show(panel) {
  document.querySelectorAll('.panel').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.topbar-actions .nav-item').forEach(btn => btn.classList.remove('active'));

  const targetPanel = document.getElementById(`panel-${panel}`);
  if (targetPanel) targetPanel.classList.add('active');

  const btn = Array.from(document.querySelectorAll('.topbar-actions .nav-item')).find(x => x.dataset.panel === panel);
  if (btn) btn.classList.add('active');

  const titles = {
    'schema-viewer': 'Schema Viewer',
    'schema-comparison': 'Schema Comparison',
    'compat-result': 'Compatibility Result',
    'matrix': 'Compatibility Matrix',
    'database': 'Database'
  };
  document.getElementById('ptitle').textContent = titles[panel] || 'API Compatibility Framework';

  if (panel === 'schema-comparison') renderComparisonSelectors();
  if (panel === 'compat-result') renderCompatibilityResult();
  if (panel === 'matrix') renderMatrixBuilder();
  if (panel === 'database') renderDatabasePanel();
}

function toggleTheme() {
  const isLight = document.documentElement.getAttribute('data-theme') === 'light';
  const next = isLight ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', next);
  document.getElementById('theme-icon').textContent = next === 'light' ? '⏾' : '☀︎';
  localStorage.setItem('theme', next);
}

window.addEventListener('DOMContentLoaded', async () => {
  const saved = localStorage.getItem('theme') || 'dark';
  const icon = document.getElementById('theme-icon');
  if (icon) icon.textContent = saved === 'light' ? '⏾' : '☀︎';

  if (typeof loadFromDatabase === 'function') {
    await loadFromDatabase();
  }

  show('schema-viewer');
});