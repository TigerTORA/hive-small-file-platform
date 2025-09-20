#!/usr/bin/env node
/**
 * Quick Playwright check for /#/clusters UI without running full e2e.
 * - Navigates to /#/clusters
 * - Waits for key UI parts (title/table/actions)
 * - Captures console errors and a screenshot
 */
import { chromium } from 'playwright'
import fs from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const BASE_URL = process.env.BASE_URL || 'http://127.0.0.1:3000'
const TARGET_URL = `${BASE_URL}/#/clusters`

const outDirUrl = new URL('../../tmp/', import.meta.url)
const outDir = fileURLToPath(outDirUrl)
try { await fs.mkdir(outDir, { recursive: true }) } catch {}

const errors = []
const logs = []

const browser = await chromium.launch({ headless: true })
const context = await browser.newContext()
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
  await page.getByText('集群管理').first().waitFor({ state: 'visible', timeout: 15000 })

  // Actions
  result.steps.push('wait add button')
  await page.getByRole('button', { name: '添加集群' }).waitFor({ state: 'visible' })

  // Grid container
  result.steps.push('wait clusters grid')
  await page.locator('.clusters-grid').first().waitFor({ state: 'visible' })

  // Optional: check if any cluster cards render
  const cardCount = await page.locator('.cluster-card').count().catch(() => 0)
  logs.push(`cardCount=${cardCount}`)

  // Optional: check if any row renders
  // Backward check: legacy table view support
  const legacyRows = await page.locator('.el-table__body-wrapper tbody tr').count().catch(() => 0)
  if (legacyRows > 0) logs.push(`legacyRows=${legacyRows}`)

  // Screenshot
  const shotPath = fileURLToPath(new URL('clusters-page.png', outDirUrl))
  await page.screenshot({ path: shotPath, fullPage: false })
  result.screenshot = shotPath
  result.ok = true
} catch (e) {
  result.errors.push(String(e?.message || e))
} finally {
  result.errors.push(...errors)
  await browser.close().catch(() => {})
  // Write a simple json artifact
  const jsonPath = fileURLToPath(new URL('clusters-check.json', outDirUrl))
  await fs.writeFile(jsonPath, JSON.stringify({ ...result, logs }, null, 2))
  console.log(`[clusters-check] ok=${result.ok} screenshot=${result.screenshot || '-'} errors=${result.errors.length}`)
  if (result.errors.length) {
    console.log(result.errors.join('\n'))
  }
}
