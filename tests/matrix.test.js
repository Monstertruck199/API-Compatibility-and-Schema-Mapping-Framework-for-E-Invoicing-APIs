/**
 * @jest-environment jsdom
 */

const {
  renderMatrixBuilder,
  buildMatrix,
  newDrawMatrix,
  renderMatrixRows,
  toggleMatrixFilter,
  highlight,
  shortLabel,
  matrixCellClass
} = require('../frontend/matrix'); // adjust path

beforeEach(() => {
  document.body.innerHTML = `
    <div id="matrix-root"></div>
  `;

  global.fetch = jest.fn();
  global.alert = jest.fn();

  global.svSchemas = [
    { name: 'API A', schema: {} },
    { name: 'API B', schema: {} }
  ];
});

afterEach(() => {
  jest.clearAllMocks();
});


// ----------------------------------
// highlight
// ----------------------------------
test('highlight wraps matching text', () => {
  const result = highlight('hello world', 'world');
  expect(result).toContain('<mark>world</mark>');
});

test('highlight returns original text if no query', () => {
  expect(highlight('hello', '')).toBe('hello');
});


// ----------------------------------
// shortLabel
// ----------------------------------
test('shortLabel returns correct labels', () => {
  expect(shortLabel('directly_compatible')).toBe('Direct');
  expect(shortLabel('compatible_with_mapping')).toBe('Mapping Required');
  expect(shortLabel('incompatible')).toBe('Incompatible');
});


// ----------------------------------
// matrixCellClass
// ----------------------------------
test('matrixCellClass returns correct classes', () => {
  expect(matrixCellClass('directly_compatible')).toBe('ok');
  expect(matrixCellClass('compatible_with_mapping')).toBe('warn');
  expect(matrixCellClass('incompatible')).toBe('bad');
});


// ----------------------------------
// renderMatrixBuilder
// ----------------------------------
test('renderMatrixBuilder creates container and triggers build', async () => {
  fetch.mockResolvedValue({
    ok: true,
    json: async () => ({ matrix: [] })
  });

  await renderMatrixBuilder();

  expect(document.getElementById('matrix-table-wrap')).not.toBeNull();
  expect(fetch).toHaveBeenCalled();
});


// ----------------------------------
// buildMatrix
// ----------------------------------
test('buildMatrix calls API and renders matrix', async () => {
  fetch.mockResolvedValue({
    ok: true,
    json: async () => ({
      matrix: [
        [
          { source: 'API A', target: 'API B', compatibility: 'directly_compatible' }
        ]
      ]
    })
  });

  document.body.innerHTML = `<div id="matrix-table-wrap"></div>`;

  await buildMatrix();

  expect(fetch).toHaveBeenCalledWith(
    'http://localhost:5000/api/matrix',
    expect.objectContaining({
      method: 'POST'
    })
  );

  expect(document.getElementById('matrix-tbody')).not.toBeNull();
});

test('buildMatrix handles API error', async () => {
  fetch.mockResolvedValue({
    ok: false,
    json: async () => ({ error: 'Failed' })
  });

  await buildMatrix();

  expect(alert).toHaveBeenCalledWith('Failed');
});


// ----------------------------------
// newDrawMatrix
// ----------------------------------
test('newDrawMatrix renders table structure', () => {
  document.body.innerHTML = `<div id="matrix-table-wrap"></div>`;

  const matrix = [
    [
      { source: 'API A', target: 'API B', compatibility: 'directly_compatible' }
    ]
  ];

  newDrawMatrix(matrix);

  expect(document.getElementById('matrix-tbody')).not.toBeNull();
  expect(document.getElementById('search-source')).not.toBeNull();
});


// ----------------------------------
// renderMatrixRows
// ----------------------------------
test('renderMatrixRows displays rows', () => {
  document.body.innerHTML = `
    <input id="search-source" />
    <input id="search-target" />
    <div id="matrix-result-count"></div>
    <table>
        <tbody id="matrix-tbody"></tbody>
    </table>
  `;

  global.matrixRows = [
    {
      source: 'API A',
      target: 'API B',
      compatibility: 'directly_compatible',
      key_issues: ''
    }
  ];

  global.activeFilters = new Set(['ok', 'warn', 'bad']);

  renderMatrixRows();

  expect(document.getElementById('matrix-tbody').innerHTML)
    .toContain('API A');

  expect(document.getElementById('matrix-result-count').textContent)
    .toContain('Showing 1 result');
});

test('renderMatrixRows applies filtering', () => {
  document.body.innerHTML = `
    <input id="search-source" />
    <input id="search-target" />
    <div id="matrix-result-count"></div>
    <table>
        <tbody id="matrix-tbody"></tbody>
    </table>
  `;

  global.matrixRows = [
    { source: 'API A', target: 'API B', compatibility: 'directly_compatible' },
    { source: 'Other', target: 'API B', compatibility: 'directly_compatible' }
  ];

  global.activeFilters = new Set(['ok', 'warn', 'bad']);

  renderMatrixRows();

  expect(document.getElementById('matrix-tbody').innerHTML)
    .toContain('API A');

  expect(document.getElementById('matrix-tbody').innerHTML)
    .not.toContain('Other');
});

test('renderMatrixRows shows empty state', () => {
  document.body.innerHTML = `
    <div id="matrix-table-wrap"></div>
    <input id="search-source" />
    <input id="search-target" />
    <div id="matrix-result-count"></div>
    <table>
      <tbody id="matrix-tbody"></tbody>
    </table>
  `;

  newDrawMatrix([]);

  renderMatrixRows();

  expect(document.getElementById('matrix-tbody').innerHTML)
    .toContain('No mappings available');
});


// ----------------------------------
// toggleMatrixFilter
// ----------------------------------
test('toggleMatrixFilter updates filter and rerenders', () => {
    document.body.innerHTML = `
    <button class="matrix-filter-btn active ok" data-filter="ok"></button>

    <input id="search-source" />
    <input id="search-target" />
    <div id="matrix-result-count"></div>

    <table>
        <tbody id="matrix-tbody"></tbody>
    </table>
    `;

  global.matrixRows = [
    { source: 'API A', target: 'API B', compatibility: 'directly_compatible' }
  ];

  global.activeFilters = new Set(['ok', 'warn', 'bad']);

  toggleMatrixFilter('ok');

  expect(global.activeFilters.has('ok')).toBe(false);
});