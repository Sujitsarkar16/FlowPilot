import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  testMatch: "**/*.spec.ts",
  use: {
    baseURL: "http://127.0.0.1:3001",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "npm run dev -- --port 3001",
    url: "http://127.0.0.1:3001",
    reuseExistingServer: false,
    env: {
      NEXT_PUBLIC_API_URL: "http://127.0.0.1:3001",
      // Placeholder Auth0 config so the client constructs; e2e uses the x-flowpilot-e2e bypass.
      APP_BASE_URL: "http://127.0.0.1:3001",
      AUTH0_DOMAIN: "example.us.auth0.com",
      AUTH0_CLIENT_ID: "test-client-id",
      AUTH0_CLIENT_SECRET: "test-client-secret",
      AUTH0_SECRET: "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      AUTH0_AUDIENCE: "https://flowpilot-api",
    },
  },
});
