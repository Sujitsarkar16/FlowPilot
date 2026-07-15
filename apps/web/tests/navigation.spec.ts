import { expect, test } from "@playwright/test";

const dashboardRoutes = [
  "/dashboard",
  "/dashboard/events",
  "/dashboard/standing-orders",
  "/dashboard/approvals",
  "/dashboard/connections",
  "/dashboard/settings",
];

test("dashboard navigation routes remain protected without a session", async ({ page }) => {
  for (const route of dashboardRoutes) {
    await page.goto(route);
    await expect(page).toHaveURL(/\/login\?error=auth_not_configured/);
  }
});
