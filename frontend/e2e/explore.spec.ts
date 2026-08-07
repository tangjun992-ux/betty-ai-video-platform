import { test, expect } from "@playwright/test";
import { E2E_GUEST_ID, waitForBackend } from "./helpers";

test.beforeAll(async () => {
  await waitForBackend();
});

test.beforeEach(async ({ page }) => {
  await page.addInitScript((gid) => {
    localStorage.removeItem("auth-store");
    localStorage.setItem("betty-guest-id", gid);
    document.cookie = `betty_guest_id=${encodeURIComponent(gid)};path=/;max-age=31536000;SameSite=Lax`;
  }, E2E_GUEST_ID);
});

test.describe("Explore 飞轮", () => {
  test("探索页展示 seed 内容网格", async ({ page }) => {
    test.setTimeout(90_000);
    await page.goto("/explore");
    const accept = page.getByRole("button", { name: /接受全部|Accept all/i });
    if (await accept.isVisible().catch(() => false)) await accept.click();

    // Gallery grid — dev seed runs on startup when empty
    const grid = page.getByTestId("gallery-grid");
    await expect(grid).toBeVisible({ timeout: 60_000 });
    const cards = page.getByTestId("gallery-item");
    await expect(cards.first()).toBeVisible({ timeout: 90_000 });
    expect(await cards.count()).toBeGreaterThan(0);
  });
});
