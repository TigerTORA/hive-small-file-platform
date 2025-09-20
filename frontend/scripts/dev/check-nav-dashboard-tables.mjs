#!/usr/bin/env node
import { chromium } from 'playwright'
import fs from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const BASE_URL = process.env.BASE_URL || 'http://127.0.0.1:3000'
const outDirUrl = new URL('../../tmp/', import.meta.url)
const outDir = fileURLToPath(outDirUrl)
try { await fs.mkdir(outDir, { recursive: true }) } catch {}

const errors = []
const logs = []
const result = { ok: false, steps: [], errors: [], shots: {} }

const browser = await chromium.launch({ headless: true })
const ctx = await browser.newContext()
await ctx.addInitScript(() => { try { localStorage.setItem('selectedCluster','1') } catch {} })
const page = await ctx.newPage()
page.on('console', m => { const t=m.type(),x=m.text(); if(t==='error') errors.push(x); logs.push(`[${t}] ${x}`) })

try {
  // Dashboard
  result.steps.push('goto dashboard')
  await page.goto(`${BASE_URL}/#/`)
  await page.getByText('监控中心').first().waitFor({ state: 'visible', timeout: 15000 })
  await page.locator('.overview-stats').first().waitFor({ state: 'visible', timeout: 15000 })
  const shot1 = fileURLToPath(new URL('nav-1-dashboard.png', outDirUrl))
  await page.screenshot({ path: shot1 })
  result.shots.dashboard1 = shot1

  // Tables
  result.steps.push('goto tables')
  await page.goto(`${BASE_URL}/#/tables`)
  await page.getByText('表管理').first().waitFor({ state: 'visible', timeout: 15000 })
  await page.locator('.el-tabs').first().waitFor({ state: 'visible', timeout: 15000 })
  const shot2 = fileURLToPath(new URL('nav-2-tables.png', outDirUrl))
  await page.screenshot({ path: shot2 })
  result.shots.tables = shot2

  // Back to Dashboard
  result.steps.push('back to dashboard')
  await page.goto(`${BASE_URL}/#/`)
  await page.getByText('监控中心').first().waitFor({ state: 'visible', timeout: 15000 })
  await page.locator('.overview-stats').first().waitFor({ state: 'visible', timeout: 15000 })
  const shot3 = fileURLToPath(new URL('nav-3-dashboard.png', outDirUrl))
  await page.screenshot({ path: shot3 })
  result.shots.dashboard2 = shot3

  result.ok = true
} catch (e) {
  result.errors.push(String(e?.message || e))
} finally {
  result.errors.push(...errors)
  await browser.close().catch(()=>{})
  const jsonPath = fileURLToPath(new URL('nav-check.json', outDirUrl))
  await fs.writeFile(jsonPath, JSON.stringify({ ...result, logs }, null, 2))
  console.log(`[nav-check] ok=${result.ok} shots=${Object.keys(result.shots).length} errors=${result.errors.length}`)
  if (result.errors.length) console.log(result.errors.join('\n'))
}

