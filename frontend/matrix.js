async function renderMatrixBuilder () {
  const el = document.getElementById('matrix-root')
  if (!el) return
  el.innerHTML = `
    <div id="matrix-table-wrap"></div>
  `
  buildMatrix()
}

function escapeRe (s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function highlight (text, query) {
  if (!query) return text
  return text.replace(new RegExp('(' + escapeRe(query) + ')', 'gi'), '<mark>$1</mark>')
}

function shortLabel (label) {
  if (label === 'directly_compatible') return 'Direct'
  if (label === 'compatible_with_mapping') return 'Mapping Required'
  if (label === 'incompatible') return 'Incompatible'
  return 'Direct'
}

function matrixCellClass (code) {
  if (code === 'directly_compatible' || code === 'same_schema') return 'ok'
  if (code === 'compatible_with_mapping') return 'warn'
  return 'bad'
}

async function buildMatrix () {
  try {
    const response = await fetch(`${API_BASE_URL}/api/matrix`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ schemas: svSchemas.map(({ name, schema }) => ({ name, schema })) })
    })
    const payload = await response.json()
    if (!response.ok) {
      alert(payload.error || 'Could not build matrix')
      return
    }
    newDrawMatrix(payload.matrix)
  } catch (error) {
    alert('Could not reach backend. Start backend/app.py before generating the matrix.')
  }
}

let matrixRows = []
const activeFilters = new Set(['ok', 'warn', 'bad'])

function newDrawMatrix (matrix) {
  matrixRows = []
  matrix.forEach(row => {
    row.forEach(cell => {
      if (cell.source != cell.target) {
        matrixRows.push(cell)
      }
    })
  })

  const wrap = document.getElementById('matrix-table-wrap')
  wrap.innerHTML = `
    <div class="search-row">
      <div class="search-group">
        <div class="search-label">Source API</div>
        <input class="search-input" id="search-source" placeholder="Filter Source..." oninput="renderMatrixRows()" />
      </div>
      <div class="search-group">
        <div class="search-label">Target API</div>
        <input class="search-input" id="search-target" placeholder="Filter target..." oninput="renderMatrixRows()" />
      </div>
    </div>
    <div class="card"> 
      <div class="matrix header">
        <div class="card-lbl">Compatibility matrix</div>
        <div class="matrix-filter-row">
          <span class="matrix-filter-lbl">Filter:</span>
          <button class="matrix-filter-btn active ok" data-filter="ok" onclick="toggleMatrixFilter('ok')">Direct</button>
          <button class="matrix-filter-btn active warn" data-filter="warn" onclick="toggleMatrixFilter('warn')">Mapping Required</button>
          <button class="matrix-filter-btn active bad" data-filter="bad" onclick="toggleMatrixFilter('bad')">Incompatible</button>
        </div>
      </div>

      <div id="matrix-result-count" class="matrix-result-count"></div>

      <table class="matrix-list-table">
        <thead>
          <tr>
            <th>Source API</th>
            <th>Target API</th>
            <th>Result</th>
            <th>Key Issues</th>
          </tr>
        </thead>
        <tbody id="matrix-tbody"></tbody>
      </table>
    </div>
  `

  renderMatrixRows()
}

function toggleMatrixFilter (filter) {
  if (activeFilters.has(filter)) {
    activeFilters.delete(filter)
  } else {
    activeFilters.add(filter)
  }
  document.querySelector(`.matrix-filter-btn[data-filter="${filter}"]`).classList.toggle('active')
  renderMatrixRows()
}

function renderMatrixRows () {
  const srcQ = (document.getElementById('search-source')?.value || '').trim().toLowerCase()
  const tgtQ = (document.getElementById('search-target')?.value || '').trim().toLowerCase()
  const tbody = document.getElementById('matrix-tbody')
  const count = document.getElementById('matrix-result-count')

  const filtered = matrixRows.filter(cell => {
    const cls = matrixCellClass(cell.compatibility)
    if (!activeFilters.has(cls)) return false
    if (srcQ && !cell.source.toLowerCase().includes(srcQ)) return false
    if (tgtQ && !cell.target.toLowerCase().includes(tgtQ)) return false
    return true
  })

  count.textContent = `Showing ${filtered.length} result${filtered.length !== 1 ? 's' : ''}`

  if (filtered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty-hint">No mappings available</td></tr>'
  } else {
    tbody.innerHTML = filtered.map(cell => {
      const cls = matrixCellClass(cell.compatibility)
      const label = shortLabel(cell.compatibility)
      const issues = cell.key_issues || cell.issues?.[0]?.message || ''
      return `
        <tr class="matrix-list-row">
          <td>${cell.source}</td>
          <td>${cell.target}</td>
          <td><span class="status-pill ${cls}">${label}</span></td>
          <td class="matrix-issues-cell">${issues}</td>
        </tr>
      `
    }).join('')
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    renderMatrixBuilder,
    buildMatrix,
    newDrawMatrix,
    renderMatrixRows,
    toggleMatrixFilter,
    highlight,
    shortLabel,
    matrixCellClass
  }
}
