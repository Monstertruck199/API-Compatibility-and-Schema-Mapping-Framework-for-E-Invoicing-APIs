/**
 * @jest-environment jsdom
 */

const {
  renderDatabasePanel,
  dbFetch,
  dbRefreshAll,
  dbSearch,
  dbRenderTable,
  dbToggleRow,
  dbFormatCell,
  dbRefreshStats
} = require('../frontend/database'); 

beforeEach(() => {
  document.body.innerHTML = `
    <div id="db-root"></div>
  `;

  global.fetch = jest.fn();
  global.alert = jest.fn();
  global.API_BASE_URL = 'http://localhost:5000';

  const mod = require('../frontend/database');

  mod._internal.dbState = {
    activeTable: 'apis',
    data: {},
    loading: {},
    error: {},   
    search: '',
    expandedRow: null,
  };
});

afterEach(() => {
  jest.clearAllMocks();
});

test('renderDatabasePanel renders layout and triggers fetch', async () => {
  fetch.mockResolvedValue({
    ok: true,
    json: async () => []
  });

  await renderDatabasePanel();
  await Promise.resolve(); 

  expect(document.querySelector('.db-layout')).not.toBeNull();
  expect(fetch).toHaveBeenCalled();
});

test('dbFetch loads data and updates count', async () => {
  document.body.innerHTML = `
    <span id="db-count-apis"></span>
  `;

  fetch.mockResolvedValue({
    ok: true,
    json: async () => [{ id: 1 }, { id: 2 }]
  });

  await dbFetch('apis');

  expect(fetch).toHaveBeenCalled();
  expect(document.getElementById('db-count-apis').textContent).toBe('2');
});

test('dbFetch handles API error', async () => {
  fetch.mockResolvedValue({
    ok: false,
    status: 500,
    json: async () => ({})
  });

  await dbFetch('apis');

  expect(fetch).toHaveBeenCalled();
});


test('dbRenderTable shows empty state when no data', () => {
  document.body.innerHTML = `
    <div id="db-table-wrap"></div>
    <span id="db-active-count"></span>
  `;

  dbRenderTable();

  expect(document.getElementById('db-table-wrap').innerHTML)
    .toContain('No records found');
});

test('dbRenderTable renders rows', () => {
  document.body.innerHTML = `
    <div id="db-table-wrap"></div>
    <span id="db-active-count"></span>
  `;

  const mod = require('../frontend/database');

  mod._internal.dbState.data['apis'] = [
    { id: 1, name: 'API A' }
  ];

  dbRenderTable();

  expect(document.getElementById('db-table-wrap').innerHTML)
    .toContain('API A');
});

test('dbSearch filters results', () => {
  document.body.innerHTML = `
    <div id="db-table-wrap"></div>
    <span id="db-active-count"></span>
  `;

  const mod = require('../frontend/database');

  mod._internal.dbState.data['apis'] = [
    { id: 1, name: 'Apple' },
    { id: 2, name: 'Banana' }
  ];

  dbSearch('apple');

  expect(document.getElementById('db-table-wrap').innerHTML)
    .toContain('Apple');
  expect(document.getElementById('db-table-wrap').innerHTML)
    .not.toContain('Banana');
});

test('dbToggleRow expands and collapses row', () => {
  document.body.innerHTML = `
    <div id="db-table-wrap"></div>
    <span id="db-active-count"></span>
  `;

  const mod = require('../frontend/database');

  mod._internal.dbState.data['apis'] = [
    { id: 1, name: 'API A', full_result: { x: 1 } }
  ];

  dbRenderTable();

  dbToggleRow(0);

  expect(document.getElementById('db-table-wrap').innerHTML)
    .toContain('db-expanded-row');
});


test('dbFormatCell formats booleans', () => {
  expect(dbFormatCell(true)).toContain('true');
  expect(dbFormatCell(false)).toContain('false');
});

test('dbFormatCell formats null', () => {
  expect(dbFormatCell(null)).toContain('null');
});

test('dbFormatCell formats compatibility', () => {
  expect(dbFormatCell('directly_compatible', 'compatibility'))
    .toContain('db-compat-ok');
});


test('dbRefreshAll calls fetch for all tables', async () => {
  fetch.mockResolvedValue({
    ok: true,
    json: async () => []
  });

  await dbRefreshAll();

  expect(fetch).toHaveBeenCalledTimes(3);
});


test('dbRefreshStats renders stats', () => {
  document.body.innerHTML = `
    <div id="db-stats"></div>
  `;

  const mod = require('../frontend/database');

  mod._internal.dbState.data = {
    apis: [{}, {}],
    transforms: [{ success: true }, { success: false }],
    compat_results: [{}]
  };

  dbRefreshStats();

  expect(document.getElementById('db-stats').innerHTML)
    .toContain('APIs');
  expect(document.getElementById('db-stats').innerHTML)
    .toContain('Transform runs');
});