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
    // show('compat-result');
    // svSchemas.push({ name: useName, url, fmt: svFmt, schema: data.schema, status: data.status });
    // svActive = svSchemas.length - 1;

    /// Normalized_source and normalized_target
    ///lastComparison.normalized_source.properties.data.properties
    console.log("hello")
    console.log(lastComparison)
    renderComparison(lastComparison)
  } catch (error) {
    alert('Could not reach backend. Start backend/app.py before running the comparison.');
  }
}


function renderComparison(comparison) {
    const el = document.getElementById('comparison-output')
    const source = comparison.normalized_source.properties.data.properties
    const target = comparison.normalized_target.properties.data.properties

    const renderFields = (obj) => {
        return Object.entries(obj || {})
        .map(([KeyboardEvent, val]) => {
            const type = val.type || 'unknown';
            return `<div class="field-row">
                        <span class="field-name>${key}</span>
                        <span class="field-type>${key}</span>
                    </div>`;
        })
        .join('')
    };


    el.innerHTML = `
        <div class="card-lbl">Schema Comparison</div>
        <div class="cmp-split">
            <div class "cmp-col">
                <div class="cmp-title">Source</div>
                ${renderFields(source)}
            </div>

        
    `
}