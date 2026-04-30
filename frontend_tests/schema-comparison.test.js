/**
 * @jest-environment jsdom
 */

const {
  schemaOptions,
  renderComparisonSelectors,
  runComparison,
  renderComparison
} = require('../frontend/schema-comparison')

beforeEach(() => {
  document.body.innerHTML = `
    <div id="comparison-root"></div>
    `
  global.fetch = jest.fn()
  global.alert = jest.fn()
  global.API_BASE_URL = 'http://localhost:5000'

  global.runComparison = jest.fn()

  jest.resetModules()
  moduleRef = require('../frontend/schema-comparison')

  global.svSchemas = [
    {
      name: 'Schema A',
      schema: {
        properties: {
          a: { type: 'string' }
        },
        required: ['a']
      }
    },
    {
      name: 'Schema B',
      schema: {
        properties: {
          b: { type: 'number' }
        },
        required: []
      }
    }
  ]
})

afterEach(() => {
  jest.clearAllMocks()
})

test('schemaOptions renders option list', () => {
  const html = schemaOptions()
  expect(html).toContain('Schema A')
  expect(html).toContain('Schema B')
})

test('schemaOptions marks selected option', () => {
  const html = schemaOptions('Schema B')

  expect(html).toContain('selected')
  expect(html).toContain('Schema B')
})

test('renderComparisonSelectors renders dropdowns', () => {
  renderComparisonSelectors()

  const root = document.getElementById('comparison-root')

  expect(root.innerHTML).toContain('Source schema')
  expect(root.innerHTML).toContain('Target schema')
  expect(root.querySelector('#cmp-source')).not.toBeNull()
  expect(root.querySelector('#cmp-target')).not.toBeNull()
})

test('change event triggers comparison logic', async () => {
  renderComparisonSelectors()

  document.getElementById('cmp-source').value = '0'
  document.getElementById('cmp-target').value = '1'

  fetch.mockResolvedValue({
    ok: true,
    json: async () => ({})
  })

  const source = document.getElementById('cmp-source')
  source.dispatchEvent(new Event('change'))

  expect(fetch).toHaveBeenCalled()
})

test('renderComparisonSelectors auto-runs comparison when >= 2 schemas', async () => {
  renderComparisonSelectors()

  await Promise.resolve()

  expect(fetch).toHaveBeenCalled()
})

test('runComparison calls API and renders comparison', async () => {
  document.body.innerHTML = `
    <div id="comparison-root"></div>
    <div id="comparison-output"></div>
  `

  global.svSchemas = [
    { name: 'A', schema: {} },
    { name: 'B', schema: {} }
  ]

  renderComparisonSelectors()

  document.getElementById('cmp-source').value = '0'
  document.getElementById('cmp-target').value = '1'

  const mockResponse = {
    normalized_source: {
      properties: { a: { type: 'string' } },
      required: ['a']
    },
    normalized_target: {
      properties: { b: { type: 'number' } },
      required: []
    }
  }

  fetch.mockResolvedValue({
    ok: true,
    json: async () => mockResponse
  })

  await runComparison()

  expect(fetch).toHaveBeenCalledWith(
    'http://localhost:5000/api/compare',
    expect.objectContaining({
      method: 'POST'
    })
  )

  const output = document.getElementById('comparison-output')

  expect(output.innerHTML).toContain('a')
  expect(output.innerHTML).toContain('b')
})

test('runComparison shows alert on API error', async () => {
  renderComparisonSelectors()

  document.getElementById('cmp-source').value = '0'
  document.getElementById('cmp-target').value = '1'

  fetch.mockResolvedValue({
    ok: false,
    json: async () => ({ error: 'Comparison failed' })
  })

  await runComparison()

  expect(alert).toHaveBeenCalledWith('Comparison failed')
})

test('runComparison handles fetch failure', async () => {
  renderComparisonSelectors()

  document.getElementById('cmp-source').value = '0'
  document.getElementById('cmp-target').value = '1'

  fetch.mockRejectedValue(new Error('Network error'))

  await runComparison()

  expect(alert).toHaveBeenCalled()
})

test('renderComparison displays aligned fields', () => {
  document.body.innerHTML += '<div id="comparison-output"></div>'

  const comparison = {
    normalized_source: {
      properties: {
        a: { type: 'string' }
      },
      required: ['a']
    },
    normalized_target: {
      properties: {
        b: { type: 'number' }
      },
      required: []
    }
  }

  renderComparison(comparison)

  const output = document.getElementById('comparison-output')

  expect(output.innerHTML).toContain('a')
  expect(output.innerHTML).toContain('b')
  expect(output.innerHTML).toContain('string')
  expect(output.innerHTML).toContain('number')
})

test('renderComparison marks missing fields correctly', () => {
  document.body.innerHTML += '<div id="comparison-output"></div>'

  const comparison = {
    normalized_source: {
      properties: {
        onlyInSource: { type: 'string' }
      },
      required: []
    },
    normalized_target: {
      properties: {},
      required: []
    }
  }

  renderComparison(comparison)

  const output = document.getElementById('comparison-output')

  expect(output.innerHTML).toContain('missing')
})

test('renderComparison handles empty schemas', () => {
  document.body.innerHTML += '<div id="comparison-output"></div>'

  renderComparison({
    normalized_source: {},
    normalized_target: {}
  })

  const output = document.getElementById('comparison-output')

  expect(output.innerHTML).toContain('cmp-split')
})
