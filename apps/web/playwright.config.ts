import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests/e2e",
  use: { baseURL: "http://127.0.0.1:3000", browserName: "chromium" },
  webServer: { command: "npm run dev", url: "http://127.0.0.1:3000", reuseExistingServer: false, timeout: 120_000 },
});
