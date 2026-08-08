import { test, expect } from "@playwright/test";
import { waitForBackend } from "./helpers";

test.beforeAll(async () => {
  await waitForBackend();
});

test.describe("Billing 成功页", () => {
  test("支付成功页加载（含 session_id 参数）", async ({ page }) => {
    await page.goto("/billing/success?session_id=cs_test_e2e_demo");

    const accept = page.getByRole("button", { name: /接受全部|Accept all/i });
    if (await accept.isVisible().catch(() => false)) await accept.click();

    await expect(page.getByText(/支付成功|Payment successful/i).first()).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole("link", { name: /开始创作|Create/i }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: /查看账单|Billing/i }).first()).toBeVisible();
  });
});
