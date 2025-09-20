#!/usr/bin/env node
/**
 * Quick Playwright check for /#/tables UI without running the full e2e.
 * - Seeds selectedCluster in localStorage
 * - Navigates to /#/tables
 * - Waits for key UI parts (title/toolbar/tabs)
 * - Captures console errors and a screenshot
 */
import { chromium } from 'playwright'
import fs from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const BASE_URL = process.env.BASE_URL || 'http://127.0.0.1:3000'
const TARGET_URL = `${BASE_URL}/#/tables`

const outDirUrl = new URL('../../tmp/', import.meta.url)
const outDir = fileURLToPath(outDirUrl)
try { await fs.mkdir(outDir, { recursive: true }) } catch {}

const errors = []
const logs = []

const browser = await chromium.launch({ headless: true })
const context = await browser.newContext()
context.addInitScript(() => {
  try { localStorage.setItem('selectedCluster', '1') } catch {}
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
  await page.goto(TARGET_URL + (process.env.CLUSTER_ID ? `?cluster=${process.env.CLUSTER_ID}` : ''))

  // Title
  result.steps.push('wait title')
  await page.getByText('表管理').first().waitFor({ state: 'visible', timeout: 15000 })

  // Toolbar essentials
  result.steps.push('wait toolbar search')
  await page.getByPlaceholder('搜索表名...').waitFor({ state: 'visible' })
  result.steps.push('wait scan button')
  await page.getByRole('button', { name: '扫描' }).waitFor({ state: 'visible' })

  // Tabs
  result.steps.push('wait tabs')
  await page.getByRole('tab', { name: '小文件/合并' }).waitFor({ state: 'visible' })
  await page.getByRole('tab', { name: '归档' }).waitFor({ state: 'visible' })

  // Switch to Archive tab and wait for table header
  result.steps.push('switch to archive tab')
  await page.getByRole('tab', { name: '归档' }).click()
  await page.getByText('归档状态').first().waitFor({ state: 'visible', timeout: 10000 }).catch(() => {})

  // Screenshot
  const shotPath = fileURLToPath(new URL('tables-page.png', outDirUrl))
  await page.screenshot({ path: shotPath, fullPage: false })
  result.screenshot = shotPath
  result.ok = true
} catch (e) {
  result.errors.push(String(e?.message || e))
} finally {
  result.errors.push(...errors)
  await browser.close().catch(() => {})
  // Write a simple json artifact
  const jsonPath = fileURLToPath(new URL('tables-check.json', outDirUrl))
  await fs.writeFile(jsonPath, JSON.stringify({ ...result, logs }, null, 2))
  console.log(`[tables-check] ok=${result.ok} screenshot=${result.screenshot || '-'} errors=${result.errors.length}`)
  if (result.errors.length) {
    console.log(result.errors.join('\n'))
  }
}
