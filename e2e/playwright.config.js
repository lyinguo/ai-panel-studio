import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 60000,
  retries: 1,
  use: {
    baseURL: "http://localhost:5173",
    headless: true,
  },
  webServer: [
    {
      command:
        "D:\\anaconda\\envs\\ai-panel-studio\\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000",
      cwd: "../backend",
      port: 8000,
      reuseExistingServer: true,
      timeout: 30000,
    },
    {
      command: "npx vite --port 5173 --host 0.0.0.0",
      cwd: "../frontend",
      port: 5173,
      reuseExistingServer: true,
      timeout: 30000,
    },
  ],
});
