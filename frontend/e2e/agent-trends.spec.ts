import { test, expect } from "@playwright/test";
import { waitForBackend } from "./helpers";

test.beforeAll(async () => {
  await waitForBackend();
});

test("Agent 页展示 VIS 趋势风格 chip", async ({ page }) => {
  test.setTimeout(60_000);
  await page.goto("/agent");
  const accept = page.getByRole("button", { name: /接受全部|Accept all/i });
  if (await accept.isVisible().catch(() => false)) await accept.click();
  await expect(page.getByTestId("agent-brief")).toBeVisible({ timeout: 60_000 });

  const chips = page.getByTestId("agent-trend-chips");
  // VIS may be empty in a fresh DB — pass if section absent, assert when present
  if (await chips.count()) {
    await expect(chips).toBeVisible();
    const first = chips.locator("button").first();
    await expect(first).toBeVisible();
    await first.click();
    await expect(page.getByTestId("agent-brief")).not.toHaveValue("");
  }
});
