#!/usr/bin/env node
/**
 * Quick Playwright check for /#/tasks UI.
 * - Seeds selectedCluster in localStorage
 * - Navigates to /#/tasks
 * - Waits for key UI parts (title/cards/tab)
 * - Captures console errors and a screenshot
 */
import { chromium } from 'playwright'
import fs from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const BASE_URL = process.env.BASE_URL || 'http://127.0.0.1:3000'
const TARGET_URL = `${BASE_URL}/#/tasks`

const outDirUrl = new URL('../../tmp/', import.meta.url)
const outDir = fileURLToPath(outDirUrl)
try { await fs.mkdir(outDir, { recursive: true }) } catch {}

const errors = []
const logs = []

const browser = await chromium.launch({ headless: true })
const context = await browser.newContext()
context.addInitScript(() => {
  try { localStorage.setItem('selectedCluster', (globalThis.__clusterId || '1')) } catch {}
})
const page = await context.newPage()

page.on('console', msg => {
  const type = msg.type()
  const text = msg.text()
  if (type === 'error') errors.push(text)
  logs.push(`[${type}] ${text}`)
})

const result = { ok: false, steps: [], errors: [], screenshot: null }

try {
  result.steps.push(`goto ${TARGET_URL}`)
  await page.goto(TARGET_URL)

  // Title
  result.steps.push('wait title')
  await page.getByText('任务管理').first().waitFor({ state: 'visible', timeout: 20000 })

  // Filters + unified table
  result.steps.push('wait filters pane')
  await page.locator('.filters-pane').first().waitFor({ state: 'visible' })
  result.steps.push('wait unified table header')
  await page.getByText('任务列表').first().waitFor({ state: 'visible' })
  result.steps.push('wait table element')
  await page.locator('.cloudera-data-table').first().waitFor({ state: 'visible' })

  // Screenshot
  const shotPath = fileURLToPath(new URL('tasks-page.png', outDirUrl))
  await page.screenshot({ path: shotPath })
  result.screenshot = shotPath
  result.ok = true
} catch (e) {
  result.errors.push(String(e?.message || e))
} finally {
  result.errors.push(...errors)
  await browser.close().catch(() => {})
  const jsonPath = fileURLToPath(new URL('tasks-check.json', outDirUrl))
  await fs.writeFile(jsonPath, JSON.stringify({ ...result, logs }, null, 2))
  console.log(`[tasks-check] ok=${result.ok} screenshot=${result.screenshot || '-'} errors=${result.errors.length}`)
  if (result.errors.length) console.log(result.errors.join('\n'))
}
