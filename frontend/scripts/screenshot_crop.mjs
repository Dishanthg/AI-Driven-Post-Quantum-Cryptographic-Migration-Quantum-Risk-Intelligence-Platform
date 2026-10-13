// Retakes the list-heavy pages as clean viewport-only (not full-page)
// screenshots for the README - the first full-page capture pass produced
// technically-correct but unusably tall images (e.g. 07_recommendations.png
// was 1440x39204px for a 42-row real recommendation list). Same real running
// app, same real data, just a saner crop for a README gallery.
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const outDir = path.resolve(__dirname, '..', '..', 'docs', 'screenshots')
mkdirSync(outDir, { recursive: true })

const BASE = 'http://localhost:5173'

async function shot(page, name) {
  await page.waitForTimeout(400)
  await page.screenshot({ path: path.join(outDir, name), fullPage: false })
  console.log('wrote (viewport-only)', name)
}

async function main() {
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

  await page.goto(BASE + '/login', { waitUntil: 'networkidle' })
  await page.fill('label:has-text("Username") input', 'admin')
  await page.fill('label:has-text("Password") input', 'Demo1234!')
  await page.click('button:has-text("Sign in")')
  await page.waitForURL(BASE + '/', { timeout: 10000 })
  await page.waitForTimeout(600)

  await page.goto(BASE + '/risk', { waitUntil: 'networkidle' })
  await shot(page, '06_risk.png')

  await page.goto(BASE + '/recommendations', { waitUntil: 'networkidle' })
  await shot(page, '07_recommendations.png')

  await page.goto(BASE + '/migrations', { waitUntil: 'networkidle' })
  await page.waitForSelector('table.data-table tbody tr', { timeout: 10000 })
  await shot(page, '08_migrations.png')

  const detailsLink = page.locator('table.data-table tbody tr a', { hasText: 'Details' }).first()
  await detailsLink.click()
  await page.waitForURL(/\/migrations\/.+/, { timeout: 10000 })
  await shot(page, '09_migration_detail.png')

  await page.goto(BASE + '/benchmarks', { waitUntil: 'networkidle' })
  const providerInput = page.locator('input.text-input[placeholder*="rsa2048"]')
  if (await providerInput.count()) {
    await providerInput.fill('ml_kem_768')
    await page.click('button:has-text("Run")')
    await page.waitForTimeout(3000)
  }
  await shot(page, '10_benchmarks.png')

  await page.goto(BASE + '/models', { waitUntil: 'networkidle' })
  await shot(page, '13_models.png')

  await browser.close()
  console.log('done')
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
