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

test.describe("Prompt Extractor", () => {
  test("YouTube 页面 → 提取 + URL-to-Viral 结构", async ({ page }) => {
    test.setTimeout(90_000);
    await page.goto("/create/extract");
    const accept = page.getByRole("button", { name: /接受全部|Accept all/i });
    if (await accept.isVisible().catch(() => false)) await accept.click();

    await expect(page.getByTestId("extract-page")).toBeVisible({ timeout: 30_000 });
    await page.getByPlaceholder(/YouTube|直链/).fill("https://www.youtube.com/watch?v=dQw4w9WgXcQ");
    await page.getByRole("button", { name: /提取提示词/ }).click();

    await expect(page.getByTestId("extract-result")).toBeVisible({ timeout: 45_000 });
    await expect(page.getByTestId("extract-viral-structure")).toBeVisible();
    await expect(page.getByTestId("extract-agent-link")).toBeVisible();
    await expect(page.getByText(/钩子|CTA/).first()).toBeVisible();
  });
});
