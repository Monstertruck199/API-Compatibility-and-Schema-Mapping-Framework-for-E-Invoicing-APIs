function schemaOptions(selectedName = '') {
  return svSchemas.map((schema, index) => `
    <option value="${index}" ${schema.name === selectedName ? 'selected' : ''}>${schema.name}</option>
  `).join('');
}

// function renderComparisonSelectors() {
//   const el = document.getElementById('comparison-root');
//   if (!el) return;
//   el.innerHTML = `
//     <div class="card" style="margin-bottom:14px">
//       <div class="card-lbl">Choose source and target schemas</div>
//       <div class="cmp-grid">
//         <div>
//           <div class="ig-lbl">Source schema (API output)</div>
//           <select class="ifield" id="cmp-source">${schemaOptions()}</select>
//         </div>
//         <div>
//           <div class="ig-lbl">Target schema (API input)</div>
//           <select class="ifield" id="cmp-target">${schemaOptions()}</select>
//         </div>
//       </div>
//       <button class="analyse-btn" onclick="runComparison()">Run compatibility analysis</button>
//     </div>
//     <div class="card">
//       <div class="card-lbl">What the classifier checks</div>
//       <p class="muted-copy">Missing fields, extra fields, nesting differences, type mismatches, enum conflicts, and places where a mapping layer can bridge the gap.</p>
//     </div>
//   `;
// }

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

// async function runComparison() {
//   const sourceIndex = Number(document.getElementById('cmp-source').value);
//   const targetIndex = Number(document.getElementById('cmp-target').value);
//   const source = svSchemas[sourceIndex];
//   const target = svSchemas[targetIndex];
// 
//   try {
//     const response = await fetch('http://localhost:5000/api/compare', {
//       method: 'POST',
//       headers: { 'Content-Type': 'application/json' },
//       body: JSON.stringify({
//         source_name: source.name,
//         target_name: target.name,
//         source_schema: source.schema,
//         target_schema: target.schema,
//       }),
//     });
//     lastComparison = await response.json();
//     if (!response.ok) {
//       alert(lastComparison.error || 'Comparison failed');
//       return;
//     }
//     show('compat-result');
//   } catch (error) {
//     alert('Could not reach backend. Start backend/app.py before running the comparison.');
//   }
// }

function badgeClass(label) {
  if (label === 'Directly compatible') return 'ok';
  if (label === 'Compatible with mapping') return 'warn';
  return 'bad';
}

function renderCompatibilityResult() {
  const el = document.getElementById('compat-root');
  if (!el) return;

  if (!lastComparison) {
    el.innerHTML = `
      <div class="card empty-card">
        <div class="card-lbl">No comparison yet</div>
        <p class="muted-copy">Go to Schema Comparison and run an analysis first.</p>
      </div>
    `;
    return;
  }

  const summary = lastComparison.summary;
  const issues = lastComparison.issues.map(issue => `
    <div class="issue issue-${issue.kind}">
      <div class="issue-head">
        <span class="issue-code">${issue.code}</span>
        <span class="issue-severity">${issue.severity}</span>
      </div>
      <div class="issue-message">${issue.message}</div>
      <div class="issue-paths"><strong>Source:</strong> ${issue.source_path} &nbsp;·&nbsp; <strong>Target:</strong> ${issue.target_path}</div>
      <div class="issue-suggestion">${issue.suggestion}</div>
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
    <div class="card">
      <div class="card-lbl">Detailed findings</div>
      ${issues || '<div class="muted-copy">No issues detected.</div>'}
    </div>
  `;
}