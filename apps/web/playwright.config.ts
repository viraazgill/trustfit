import fs from "node:fs";
import path from "node:path";
import { defineConfig } from "@playwright/test";

// Seed-user credentials and ports come from the repo's .env (never committed).
const envFile = path.resolve(__dirname, "../../.env");
if (fs.existsSync(envFile)) process.loadEnvFile(envFile);

const python = path.resolve(__dirname, "../../.venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const WEB_URL = process.env.E2E_BASE_URL ?? "http://localhost:3000";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: WEB_URL, viewport: { width: 1360, height: 900 }, trace: "retain-on-failure" },
  // Against a deployed URL (E2E_BASE_URL) nothing is started locally.
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : [
        {
          command: `"${python}" -m uvicorn app.main:app --port 8000`,
          cwd: path.resolve(__dirname, "../api"),
          url: "http://localhost:8000/api/v1/health",
          reuseExistingServer: true,
          timeout: 60_000,
        },
        { command: "npm run dev", url: WEB_URL, reuseExistingServer: true, timeout: 120_000 },
      ],
});
