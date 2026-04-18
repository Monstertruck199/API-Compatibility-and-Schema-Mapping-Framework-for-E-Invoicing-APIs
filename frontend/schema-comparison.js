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
  document.getElementById('cmp-source').addEventListener('change', runComparison);
  document.getElementById('cmp-target').addEventListener('change', runComparison);
  if (svSchemas.length >= 2) {
    runComparison();
  }
}

async function runComparison() {
  const sourceIndex = Number(document.getElementById('cmp-source').value);
  const targetIndex = Number(document.getElementById('cmp-target').value);
  const source = svSchemas[sourceIndex];
  const target = svSchemas[targetIndex];

  let result = null;

  if (source.apiId && target.apiId) {
    try {
      const dbRes = await fetch(`${API_BASE_URL}/api/compatibility/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_api_id: source.apiId, target_api_id: target.apiId }),
      });
      if (dbRes.ok) {
        result = await dbRes.json();
      }
    } catch (e) {}
  }

  if (!result) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_name: source.name,
          target_name: target.name,
          source_schema: source.schema,
          target_schema: target.schema,
        }),
      });
      result = await response.json();
      if (!response.ok) {
        alert(result.error || 'Comparison failed');
        return;
      }
    } catch (error) {
      alert(error);
      return;
    }
  }

  lastComparison = result;
  renderComparison(lastComparison);
}

function renderComparison(comparison) {
  const el = document.getElementById('comparison-output');
  const source = comparison.normalized_source;
  const target = comparison.normalized_target;

  const src = source?.properties || {};
  const tgt = target?.properties || {};

  const allBalls = new Set([
    ...Object.keys(src),
    ...Object.keys(tgt)
  ]);

  const allReqs = new Set([
    ...(source?.required || []),
    ...(target?.required || [])
  ]);

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
          missing = "direct";
        }

        const type = val.type || 'unknown';
        return `<div class="field-row ${missing}">
                  <span class="field-name">${key}</span>
                  <span class="field-type">${type}•${req}</span>
                </div>`;
      })
      .join('');
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
  `;
}