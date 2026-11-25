import { defineConfig } from '@playwright/test'
import { randomBytes } from 'node:crypto'
import { apiPort, webOrigin, webPort } from './e2e/environment.ts'

process.env.E2E_RUN_ID ??= randomBytes(8).toString('hex')
process.env.E2E_PASSWORD ??= `Test1!${randomBytes(24).toString('hex')}`
process.env.E2E_SIGNING_KEY ??= randomBytes(32).toString('hex')

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 45000,
  expect: { timeout: 10000 },
  reporter: [['list']],
  use: {
    baseURL: webOrigin,
    headless: true,
    channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
    screenshot: 'off',
    trace: 'off',
    video: 'off',
  },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1280, height: 900 } } },
    { name: 'mobile', use: { viewport: { width: 360, height: 900 } } },
  ],
  webServer: [
    {
      command: 'node e2e/start-api.mjs',
      url: `http://127.0.0.1:${apiPort}/health/ready`,
      reuseExistingServer: false,
      timeout: 60000,
    },
    {
      command:
        process.env.E2E_BUILT_FRONTEND === '1'
          ? `npm run preview -- --port ${webPort} --strictPort`
          : 'npm run dev',
      url: webOrigin,
      reuseExistingServer: false,
      timeout: 30000,
    },
  ],
})
