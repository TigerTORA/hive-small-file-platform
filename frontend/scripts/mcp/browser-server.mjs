#!/usr/bin/env node
// Minimal MCP server exposing a Playwright-powered "headless browser"
// Tools:
// - navigate(url)
// - click(selector)
// - type(selector, text, clear?)
// - waitFor(selector, state?, timeout?)
// - screenshot(selector?, fullPage?, path?)
// - evaluate(script)

import { Server } from '@modelcontextprotocol/sdk/server/index.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio-transport.js'

const launchHeadful = process.env.HEADFUL === '1' || process.env.HEADLESS === 'false'
const defaultTimeout = Number(process.env.MCP_BROWSER_TIMEOUT || 15000)

let browser
let context
let page

async function ensurePage() {
  if (page) return page
  const { chromium } = await import('playwright')
  browser = await chromium.launch({ headless: !launchHeadful })
  context = await browser.newContext()
  page = await context.newPage()
  page.setDefaultTimeout(defaultTimeout)
  return page
}

async function dispose() {
  try { await context?.close() } catch {}
  try { await browser?.close() } catch {}
  page = undefined
  context = undefined
  browser = undefined
}

const server = new Server({
  name: 'mcp-playwright-browser',
  version: '0.1.0',
  capabilities: { tools: {} }
})

server.tool('navigate', {
  description: 'Navigate the browser to a URL',
  inputSchema: {
    type: 'object',
    properties: {
      url: { type: 'string' }
    },
    required: ['url']
  },
  handler: async ({ url }) => {
    const p = await ensurePage()
    await p.goto(url)
    return { content: [{ type: 'text', text: `navigated: ${url}` }] }
  }
})

server.tool('click', {
  description: 'Click a DOM element by selector',
  inputSchema: {
    type: 'object',
    properties: {
      selector: { type: 'string' }
    },
    required: ['selector']
  },
  handler: async ({ selector }) => {
    const p = await ensurePage()
    await p.click(selector)
    return { content: [{ type: 'text', text: `clicked: ${selector}` }] }
  }
})

server.tool('type', {
  description: 'Type text into an element',
  inputSchema: {
    type: 'object',
    properties: {
      selector: { type: 'string' },
      text: { type: 'string' },
      clear: { type: 'boolean' }
    },
    required: ['selector', 'text']
  },
  handler: async ({ selector, text, clear = false }) => {
    const p = await ensurePage()
    const el = p.locator(selector)
    if (clear) await el.fill('')
    await el.type(text)
    return { content: [{ type: 'text', text: `typed into ${selector}` }] }
  }
})

server.tool('waitFor', {
  description: 'Wait for a selector to reach a state',
  inputSchema: {
    type: 'object',
    properties: {
      selector: { type: 'string' },
      state: { type: 'string', enum: ['visible', 'attached', 'detached', 'hidden'] },
      timeout: { type: 'number' }
    },
    required: ['selector']
  },
  handler: async ({ selector, state = 'visible', timeout }) => {
    const p = await ensurePage()
    await p.waitForSelector(selector, { state, timeout })
    return { content: [{ type: 'text', text: `waited: ${selector} (${state})` }] }
  }
})

server.tool('screenshot', {
  description: 'Take a screenshot (full page or selector)',
  inputSchema: {
    type: 'object',
    properties: {
      selector: { type: 'string' },
      fullPage: { type: 'boolean' },
      path: { type: 'string' }
    }
  },
  handler: async ({ selector, fullPage = false, path }) => {
    const p = await ensurePage()
    let buffer
    if (selector) {
      const el = p.locator(selector)
      await el.waitFor({ state: 'visible' })
      buffer = await el.screenshot()
    } else {
      buffer = await p.screenshot({ fullPage })
    }
    if (path) {
      // write file lazily without importing fs/promises upfront
      const fs = await import('node:fs/promises')
      await fs.writeFile(path, buffer)
    }
    const b64 = buffer.toString('base64')
    return { content: [{ type: 'text', text: `screenshot (bytes=${buffer.length})` }, { type: 'image', data: b64, mimeType: 'image/png' }] }
  }
})

server.tool('evaluate', {
  description: 'Evaluate JS in the page context and return the result as text',
  inputSchema: {
    type: 'object',
    properties: { script: { type: 'string' } },
    required: ['script']
  },
  handler: async ({ script }) => {
    const p = await ensurePage()
    const result = await p.evaluate(script)
    return { content: [{ type: 'text', text: typeof result === 'string' ? result : JSON.stringify(result) }] }
  }
})

process.on('SIGINT', async () => { await dispose(); process.exit(0) })
process.on('SIGTERM', async () => { await dispose(); process.exit(0) })

const transport = new StdioServerTransport()
await server.connect(transport)
console.error('[mcp-browser] ready on stdio (Playwright)')
