import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const outDir = path.resolve(__dirname, '..', '..', 'docs', 'screenshots')
mkdirSync(outDir, { recursive: true })

const BASE = 'http://localhost:5173'

async function shot(page, name) {
  await waitForChartsSettled(page)
  await page.screenshot({ path: path.join(outDir, name), fullPage: true })
  console.log('wrote', name)
}

// Recharts animates chart geometry in on mount (grow-from-zero), and headless
// Chromium's rAF/paint scheduling can be inconsistent about when that
// animation actually settles - screenshotting too early (or, paradoxically,
// after an intervening navigation/resize invalidates the settled state)
// can catch bars/pie slices mid-collapse. Force a resize (recharts'
// ResponsiveContainer recomputes on resize) and then poll for real painted
// geometry (nonzero rendered height/radius) before treating a chart as ready.
async function waitForChartsSettled(page, { timeoutMs = 8000 } = {}) {
  await page.evaluate(() => window.dispatchEvent(new Event('resize')))
  await page.waitForTimeout(150)
  try {
    await page.waitForFunction(
      () => {
        const bars = Array.from(document.querySelectorAll('.recharts-bar-rectangle path, .recharts-rectangle'))
        const pies = Array.from(document.querySelectorAll('.recharts-pie-sector path'))
        const shapes = [...bars, ...pies]
        if (shapes.length === 0) return true // page has no charts at all - nothing to wait for
        return shapes.some((el) => {
          const box = el.getBBox ? el.getBBox() : { width: 0, height: 0 }
          return box.width > 1 && box.height > 1
        })
      },
      { timeout: timeoutMs },
    )
  } catch {
    // fall through - screenshot whatever state we have rather than hang the whole run
  }
  await page.waitForTimeout(300)
}

async function main() {
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

  // 1. Login page (logged out)
  await page.goto(BASE + '/login', { waitUntil: 'networkidle' })
  await page.waitForTimeout(400)
  await shot(page, '01_login.png')

  // Log in for real via the form
  await page.fill('label:has-text("Username") input', 'admin')
  await page.fill('label:has-text("Password") input', 'Demo1234!')
  await page.click('button:has-text("Sign in")')
  await page.waitForURL(BASE + '/', { timeout: 10000 })
  await page.waitForTimeout(800)

  // 2. Executive Overview
  await shot(page, '02_overview.png')

  // 3. Cryptographic Inventory
  await page.goto(BASE + '/inventory', { waitUntil: 'networkidle' })
  await page.waitForSelector('table.data-table tbody tr', { timeout: 10000 })
  await page.waitForTimeout(300)
  await shot(page, '03_inventory.png')

  // 4. Asset detail (click first row link)
  const firstAssetLink = page.locator('table.data-table tbody tr td a').first()
  await firstAssetLink.click()
  await page.waitForURL(/\/inventory\/.+/, { timeout: 10000 })
  await page.waitForTimeout(500)
  await shot(page, '04_asset_detail.png')

  // 5. Algorithm Explorer
  await page.goto(BASE + '/algorithms', { waitUntil: 'networkidle' })
  await page.waitForTimeout(600)
  await shot(page, '05_algorithms.png')

  // 6. Quantum Risk / AI Explanation
  await page.goto(BASE + '/risk', { waitUntil: 'networkidle' })
  await page.waitForTimeout(600)
  await shot(page, '06_risk.png')

  // 7. PQC Recommendations
  await page.goto(BASE + '/recommendations', { waitUntil: 'networkidle' })
  await page.waitForTimeout(600)
  await shot(page, '07_recommendations.png')

  // 8. Migration Planner
  await page.goto(BASE + '/migrations', { waitUntil: 'networkidle' })
  await page.waitForSelector('table.data-table tbody tr', { timeout: 10000 })
  await page.waitForTimeout(300)
  await shot(page, '08_migrations.png')

  // 9. Migration plan detail
  const detailsLink = page.locator('table.data-table tbody tr a', { hasText: 'Details' }).first()
  await detailsLink.click()
  await page.waitForURL(/\/migrations\/.+/, { timeout: 10000 })
  await page.waitForTimeout(500)
  await shot(page, '09_migration_detail.png')

  // 10. Benchmark Lab - trigger a real run then screenshot
  await page.goto(BASE + '/benchmarks', { waitUntil: 'networkidle' })
  await page.waitForTimeout(500)
  const providerInput = page.locator('input.text-input[placeholder*="rsa2048"]')
  if (await providerInput.count()) {
    await providerInput.fill('ecdsa_p256')
    await page.click('button:has-text("Run")')
    await page.waitForTimeout(3000)
  }
  await shot(page, '10_benchmarks.png')

  // 11. Quantum Algorithm Lab - run Grover for real
  await page.goto(BASE + '/quantum-lab', { waitUntil: 'networkidle' })
  await page.waitForTimeout(500)
  const groverBtn = page.locator('button:has-text("Run Grover search")')
  if (await groverBtn.count()) {
    await groverBtn.click()
    await page.waitForSelector('text=Success probability', { timeout: 15000 })
    await page.waitForTimeout(500)
  }
  await shot(page, '11_quantum_lab.png')

  // 12. Crypto Agility Demo
  await page.goto(BASE + '/agility', { waitUntil: 'networkidle' })
  await page.waitForTimeout(400)
  await shot(page, '12_agility.png')

  // 13. Model Registry
  await page.goto(BASE + '/models', { waitUntil: 'networkidle' })
  await page.waitForTimeout(400)
  await shot(page, '13_models.png')

  // 14. Audit Logs (admin only)
  await page.goto(BASE + '/audit', { waitUntil: 'networkidle' })
  await page.waitForTimeout(500)
  await shot(page, '14_audit.png')

  // 15. System Health
  await page.goto(BASE + '/health', { waitUntil: 'networkidle' })
  await page.waitForTimeout(500)
  await shot(page, '15_health.png')

  await browser.close()
  console.log('done')
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
