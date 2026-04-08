function schemaOptions(selectedName = '') {
  return svSchemas.map((schema, index) => `
    <option value="${index}" ${schema.name === selectedName ? 'selected' : ''}>${schema.name}</option>
  `).join('');
}

async function downloadReport(format = 'pdf') {
  const el = document.getElementById('compat-root');
  if (!el || !lastComparison) return;

  const btn = document.getElementById('download-btn');
  btn.textContent = 'Generating...';
  btn.disabled = true;

  try {
    const canvas = await html2canvas(el, {
      scale: 2,
      useCORS: true,
      backgroundColor: null,
    });

    const filename = `${lastComparison.source}-to-${lastComparison.target}`.replace(/\s+/g, '_');

    if (format === 'png') {
      const link = document.createElement('a');
      link.download = `${filename}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } else {
      const { jsPDF } = window.jspdf;
      const imgData = canvas.toDataURL('image/png');
      const pxToMm = 0.264583;
      const imgW = canvas.width * pxToMm;
      const imgH = canvas.height * pxToMm;
      const pdf = new jsPDF({ orientation: imgW > imgH ? 'l' : 'p', unit: 'mm', format: [imgW, imgH] });
      pdf.addImage(imgData, 'PNG', 0, 0, imgW, imgH);
      pdf.save(`${filename}.pdf`);
    }
  } finally {
    btn.textContent = '\u2913 Download report';
    btn.disabled = false;
  }

}

function badgeClass(label) {
  if (label === 'Directly compatible') return 'ok';
  if (label === 'Compatible with mapping') return 'warn';
  return 'bad';
}

function renderCompatibilityResult() {
  const el = document.getElementById('compat-root');
  if (!el) return;

  el.innerHTML = `
    <div class="card" style="margin-bottom:14px">
      <div class="cmp-grid">
        <div>
          <div class="ig-lbl">Source schema (API output)</div>
          <select class="ifield" id="compat-source">${schemaOptions(lastComparison?.source)}</select>
        </div>
        <div>
          <div class="ig-lbl">Target schema (API input)</div>
          <select class="ifield" id="compat-target">${schemaOptions(lastComparison?.target)}</select>
        </div>
      </div>
    </div>
    <div id="compat-result-output"></div>
  `;

  document.getElementById('compat-source').addEventListener('change', runCompatibilityComparison);
  document.getElementById('compat-target').addEventListener('change', runCompatibilityComparison);

  if (lastComparison) {
    renderCompatibilityOutput();
  } else if (svSchemas.length >= 2) {
    runCompatibilityComparison();
  }
}

async function runCompatibilityComparison() {
  const sourceIndex = Number(document.getElementById('compat-source').value);
  const targetIndex = Number(document.getElementById('compat-target').value);
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
    renderCompatibilityOutput();
  } catch (error) {
    alert(error);
  }
}

function renderCompatibilityOutput() {
  const el = document.getElementById('compat-result-output');
  if (!el) return;

  if (!lastComparison) {
    el.innerHTML = `
      <div class="card empty-card">
        <div class="card-lbl">No comparison yet</div>
        <p class="muted-copy">Select two schemas above to run an analysis.</p>
      </div>
    `;
    return;
  }

  const summary = lastComparison.summary;
  const issues = lastComparison.issues.map(issue => `
    <div class="issue issue-${issue.kind}">
      <div class="issue-message">${issue.message}</div>
    </div>
  `).join('');

  el.innerHTML = `
    <div class="card" style="margin-bottom:14px">
      <div class="result-top">
        <div>
          <div class="card-lbl">Result</div>
          <div class="schema-big">${lastComparison.source} → ${lastComparison.target}</div>
        </div>
        <div>
          <div class="download-bar">
            <button id="download-btn" class="analyse-btn" onclick="downloadReport('pdf')">↓ Download report</button>
            <button class="analyse-btn secondary" onclick="downloadReport('png')">↓ Save as PNG</button>
            <span class="status-pill ${badgeClass(summary.compatibility_label)}">${summary.compatibility_label}</span>
          </div>
        </div>
      </div>
      <div class="summary-grid">
        <div class="stat-box"><div class="stat-num">${summary.blocking_issues}</div><div class="stat-lbl">Blocking issues</div></div>
        <div class="stat-box"><div class="stat-num">${summary.mapping_issues}</div><div class="stat-lbl">Mapping issues</div></div>
        <div class="stat-box"><div class="stat-num">${summary.informational_issues}</div><div class="stat-lbl">Info issues</div></div>
        <div class="stat-box"><div class="stat-num">${summary.issue_count}</div><div class="stat-lbl">Total findings</div></div>
      </div>
    </div>
    <div class="card-lbl">Issues and Recommendations</div>
    ${issues || '<div class="stat-box">Schemas align - no mapping required</div>'}
  `;
}