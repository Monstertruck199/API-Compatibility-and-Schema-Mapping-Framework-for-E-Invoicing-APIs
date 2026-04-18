let svFmt     = 'json';
let svSchemas = [];
let svActive  = null;

function setFmt(f) {
  svFmt = f;
  document.getElementById('fj').classList.toggle('on', f === 'json');
  document.getElementById('fx').classList.toggle('on', f === 'xml');
}

async function svAnalyse() {
  const url  = document.getElementById('sv-url').value.trim();
  const name = document.getElementById('sv-name').value.trim();

  if (!url) { highlightError('sv-url'); return; }

  try {
    const res  = await fetch(`http://localhost:5050/api/analyze?url=${encodeURIComponent(url)}&format=${svFmt}`);
    const data = await res.json();

    if (!res.ok) {
      alert(data.error || 'Request failed');
      return;
    }

    const useName = name || new URL(url).hostname;
    svSchemas.push({ name: useName, url, fmt: svFmt, schema: data.schema, status: data.status });
    svActive = svSchemas.length - 1;

    renderSVList();
    renderViewer(svActive);

    document.getElementById('sv-url').value  = '';
    document.getElementById('sv-name').value = '';
  } catch (e) {
    alert('Could not reach backend. Is backend/app.py running?');
  }
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
      <span class="fmt-pill fp-${s.fmt}">${s.fmt.toUpperCase()}</span>
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