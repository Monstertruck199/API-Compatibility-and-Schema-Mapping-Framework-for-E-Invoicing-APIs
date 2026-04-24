/**
 * @jest-environment jsdom
 */

const {
  schemaOptions,
  downloadReport,
  badgeClass,
  renderCompatibilityResult,
  runCompatibilityComparison,
  renderCompatibilityOutput
} = require('../frontend/compatibility-result'); // adjust filename if needed

beforeEach(() => {
  document.body.innerHTML = `
    <div id="compat-root"></div>
  `;

  global.fetch = jest.fn();
  global.alert = jest.fn();

  global.svSchemas = [
    {
      name: 'Source API',
      schema: { properties: { a: { type: 'string' } } }
    },
    {
      name: 'Target API',
      schema: { properties: { b: { type: 'number' } } }
    }
  ];

  global.lastComparison = null;
});

afterEach(() => {
  jest.clearAllMocks();
});


// ----------------------------------
// schemaOptions
// ----------------------------------
test('schemaOptions renders schema options', () => {
  const html = schemaOptions();

  expect(html).toContain('Source API');
  expect(html).toContain('Target API');
});

test('schemaOptions marks selected schema', () => {
  const html = schemaOptions('Target API');

  expect(html).toContain('selected');
  expect(html).toContain('Target API');
});


// ----------------------------------
// badgeClass
// ----------------------------------
test('badgeClass returns correct class', () => {
  expect(badgeClass('Directly compatible')).toBe('ok');
  expect(badgeClass('Compatible with mapping')).toBe('warn');
  expect(badgeClass('Anything else')).toBe('bad');
});


// ----------------------------------
// renderCompatibilityResult
// ----------------------------------
test('renderCompatibilityResult renders selectors', () => {
  renderCompatibilityResult();

  const root = document.getElementById('compat-root');

  expect(root.innerHTML).toContain('Source schema');
  expect(root.innerHTML).toContain('Target schema');
  expect(root.querySelector('#compat-source')).not.toBeNull();
  expect(root.querySelector('#compat-target')).not.toBeNull();
});

test('renderCompatibilityResult auto-runs comparison when >= 2 schemas', async () => {
  fetch.mockResolvedValue({
    ok: true,
    json: async () => ({
      source: 'Source API',
      target: 'Target API',
      summary: {
        compatibility_label: 'Directly compatible',
        blocking_issues: 0,
        mapping_issues: 0,
        informational_issues: 0
      },
      issues: []
    })
  });

  renderCompatibilityResult();

  await Promise.resolve();

  expect(fetch).toHaveBeenCalled();
});


// ----------------------------------
// runCompatibilityComparison
// ----------------------------------
test('runCompatibilityComparison calls API and updates UI', async () => {
  renderCompatibilityResult();

  document.getElementById('compat-source').value = '0';
  document.getElementById('compat-target').value = '1';

  fetch.mockResolvedValue({
    ok: true,
    json: async () => ({
      source: 'Source API',
      target: 'Target API',
      summary: {
        compatibility_label: 'Directly compatible',
        blocking_issues: 0,
        mapping_issues: 0,
        informational_issues: 0
      },
      issues: []
    })
  });

  await runCompatibilityComparison();

  expect(fetch).toHaveBeenCalledWith(
    'http://localhost:5000/api/compare',
    expect.objectContaining({
      method: 'POST'
    })
  );

  const output = document.getElementById('compat-result-output');
  expect(output.innerHTML).toContain('Directly compatible');
});

test('runCompatibilityComparison handles API failure', async () => {
  renderCompatibilityResult();

  document.getElementById('compat-source').value = '0';
  document.getElementById('compat-target').value = '1';

  fetch.mockResolvedValue({
    ok: false,
    json: async () => ({ error: 'Comparison failed' })
  });

  await runCompatibilityComparison();

  expect(alert).toHaveBeenCalledWith('Comparison failed');
});

test('runCompatibilityComparison handles network error', async () => {
  renderCompatibilityResult();

  document.getElementById('compat-source').value = '0';
  document.getElementById('compat-target').value = '1';

  fetch.mockRejectedValue(new Error('Network error'));

  await runCompatibilityComparison();

  expect(alert).toHaveBeenCalled();
});


// ----------------------------------
// renderCompatibilityOutput
// ----------------------------------
test('renderCompatibilityOutput shows empty state', () => {
  renderCompatibilityResult();

  renderCompatibilityOutput();

  const output = document.getElementById('compat-result-output');

  expect(output.innerHTML).toContain('No comparison yet');
});

test('renderCompatibilityOutput renders comparison result', () => {
  renderCompatibilityResult();

  global.lastComparison = {
    source: 'Source API',
    target: 'Target API',
    summary: {
      compatibility_label: 'Compatible with mapping',
      blocking_issues: 1,
      mapping_issues: 2,
      informational_issues: 3
    },
    issues: [
      {
        kind: 'blocking',
        message: 'Missing required field'
      }
    ]
  };

  renderCompatibilityOutput();

  const output = document.getElementById('compat-result-output');

  expect(output.innerHTML).toContain('Source API');
  expect(output.innerHTML).toContain('Target API');
  expect(output.innerHTML).toContain('Compatible with mapping');
  expect(output.innerHTML).toContain('Missing required field');
});

test('renderCompatibilityOutput handles no issues', () => {
  renderCompatibilityResult();

  global.lastComparison = {
    source: 'Source API',
    target: 'Target API',
    summary: {
      compatibility_label: 'Directly compatible',
      blocking_issues: 0,
      mapping_issues: 0,
      informational_issues: 0
    },
    issues: []
  };

  renderCompatibilityOutput();

  const output = document.getElementById('compat-result-output');

  expect(output.innerHTML).toContain('Schemas align');
});