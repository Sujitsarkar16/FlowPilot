import { expect, test } from "@playwright/test";

test("unauthenticated dashboard requests redirect to login", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login\?error=auth_not_configured/);
  await expect(page.getByRole("heading", { name: "Sign in to your workspace" })).toBeVisible();
});
