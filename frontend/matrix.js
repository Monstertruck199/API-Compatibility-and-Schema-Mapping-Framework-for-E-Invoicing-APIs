async function renderMatrixBuilder() {
  const el = document.getElementById('matrix-root');
  if (!el) return;
  el.innerHTML = `
    <div class="card" style="margin-bottom:14px">
      <div class="card-lbl">Generate matrix</div>
      <p class="muted-copy">This compares every loaded schema as a source against every loaded schema as a target.</p>
      <button class="analyse-btn" onclick="buildMatrix()">Build compatibility matrix</button>
    </div>
    <div id="matrix-table-wrap"></div>
  `;
}

function shortLabel(label) {
  if (label === 'directly_compatible') return 'Direct';
  if (label === 'compatible_with_mapping') return 'Mapping';
  if (label === 'incompatible') return 'Blocked';
  return 'Same';
}

function matrixCellClass(code) {
  if (code === 'directly_compatible' || code === 'same_schema') return 'ok';
  if (code === 'compatible_with_mapping') return 'warn';
  return 'bad';
}

async function buildMatrix() {
  try {
    const response = await fetch('http://localhost:5000/api/matrix', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ schemas: svSchemas.map(({ name, schema }) => ({ name, schema })) }),
    });
    const payload = await response.json();
    if (!response.ok) {
      alert(payload.error || 'Could not build matrix');
      return;
    }
    drawMatrix(payload.matrix);
  } catch (error) {
    alert('Could not reach backend. Start backend/app.py before generating the matrix.');
  }
}

function drawMatrix(matrix) {
  const wrap = document.getElementById('matrix-table-wrap');
  const headers = matrix[0].map(cell => `<th>${cell.target}</th>`).join('');
  const rows = matrix.map(row => `
    <tr>
      <th>${row[0].source}</th>
      ${row.map(cell => `<td class="m-${matrixCellClass(cell.compatibility)}">${shortLabel(cell.compatibility)}</td>`).join('')}
    </tr>
  `).join('');
  wrap.innerHTML = `
    <div class="card">
      <div class="card-lbl">Compatibility matrix</div>
      <table class="matrix-table">
        <thead>
          <tr>
            <th>Source \ Target</th>
            ${headers}
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}