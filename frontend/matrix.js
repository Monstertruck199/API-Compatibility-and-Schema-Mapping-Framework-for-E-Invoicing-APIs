async function renderMatrixBuilder() {
  const el = document.getElementById('matrix-root');
  if (!el) return;
  el.innerHTML = `
    <div id="matrix-table-wrap"></div>
  `;
  buildMatrix();
}

function shortLabel(label) {
  if (label === 'directly_compatible') return 'Direct';
  if (label === 'compatible_with_mapping') return 'Mapping Required';
  if (label === 'incompatible') return 'Incompatible';
  return 'Direct';
}

function matrixCellClass(code) {
  if (code === 'directly_compatible' || code === 'same_schema') return 'ok';
  if (code === 'compatible_with_mapping') return 'warn';
  return 'bad';
}

async function buildMatrix() {
  try {
    const response = await fetch('http://localhost:5050/api/matrix', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ schemas: svSchemas.map(({ name, schema }) => ({ name, schema })) }),
    });
    const payload = await response.json();
    if (!response.ok) {
      alert(payload.error || 'Could not build matrix');
      return;
    }
    newDrawMatrix(payload.matrix);
  } catch (error) {
    alert('Could not reach backend. Start backend/app.py before generating the matrix.');
  }
}

let matrixRows = [];
let activeFilters = new Set(['ok', 'warn', 'bad']);

function newDrawMatrix(matrix) {
  matrixRows = [];
  matrix.forEach(row => {
    row.forEach(cell => {
      if (cell.source != cell.target) {
        matrixRows.push(cell);
      }
    });
  });

  const wrap = document.getElementById('matrix-table-wrap');
  wrap.innerHTML = `
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
  `;

  renderMatrixRows();
}

function toggleMatrixFilter(filter) {
  if (activeFilters.has(filter)) {
    activeFilters.delete(filter);
  } else {
    activeFilters.add(filter);
  }
  document.querySelector(`.matrix-filter-btn[data-filter="${filter}"]`).classList.toggle('active');
  renderMatrixRows();
}

function renderMatrixRows() {
  const tbody = document.getElementById('matrix-tbody');
  const count = document.getElementById('matrix-result-count');

  const filtered = matrixRows.filter(cell => {
    const cls = matrixCellClass(cell.compatibility);
    if (!activeFilters.has(cls)) return false;
    return true;
  })

  count.textContent = `Showing ${filtered.length} result${filtered.length !== 1 ? 's' : ''}`;

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="empty-hint">No mappings available</td></tr>`;
  } else {
    tbody.innerHTML = filtered.map(cell => {
      const cls = matrixCellClass(cell.compatibility);
      const label = shortLabel(cell.compatibility);
      const issues = cell.key_issues || cell.issues?.[0]?.message || '';
      return `
        <tr class="matrix-list-row">
          <td>${cell.source}</td>
          <td>${cell.target}</td>
          <td><span class="status-pill ${cls}">${label}</span></td>
          <td class="matrix-issues-cell">${issues}</td>
        </tr>
      `;
    }).join('');
  }
}

// function drawMatrix(matrix) {
//   const wrap = document.getElementById('matrix-table-wrap');
//   const headers = matrix[0].map(cell => `<th>${cell.target}</th>`).join('');
//   const rows = matrix.map(row => `
//     <tr>
//       <th>${row[0].source}</th>
//       ${row.map(cell => `<td class="m-${matrixCellClass(cell.compatibility)}">${shortLabel(cell.compatibility)}</td>`).join('')}
//     </tr>
//   `).join('');
//   wrap.innerHTML = `
//     <div class="card">
//       <div class="card-lbl">Compatibility matrix</div>
//       <table class="matrix-table">
//         <thead>
//           <tr>
//             <th>Source \ Target</th>
//             ${headers}
//           </tr>
//         </thead>
//         <tbody>${rows}</tbody>
//       </table>
//     </div>
//   `;
// }