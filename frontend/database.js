const DB_TABLES = [
  { key: 'apis',                   label: 'APIs',                    endpoint: '/api/apis' },
  { key: 'transforms',             label: 'Transform Runs',          endpoint: '/api/transforms?limit=100' },
  { key: 'compat_results',         label: 'Compatibility Results',   endpoint: '/api/compatibility/results' },
];

let dbState = {
  activeTable: 'apis',
  data: {},
  loading: {},
  error: {},
  search: '',
  expandedRow: null,
};

function renderDatabasePanel() {
  const root = document.getElementById('db-root');
  if (!root) return;

  root.innerHTML = `
    <div class="db-layout">
      <div class="db-sidebar">
        <div class="db-sidebar-head">
          <span class="db-sidebar-title">Tables</span>
          <button class="db-refresh-all btn" onclick="dbRefreshAll()" title="Refresh all">↺</button>
        </div>
        <nav class="db-nav">
          ${DB_TABLES.map(t => `
            <button
              class="db-nav-item ${dbState.activeTable === t.key ? 'active' : ''}"
              onclick="dbSetTable('${t.key}')"
            >
              <span class="db-nav-label">${t.label}</span>
              <span class="db-nav-count" id="db-count-${t.key}">
                ${dbState.data[t.key] ? dbState.data[t.key].length : '—'}
              </span>
            </button>
          `).join('')}
        </nav>

        <div class="db-sidebar-section">
          <div class="db-sidebar-title" style="margin-bottom:8px">Quick stats</div>
          <div id="db-stats" class="db-stats"></div>
        </div>
      </div>

      <div class="db-main">
        <div class="db-toolbar">
          <div class="db-toolbar-left">
            <span class="db-table-name">${DB_TABLES.find(t => t.key === dbState.activeTable)?.label}</span>
            <span class="db-row-count" id="db-active-count"></span>
          </div>
          <div class="db-toolbar-right">
            <div class="db-search-wrap">
              <span class="db-search-icon">⌕</span>
              <input
                class="db-search ifield"
                id="db-search"
                placeholder="Filter rows…"
                value="${dbState.search}"
                oninput="dbSearch(this.value)"
              >
            </div>
            <button class="btn db-refresh-btn" onclick="dbRefreshActive()">↺ Refresh</button>
          </div>
        </div>

        <div class="db-table-wrap" id="db-table-wrap">
          <div class="empty-hint" style="padding:60px 0">Loading…</div>
        </div>
      </div>
    </div>
  `;

  dbRefreshActive();
  dbRefreshStats();
}

async function dbFetch(key) {
  const table = DB_TABLES.find(t => t.key === key);
  if (!table) return;

  dbState.loading[key] = true;
  dbState.error[key] = null;

  try {
    const res = await fetch(`${API_BASE_URL}${table.endpoint}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    dbState.data[key] = Array.isArray(data) ? data : (data.results || data.matrix || []);
    const countEl = document.getElementById(`db-count-${key}`);
    if (countEl) countEl.textContent = dbState.data[key].length;
  } catch (e) {
    dbState.error[key] = e.message;
    dbState.data[key] = [];
  }

  dbState.loading[key] = false;
}

async function dbRefreshActive() {
  await dbFetch(dbState.activeTable);
  dbRenderTable();
  dbRefreshStats();
}

async function dbRefreshAll() {
  await Promise.all(DB_TABLES.map(t => dbFetch(t.key)));
  dbRenderTable();
  dbRefreshStats();
}

function dbSetTable(key) {
  dbState.activeTable = key;
  dbState.search = '';
  dbState.expandedRow = null;

  document.querySelectorAll('.db-nav-item').forEach(el => {
    el.classList.toggle('active', el.textContent.trim().startsWith(
      DB_TABLES.find(t => t.key === key)?.label
    ));
  });
  document.querySelector('.db-table-name').textContent =
    DB_TABLES.find(t => t.key === key)?.label;

  const searchEl = document.getElementById('db-search');
  if (searchEl) searchEl.value = '';

  if (!dbState.data[key]) {
    dbFetch(key).then(dbRenderTable);
  } else {
    dbRenderTable();
  }
}

function dbSearch(val) {
  dbState.search = val.toLowerCase();
  dbState.expandedRow = null;
  dbRenderTable();
}

function dbRenderTable() {
  const wrap = document.getElementById('db-table-wrap');
  if (!wrap) return;

  const key = dbState.activeTable;
  const rows = dbState.data[key];

  if (dbState.loading[key]) {
    wrap.innerHTML = '<div class="empty-hint" style="padding:60px 0">Loading…</div>';
    return;
  }

  if (dbState.error[key]) {
    wrap.innerHTML = `<div class="empty-hint" style="padding:60px 0;color:var(--red)">Error: ${dbState.error[key]}</div>`;
    return;
  }

  if (!rows || rows.length === 0) {
    wrap.innerHTML = '<div class="empty-hint" style="padding:60px 0">No records found</div>';
    const countEl = document.getElementById('db-active-count');
    if (countEl) countEl.textContent = '0 rows';
    return;
  }

  let filtered = rows;
  if (dbState.search) {
    filtered = rows.filter(row =>
      JSON.stringify(row).toLowerCase().includes(dbState.search)
    );
  }

  const countEl = document.getElementById('db-active-count');
  if (countEl) countEl.textContent = `${filtered.length} row${filtered.length !== 1 ? 's' : ''}`;

  if (filtered.length === 0) {
    wrap.innerHTML = '<div class="empty-hint" style="padding:60px 0">No rows match filter</div>';
    return;
  }

  const allCols = Object.keys(filtered[0]);
  const cols = ['id', ...allCols.filter(c => c !== 'id')];

  const jsonCols = new Set();
  cols.forEach(col => {
    filtered.forEach(row => {
      const v = row[col];
      if (v !== null && typeof v === 'object') jsonCols.add(col);
    });
  });

  const heavyCols = new Set(['full_result', 'raw_schema', 'normalized_schema', 'input_data', 'output_data', 'summary', 'warnings']);
  const visibleCols = cols.filter(c => !heavyCols.has(c));

  wrap.innerHTML = `
    <table class="db-table">
      <thead>
        <tr>
          ${visibleCols.map(c => `<th>${c}</th>`).join('')}
          <th class="db-col-expand"></th>
        </tr>
      </thead>
      <tbody>
        ${filtered.map((row, i) => {
          const isExpanded = dbState.expandedRow === i;
          const heavyData = cols
            .filter(c => heavyCols.has(c) && row[c] != null)
            .map(c => ({ col: c, val: row[c] }));

          return `
            <tr class="db-row ${isExpanded ? 'expanded' : ''}" onclick="dbToggleRow(${i})">
              ${visibleCols.map(c => `<td>${dbFormatCell(row[c], c)}</td>`).join('')}
              <td class="db-col-expand">${heavyData.length ? '⊞' : ''}</td>
            </tr>
            ${isExpanded && heavyData.length ? `
              <tr class="db-expanded-row">
                <td colspan="${visibleCols.length + 1}">
                  <div class="db-expanded-wrap">
                    ${heavyData.map(({ col, val }) => `
                      <div class="db-expanded-field">
                        <div class="db-expanded-label">${col}</div>
                        <pre class="db-expanded-pre">${JSON.stringify(val, null, 2)}</pre>
                      </div>
                    `).join('')}
                  </div>
                </td>
              </tr>
            ` : ''}
          `;
        }).join('')}
      </tbody>
    </table>
  `;
}

function dbToggleRow(i) {
  dbState.expandedRow = dbState.expandedRow === i ? null : i;
  dbRenderTable();
}

function dbFormatCell(val, col) {
  if (val === null || val === undefined) return '<span class="db-null">null</span>';

  if (typeof val === 'boolean') {
    return val
      ? '<span class="db-bool-t">true</span>'
      : '<span class="db-bool-f">false</span>';
  }

  if (typeof val === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(val)) {
    const d = new Date(val);
    return `<span class="db-ts" title="${val}">${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>`;
  }

  if (col === 'compatibility_level' || col === 'compatibility') {
    const map = {
      directly_compatible:    'db-compat-ok',
      compatible_with_mapping:'db-compat-warn',
      incompatible:           'db-compat-bad',
      same_schema:            'db-compat-same',
      not_assessed:           'db-compat-na',
    };
    return `<span class="db-compat-pill ${map[val] || ''}">${val}</span>`;
  }

  if (col === 'success') {
    return val
      ? '<span class="db-bool-t">✓ success</span>'
      : '<span class="db-bool-f">✗ failed</span>';
  }

  if (col === 'mapping_status') {
    const cls = val === 'ok' || val === 'full' ? 'db-bool-t' : 'db-compat-warn';
    return `<span class="${cls}">${val}</span>`;
  }

  if (typeof val === 'object') {
    return `<span class="db-json-badge">{ … }</span>`;
  }

  const str = String(val);
  if (str.length > 60) {
    return `<span title="${str.replace(/"/g, '&quot;')}">${str.slice(0, 58)}…</span>`;
  }

  return str;
}

async function dbRefreshStats() {
  const statsEl = document.getElementById('db-stats');
  if (!statsEl) return;

  const apis    = dbState.data['apis']?.length ?? '—';
  const runs    = dbState.data['transforms']?.length ?? '—';
  const compat  = dbState.data['compat_results']?.length ?? '—';

  const successRuns = dbState.data['transforms']?.filter(r => r.success)?.length ?? null;
  const failedRuns  = dbState.data['transforms']?.filter(r => !r.success)?.length ?? null;

  statsEl.innerHTML = `
    <div class="db-stat"><span class="db-stat-val">${apis}</span><span class="db-stat-lbl">APIs</span></div>
    <div class="db-stat"><span class="db-stat-val">${runs}</span><span class="db-stat-lbl">Transform runs</span></div>
    ${successRuns !== null ? `<div class="db-stat"><span class="db-stat-val db-bool-t">${successRuns}</span><span class="db-stat-lbl">Successful</span></div>` : ''}
    ${failedRuns  !== null ? `<div class="db-stat"><span class="db-stat-val db-bool-f">${failedRuns}</span><span class="db-stat-lbl">Failed</span></div>` : ''}
    <div class="db-stat"><span class="db-stat-val">${compat}</span><span class="db-stat-lbl">Compat results</span></div>
  `;
}