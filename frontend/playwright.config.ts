import { defineConfig, devices } from "@playwright/test";

const backendCmd =
  "cd ../backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: 1,
  workers: 1,
  reporter: [["html"], ["list"]],
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: backendCmd,
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: true,
      timeout: 120_000,
      cwd: __dirname,
    },
    {
      command: "npm run dev",
      url: "http://localhost:3000",
      reuseExistingServer: true,
      timeout: 90_000,
    },
  ],
});
