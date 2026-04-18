
function schemaOptions(selectedName = '') {
  return svSchemas.map((schema, index) => `
    <option value="${index}" ${schema.name === selectedName ? 'selected' : ''}>${schema.name}</option>
  `).join('');
}

function renderComparisonSelectors() {
  const el = document.getElementById('comparison-root');
  if (!el) return;
  el.innerHTML = `
    <div class="card" style="margin-bottom:14px">
      <div class="cmp-grid">
        <div>
          <div class="ig-lbl">Source schema (API output)</div>
          <select class="ifield" id="cmp-source">${schemaOptions()}</select>
        </div>
        <div>
          <div class="ig-lbl">Target schema (API input)</div>
          <select class="ifield" id="cmp-target">${schemaOptions()}</select>
        </div>
      </div>
    </div>
    <div class="card" id="comparison-output">
      <div class="card-lbl">What the classifier checks</div>
      <p class="muted-copy">Missing fields, extra fields, nesting differences, type mismatches, enum conflicts, and places where a mapping layer can bridge the gap.</p>
    </div>
  `;
    document.getElementById('cmp-source').addEventListener('change', runComparison)
    document.getElementById('cmp-target').addEventListener('change', runComparison)
    if (svSchemas.length >= 2) {
        runComparison();
    }

    renderTransformer();
}

async function runComparison() {
  const sourceIndex = Number(document.getElementById('cmp-source').value);
  const targetIndex = Number(document.getElementById('cmp-target').value);
  const source = svSchemas[sourceIndex];
  const target = svSchemas[targetIndex];

  try {
    const response = await fetch('http://localhost:5050/api/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_name: source.name,
        target_name: target.name,
        source_schema: source.schema,
        target_schema: target.schema,
      }),
    });
    lastComparison = await response.json();
    if (!response.ok) {
      alert(lastComparison.error || 'Comparison failed');
      return;
    }
    renderComparison(lastComparison)
  } catch (error) {
    alert(error);
  }
}

function renderComparison(comparison) {
    const el = document.getElementById('comparison-output')
    const source = comparison.normalized_source
    const target = comparison.normalized_target

    const src = source?.properties || {};
    const tgt = target?.properties || {};

    const allBalls = new Set([
    ...Object.keys(src),
    ...Object.keys(tgt)
    ]);

    const allReqs = new Set([
        ...(source?.required || []),
        ...(target?.required || [])
    ])

    const aligned = Object.fromEntries(
    [...allBalls].map(key => [
        key,
        [
        key in src ? src[key] : null,
        key in tgt ? tgt[key] : null
        ]
    ])
    );

    const renderFields = (obj, tgt, reqs) => {
        const idx = tgt === 'src' ? 0 : 1;
        return Object.entries(obj || {})
        .map(([key, [srcVal, tgtVal]]) => {
            const val = idx === 0 ? srcVal : tgtVal;
            let missing;
            const req = allReqs.has(key) ? 'required' : 'optional';

            if ((idx === 0 && tgtVal == null) || (idx === 1 && srcVal == null)) {
                missing = 'missing';
            } else if (val == null) {
                return `<div class="field-row null">
                        <span class="field-name">--</span>
                        <span class="field-type">not present</span>
                    </div>`;
            } else {
                missing = "direct"
            }

            const type = val.type || 'unknown';
            return `<div class="field-row ${missing}">
                        <span class="field-name">${key}</span>
                        <span class="field-type">${type}•${req}</span>
                    </div>`;
        })
        .join('') 
    };

    el.innerHTML = `
        <div class="card-lbl"></div>
        <div class="cmp-split">
            <div class="cmp-col">
                <div class="cmp-title">Field•type•required</div>
                ${renderFields(aligned, "src", allReqs)}
            </div>

            <div class="cmp-col">
                <div class="cmp-title">Field•type•required</div>
                ${renderFields(aligned, "tgt", allReqs)}
            </div>
        </div>
    `
}

function renderTransformer() {
  const existing = document.getElementById('transformer-root');
  if (existing) existing.remove();

  const el = document.getElementById('comparison-root');
  if (!el) return;

  const wrapper = document.createElement('div');
  wrapper.id = 'transformer-root';
  wrapper.innerHTML = `
    <div class="card transformer-card">
      <div class="card-lbl">Data Transformer</div>
      <div class="cmp-grid transformer-grid">
        <div>
          <div class="ig-lbl">Input (source format)</div>
          <textarea
            id="transformer-input"
            class="ifield transformer-textarea"
            rows="10"
            placeholder='{\n  "field": "value"\n}'
          ></textarea>
        </div>
        <div>
          <div class="ig-lbl">Output (target format)</div>
          <div id="transformer-warning"></div>
          <pre id="transformer-output" class="ifield transformer-output" data-placeholder="Run transform to see output…"></pre>
        </div>
      </div>
      <div class="transformer-actions">
        <span id="transformer-status" class="transformer-status"></span>
        <div class="fmt-row">
          <button class="fmt-btn on" id="tfmt-json" onclick="setTransformFmt('json')">JSON</button>
          <button class="fmt-btn"    id="tfmt-xml"  onclick="setTransformFmt('xml')">XML</button>
        </div>
        <button class="analyse-btn transformer-btn" onclick="runTransform()">Transform →</button>
      </div>
    </div>
  `;
  el.appendChild(wrapper);
}

let transformFmt = 'json';
function setTransformFmt(fmt) {
  transformFmt = fmt;
  document.getElementById('tfmt-json').classList.toggle('on', fmt === 'json');
  document.getElementById('tfmt-xml').classList.toggle('on', fmt === 'xml');
}

async function runTransform() {
  const sourceIndex = Number(document.getElementById('cmp-source').value);
  const targetIndex = Number(document.getElementById('cmp-target').value);
  const source = svSchemas[sourceIndex];
  const target = svSchemas[targetIndex];

  const inputRaw = document.getElementById('transformer-input').value.trim();
  const outputEl  = document.getElementById('transformer-output');
  const statusEl  = document.getElementById('transformer-status');

  if (!inputRaw) { outputEl.textContent = 'No input provided.'; return; }

  let inputData;
  try {
    inputData = JSON.parse(inputRaw);
  } catch {
    outputEl.textContent = '⚠ Invalid JSON in input.';
    return;
  }

  outputEl.innerHTML = '<span class="muted-copy">Transforming…</span>';
  statusEl.textContent = '';

  try {
    const res = await fetch('http://localhost:5000/api/transform', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_schema: source.schema,
        target_schema: target.schema,
        data: inputData,
        format: transformFmt,
      }),
    });

    const json = await res.json();
    if (!res.ok) throw new Error(json.error || 'Transform failed');

    const warningEl = document.getElementById('transformer-warning');
    const status = json.mapping_status;
    const warnings = json.warnings || [];

    warningEl.innerHTML = '';

    if (status && status !== 'ok' && status !== 'full') {
      const warningLines = warnings.length
        ? warnings.map(w => `<li>${w}</li>`).join('')
        : '<li>Fields may be dropped, renamed, or left empty.</li>';

      warningEl.innerHTML = `
        <div class="transform-warning">
          ⚠ Schemas are <strong>${status}</strong> — this is the closest possible mapping, but data loss or gaps may occur:
          <ul>${warningLines}</ul>
        </div>
      `;
    }

    outputEl.textContent = transformFmt === 'xml'
      ? json.result
      : JSON.stringify(json.result, null, 2);

    statusEl.textContent = status === 'ok' || 'full' ? '✓ Done' : `⚠ Done (${status})`;
  } catch (err) {
    outputEl.textContent = `Error: ${err.message}`;
    statusEl.textContent = '';
  }
}