import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: 'http://localhost:3006',
    headless: true,
    screenshot: 'only-on-failure',
  },
  retries: 0,
});
