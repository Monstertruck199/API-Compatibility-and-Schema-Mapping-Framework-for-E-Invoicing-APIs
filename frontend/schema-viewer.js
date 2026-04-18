let svFmt     = 'json';
let svCat     = 'transformation';
let svSchemas = [];
let svActive  = null;

function setFmt(f) {
  svFmt = f;
  document.getElementById('fj').classList.toggle('on', f === 'json');
  document.getElementById('fx').classList.toggle('on', f === 'xml');
}

function setCat(c) {
  svCat = c;
  document.getElementById('ct').classList.toggle('on', c === 'transformation');
  document.getElementById('cv').classList.toggle('on', c === 'validation');
  document.getElementById('cc').classList.toggle('on', c === 'communication');
}

async function svAnalyse() {
  const url  = document.getElementById('sv-url').value.trim();
  const name = document.getElementById('sv-name').value.trim();

  if (!url) { highlightError('sv-url'); return; }

  let data;
  try {
    const res = await fetch(`${API_BASE_URL}/api/analyze?url=${encodeURIComponent(url)}&format=${svFmt}`);
    data = await res.json();
    if (!res.ok) {
      alert(data.error || 'Request failed');
      return;
    }
  } catch (e) {
    alert('Could not reach backend. Is backend/app.py running?');
    return;
  }

  const useName = name || new URL(url).hostname;
  const entry = {
    name: useName,
    url,
    fmt: svFmt,
    schema: data.schema,
    status: data.status,
    category: svCat,
    apiId: null,
    outputSchemaId: null,
    inputSchemaId: null,
    persisted: false,
  };

  try {
    const apiRes = await fetch(`${API_BASE_URL}/api/apis`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: useName, category: svCat, base_url: url }),
    });
    if (apiRes.ok) {
      const api = await apiRes.json();
      entry.apiId = api.id;

      try {
        const outRes = await fetch(`${API_BASE_URL}/api/apis/${api.id}/schemas`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ direction: 'output', format: svFmt, schema: data.schema }),
        });
        if (outRes.ok) {
          const out = await outRes.json();
          entry.outputSchemaId = out.id;
        }
      } catch (e) {}

      try {
        const inRes = await fetch(`${API_BASE_URL}/api/apis/${api.id}/schemas`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ direction: 'input', format: svFmt, schema: data.schema }),
        });
        if (inRes.ok) {
          const inp = await inRes.json();
          entry.inputSchemaId = inp.id;
        }
      } catch (e) {}

      entry.persisted = !!(entry.outputSchemaId || entry.inputSchemaId);
    }
  } catch (e) {}

  const existing = svSchemas.findIndex(s => s.name === useName);
  if (existing >= 0) {
    svSchemas[existing] = entry;
    svActive = existing;
  } else {
    svSchemas.push(entry);
    svActive = svSchemas.length - 1;
  }

  renderSVList();
  renderViewer(svActive);

  document.getElementById('sv-url').value  = '';
  document.getElementById('sv-name').value = '';
}

async function svDelete(i) {
  const s = svSchemas[i];
  if (!s) return;

  if (s.persisted && s.apiId) {
    try {
      await fetch(`${API_BASE_URL}/api/apis/${s.apiId}`, { method: 'DELETE' });
    } catch (e) {}
  }

  svSchemas.splice(i, 1);

  if (svActive === i) {
    svActive = svSchemas.length ? 0 : null;
  } else if (svActive !== null && svActive > i) {
    svActive = svActive - 1;
  }

  renderSVList();
  const viewer = document.getElementById('sv-viewer');
  if (svActive !== null) {
    renderViewer(svActive);
  } else if (viewer) {
    viewer.innerHTML = '';
  }
}

async function loadFromDatabase() {
  let apis;
  try {
    const res = await fetch(`${API_BASE_URL}/api/apis`);
    if (!res.ok) return false;
    apis = await res.json();
  } catch (e) {
    return false;
  }

  if (!Array.isArray(apis) || apis.length === 0) return false;

  for (const api of apis) {
    try {
      const schemasRes = await fetch(`${API_BASE_URL}/api/apis/${api.id}/schemas`);
      if (!schemasRes.ok) continue;
      const schemas = await schemasRes.json();
      if (!schemas.length) continue;

      const outputs = schemas.filter(s => s.direction === 'output');
      const inputs  = schemas.filter(s => s.direction === 'input');
      const primary = outputs[0] || inputs[0];
      if (!primary) continue;

      svSchemas.push({
        name: api.name,
        url: api.base_url || '',
        fmt: primary.format || 'json',
        schema: primary.raw_schema,
        status: 200,
        category: api.category,
        apiId: api.id,
        outputSchemaId: outputs[0] ? outputs[0].id : null,
        inputSchemaId: inputs[0] ? inputs[0].id : null,
        persisted: true,
      });
    } catch (e) {}
  }

  if (svSchemas.length) {
    svActive = 0;
    renderSVList();
    renderViewer(svActive);
    return true;
  }
  return false;
}

function highlightError(id) {
  const el = document.getElementById(id);
  el.style.borderColor = 'var(--red)';
  setTimeout(() => el.style.borderColor = '', 1300);
}

function renderSVList() {
  const el = document.getElementById('sv-list');
  if (!svSchemas.length) {
    el.innerHTML = '<div class="empty-hint">No schemas loaded yet</div>';
    return;
  }
  el.innerHTML = svSchemas.map((s, i) => `
    <div class="sv-item ${i === svActive ? 'on' : ''}" onclick="svPick(${i})">
      <span class="sv-item-name">${s.name}</span>
      ${s.persisted ? `<span style="font-size:10px;padding:2px 6px;border-radius:4px;background:var(--green-bg);color:var(--green);border:1px solid var(--green-bd);margin-right:6px">DB</span>` : ''}
      <span class="fmt-pill fp-${s.fmt}">${s.fmt.toUpperCase()}</span>
      <span onclick="event.stopPropagation();svDelete(${i})" style="margin-left:8px;color:var(--text3);cursor:pointer;font-size:14px;padding:0 4px">×</span>
    </div>
  `).join('');
}

function svPick(i) {
  svActive = i;
  renderSVList();
  renderViewer(i);
}

function cntFields(schema) {
  let count = 0;
  function walk(node) {
    if (!node || typeof node !== 'object') return;
    if (node.properties) {
      Object.values(node.properties).forEach(v => { count++; walk(v); });
    }
    if (node.items) walk(node.items);
    if (node.schema) walk(node.schema);
  }
  walk(schema);
  return count;
}

function renderViewer(i) {
  if (i === null || !svSchemas[i]) return;
  const s  = svSchemas[i];
  const el = document.getElementById('sv-viewer');
  el.innerHTML = `
    <div class="schema-hdr">
      <div>
        <div class="schema-big">${s.name}</div>
        <div class="schema-meta">${s.url} &nbsp;·&nbsp; ${cntFields(s.schema)} fields</div>
      </div>
      <span class="s200">${s.status || 200}</span>
    </div>
    <hr class="divider" style="margin-top:0">
    <div class="tree" id="sv-tree"></div>
  `;
  buildTree(document.getElementById('sv-tree'), s.schema.schema || s.schema, 'root', 0, true);
}

function typeClass(t) {
  return 'tt-' + (t || 'unknown');
}

function buildTree(container, node, key, depth, isRoot) {
  const hasChildren = node.properties || (node.items && node.items.properties);
  const div = document.createElement('div');
  const row = document.createElement('div');
  row.className = 'tree-row';

  const tog = document.createElement('span');
  tog.className = 'tree-tog';
  if (hasChildren) tog.textContent = '▾';

  const dot = document.createElement('span');
  dot.className = 'tree-dot ' + ((node.required && node.required.length) ? 'td-req' : 'td-opt');

  const keyEl = document.createElement('span');
  keyEl.className = 'tree-key';
  keyEl.textContent = isRoot ? '{ root }' : key;

  const typeEl = document.createElement('span');
  typeEl.className = 'tree-type ' + typeClass(node.type);
  typeEl.textContent = node.type || 'unknown';

  row.append(tog, dot, keyEl, typeEl);

  if (node.enum) {
    const en = document.createElement('span');
    en.className = 'tree-enum';
    en.textContent = 'enum: ' + node.enum.map(v => `'${v}'`).join(', ');
    row.appendChild(en);
  }

  div.appendChild(row);

  if (hasChildren) {
    const kids = document.createElement('div');
    kids.className = 'tree-kids';
    const props = node.properties || (node.items && node.items.properties);
    if (props) Object.entries(props).forEach(([k, v]) => buildTree(kids, v, k, depth + 1, false));
    div.appendChild(kids);
  }

  container.appendChild(div);
}