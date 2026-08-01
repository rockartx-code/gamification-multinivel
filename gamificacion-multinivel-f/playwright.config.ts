import { defineConfig, devices } from '@playwright/test';

// Modos de ejecución:
// - Por defecto: solo pruebas mockeadas (interceptan el API; deterministas, sin datos en AWS).
// - E2E_LIVE=1 npx playwright test --grep @live : smoke tests contra el API dev real (microlambdas).
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  retries: process.env['CI'] ? 2 : 0,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'e2e-report' }]],
  grepInvert: process.env['E2E_LIVE'] ? undefined : /@live/,
  use: {
    // Puerto dedicado 4300: el 4200 suele estar ocupado por otras apps en este equipo.
    baseURL: 'http://localhost:4300',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure'
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'npm start -- --port 4300',
    url: 'http://localhost:4300',
    reuseExistingServer: !process.env['CI'],
    timeout: 180_000
  }
});
