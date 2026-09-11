import { defineConfig, devices } from '@playwright/test'

/**
 * End-to-end tests run against the real backend and a real database, because
 * the rule under test — "no store means every store" — lives in SQL. A mocked
 * API would only prove the mock agrees with itself.
 *
 * Start the stack first:  make up   (or: make db-reset && make run)
 */
const BASE_URL = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5173'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  reporter: process.env.CI ? 'line' : 'list',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'phone',
      // The list is used on a phone, walking around a shop.
      use: { ...devices['Pixel 7'] },
    },
  ],
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : {
        // Test the production build, not the dev server: the manifest and
        // service worker are generated at build time and are part of the
        // installability requirement.
        command: 'npm run build && npm run preview -- --port 5173 --strictPort',
        url: BASE_URL,
        reuseExistingServer: true,
        timeout: 120_000,
      },
})
