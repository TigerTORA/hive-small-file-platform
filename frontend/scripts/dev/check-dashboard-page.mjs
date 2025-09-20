#!/usr/bin/env node
import { chromium } from 'playwright'
import fs from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const BASE_URL = process.env.BASE_URL || 'http://127.0.0.1:3000'
const TARGET_URL = `${BASE_URL}/#/`

const outDirUrl = new URL('../../tmp/', import.meta.url)
const outDir = fileURLToPath(outDirUrl)
try { await fs.mkdir(outDir, { recursive: true }) } catch {}

const errors = []
const logs = []

const browser = await chromium.launch({ headless: true })
const context = await browser.newContext()
context.addInitScript(() => { try { localStorage.setItem('selectedCluster', '1') } catch {} })
const page = await context.newPage()

page.on('console', msg => {
  const type = msg.type(); const text = msg.text();
  if (type === 'error') errors.push(text)
  logs.push(`[${type}] ${text}`)
})

const result = { ok: false, steps: [], errors: [], screenshot: null }

try {
  result.steps.push(`goto ${TARGET_URL}`)
  await page.goto(TARGET_URL)
  result.steps.push('wait page title visible')
  await page.getByText('监控中心').first().waitFor({ state: 'visible', timeout: 15000 })
  result.steps.push('wait overview grid visible')
  await page.locator('.overview-stats').first().waitFor({ state: 'visible', timeout: 15000 })
  const shotPath = fileURLToPath(new URL('dashboard-page.png', outDirUrl))
  await page.screenshot({ path: shotPath })
  result.screenshot = shotPath
  result.ok = true
} catch (e) {
  result.errors.push(String(e?.message || e))
} finally {
  result.errors.push(...errors)
  await browser.close().catch(() => {})
  const jsonPath = fileURLToPath(new URL('dashboard-check.json', outDirUrl))
  await fs.writeFile(jsonPath, JSON.stringify({ ...result, logs }, null, 2))
  console.log(`[dashboard-check] ok=${result.ok} screenshot=${result.screenshot || '-'} errors=${result.errors.length}`)
  if (result.errors.length) console.log(result.errors.join('\n'))
}

