let compSchemas = []

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
        <button class="analyse-btn" onclick="runComparison()">Run compatibility analysis</button>
    </div>
    <div class="card" id="comparison-output">
      <div class="card-lbl">What the classifier checks</div>
      <p class="muted-copy">Missing fields, extra fields, nesting differences, type mismatches, enum conflicts, and places where a mapping layer can bridge the gap.</p>
    </div>
  `;
}


async function runComparison() {
  const sourceIndex = Number(document.getElementById('cmp-source').value);
  const targetIndex = Number(document.getElementById('cmp-target').value);
  const source = svSchemas[sourceIndex];
  const target = svSchemas[targetIndex];

  try {
    const response = await fetch('http://localhost:5000/api/compare', {
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
    console.log("helloe", comparison)

    const test1 = source.properties
    const test2 = target.properties

    const allKeys = new Set([...Object.keys(test1), ...Object.keys(test2)]);

    const merged = Array.from(allKeys).reduce((acc, key) => {
        acc[key] = (test1[key] !== undefined && test2[key] !== undefined) 
            ? [test1[key], test2[key]] 
            : null; 
        return acc;
    }, {});

    const src = source?.properties || {};
    const tgt = target?.properties || {};

    const allBalls = new Set([
    ...Object.keys(src),
    ...Object.keys(tgt)
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
    console.log("BALLS", aligned)

    console.log(merged)

    const renderFields = (obj, tgt, comp) => {
        const idx = tgt === 'src' ? 0 : 1;
        return Object.entries(obj || {})
        .map(([key, [srcVal, tgtVal]]) => {
            const val = idx === 0 ? srcVal : tgtVal;
            let missing;

            if (val == null) missing = 'missing';
            if (val == null) {
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
                        <span class="field-type">${type}</span>
                    </div>`;
        })
        .join('') 
    };


    el.innerHTML = `
        <div class="card-lbl"></div>
        <div class="cmp-split">
            <div class "cmp-col">
                <div class="cmp-title">Field•type•required</div>
                ${renderFields(aligned, "src", merged)}
            </div>

            <div class "cmp-col">
                <div class="cmp-title">Field•type•required</div>
                ${renderFields(aligned, "tgt", merged)}
            </div>
        </div>
    `
}