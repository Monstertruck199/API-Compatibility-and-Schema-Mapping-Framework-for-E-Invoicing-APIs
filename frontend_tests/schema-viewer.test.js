// /**
//  * @jest-environment jsdom
//  */

const {
  setFmt,
  svAnalyse,
  highlightError,
  cntFields,
  buildTree
} = require('../frontend/schema-viewer')

beforeEach(() => {
  jest.resetModules()
  document.body.innerHTML = `
        <button id="fj"></button>
        <button id="fx"></button>
        <input id="sv-url" />
        <input id="sv-name" />
        <div id="sv-list"></div>
        <div id="sv-viewer"></div>
    `

  global.fetch = jest.fn()
  global.alert = jest.fn()
  global.API_BASE_URL = 'http://localhost:5000'

  jest.useFakeTimers()

  jest.resetModules()
  moduleRef = require('../frontend/schema-viewer')

  global.svSchemas = [
    {
      name: 'Source API',
      schema: { properties: { a: { type: 'string' } } }
    },
    {
      name: 'Target API',
      schema: { properties: { b: { type: 'number' } } }
    }
  ]

  global.lastComparison = null
})

afterEach(() => {
  jest.clearAllMocks()
})

test('setFmt toggles correct format buttons', () => {
  setFmt('json')

  expect(document.getElementById('fj').classList.contains('on')).toBe(true)
  expect(document.getElementById('fx').classList.contains('on')).toBe(false)

  setFmt('xml')

  expect(document.getElementById('fj').classList.contains('on')).toBe(false)
  expect(document.getElementById('fx').classList.contains('on')).toBe(true)
})

test('highlightError temporarily sets border color', () => {
  const input = document.getElementById('sv-url')

  highlightError('sv-url')

  expect(input.style.borderColor).toBe('var(--red)')

  jest.advanceTimersByTime(1300)

  expect(input.style.borderColor).toBe('')
})

test('svAnalyse highlights error when URL is empty', async () => {
  document.getElementById('sv-url').value = ''

  await svAnalyse()

  const input = document.getElementById('sv-url')
  expect(input.style.borderColor).toBe('var(--red)')
})

test('svAnalyse adds schema and updates UI on success', async () => {
  document.getElementById('sv-url').value = 'http://test.com/api'
  document.getElementById('sv-name').value = 'Test API'

  fetch.mockResolvedValue({
    ok: true,
    json: async () => ({
      schema: { properties: { a: { type: 'string' } } },
      status: 200
    })
  })

  await svAnalyse()

  expect(fetch).toHaveBeenCalled()

  const list = document.getElementById('sv-list')
  expect(list.innerHTML).toContain('Test API')

  const viewer = document.getElementById('sv-viewer')
  expect(viewer.innerHTML).toContain('Test API')
})

test('svAnalyse shows alert on failed response', async () => {
  document.getElementById('sv-url').value = 'http://fail.com'

  fetch.mockResolvedValue({
    ok: false,
    json: async () => ({ error: 'Bad request' })
  })

  await svAnalyse()

  expect(alert).toHaveBeenCalledWith('Bad request')
})

test('renderSVList shows empty state when no schemas', () => {
  const { renderSVList } = require('../frontend/schema-viewer')
  renderSVList()

  const el = document.getElementById('sv-list')
  expect(el.innerHTML).toContain('No schemas loaded yet')
})

test('svPick updates active schema and re-renders', () => {
  const mod = require('../frontend/schema-viewer')

  document.body.innerHTML = `
    <div id="sv-list"></div>
    <div id="sv-viewer"></div>
  `

  mod._internal.svSchemas = [
    { name: 'A', url: 'a', fmt: 'json', schema: {} },
    { name: 'B', url: 'b', fmt: 'json', schema: {} }
  ]

  mod.svPick(1)

  const list = document.getElementById('sv-list')
  expect(list.innerHTML).toContain('B')
})

test('cntFields counts nested properties correctly', () => {
  const schema = {
    properties: {
      a: { type: 'string' },
      b: {
        properties: {
          c: { type: 'number' }
        }
      }
    }
  }

  expect(cntFields(schema)).toBe(3)
})

test('renderViewer displays schema metadata', () => {
  const mod = require('../frontend/schema-viewer')

  document.body.innerHTML = `
    <div id="sv-viewer"></div>
  `

  mod._internal.svSchemas = [
    {
      name: 'Test',
      url: 'http://x.com',
      fmt: 'json',
      schema: { properties: { a: { type: 'string' } } },
      status: 200
    }
  ]

  mod.renderViewer(0)

  const viewer = document.getElementById('sv-viewer')

  expect(viewer.innerHTML).toContain('Test')
  expect(viewer.innerHTML).toContain('http://x.com')
})

test('buildTree renders tree nodes', () => {
  const container = document.createElement('div')

  const schema = {
    type: 'object',
    properties: {
      name: { type: 'string' }
    }
  }

  buildTree(container, schema, 'root', 0, true)

  expect(container.innerHTML).toContain('name')
  expect(container.innerHTML).toContain('string')
})
