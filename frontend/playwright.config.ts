import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

/**
 * Full-stack E2E config: Playwright starts the real FastAPI app (deterministic
 * fake AI providers, an isolated migrated SQLite database) and the real
 * Next.js app, then drives both through a real Chromium browser.
 *
 * Ports are deliberately distinct from the normal dev ports (3000 / 8000) so
 * that `reuseExistingServer` (enabled outside CI, for fast local iteration)
 * can never accidentally attach to a developer's already-running dev server
 * — which would silently point tests at real OpenAI and the real dev
 * database instead of the fakes configured below.
 */
const FRONTEND_PORT = 3100;
const BACKEND_PORT = 8100;
const FRONTEND_URL = `http://127.0.0.1:${FRONTEND_PORT}`;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
const BACKEND_DIR = path.resolve(__dirname, "../backend");
// Always resolve the backend's own virtualenv interpreter rather than
// relying on `python3` on PATH, which may resolve to an unrelated system
// or conda Python with none of the backend's dependencies installed.
const BACKEND_PYTHON = path.resolve(BACKEND_DIR, ".venv", "bin", "python3");

const isCI = !!process.env.CI;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  forbidOnly: isCI,
  retries: isCI ? 1 : 0,
  reporter: isCI ? [["html", { open: "never" }], ["list"]] : "list",
  timeout: 45_000,
  expect: {
    timeout: 15_000,
  },
  use: {
    baseURL: FRONTEND_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 15_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command:
        `${BACKEND_PYTHON} scripts/prepare_e2e_db.py && ` +
        `${BACKEND_PYTHON} -m uvicorn app.main:app --host 127.0.0.1 --port ${BACKEND_PORT}`,
      cwd: BACKEND_DIR,
      url: `${BACKEND_URL}/api/v1/health`,
      timeout: 60_000,
      reuseExistingServer: !isCI,
      stdout: "pipe",
      stderr: "pipe",
      env: {
        APP_ENV: "test",
        E2E_FAKE_AI: "true",
        DATABASE_URL: "sqlite:///./data/e2e-test.db",
        CORS_ORIGINS: FRONTEND_URL,
      },
    },
    {
      command: `npm run dev -- -p ${FRONTEND_PORT}`,
      cwd: __dirname,
      url: FRONTEND_URL,
      timeout: 60_000,
      reuseExistingServer: !isCI,
      stdout: "pipe",
      stderr: "pipe",
      env: {
        NEXT_PUBLIC_API_BASE_URL: BACKEND_URL,
      },
    },
  ],
});
