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

test.describe("Director Agent 黄金路径", () => {
  test("输入创意 → 规划出分镜 DAG", async ({ page }) => {
    test.setTimeout(90_000);

    await page.goto("/agent");

    // Dismiss cookie consent so it cannot intercept input.
    const accept = page.getByRole("button", { name: /接受全部|Accept all/i });
    if (await accept.isVisible().catch(() => false)) await accept.click();

    const brief = page.getByTestId("agent-brief");
    await expect(brief).toBeVisible({ timeout: 30_000 });

    const idea = "做一个15秒的咖啡产品宣传片，电影级画质，竖屏抖音";
    // Refill until the value sticks (guards against React hydration resetting a
    // too-early fill), then plan via the built-in Ctrl+Enter shortcut.
    await expect(async () => {
      await brief.fill(idea);
      await expect(brief).toHaveValue(idea, { timeout: 1000 });
    }).toPass({ timeout: 20_000 });

    const planBtn = page.getByTestId("agent-plan-btn");
    await expect(planBtn).toBeEnabled({ timeout: 10_000 });
    await planBtn.click();

    // Director returns a real multi-step plan (works in demo/dry-run without keys)
    await expect(page.getByTestId("agent-plan")).toBeVisible({ timeout: 45_000 });
    const steps = page.getByTestId("agent-step");
    await expect(steps.first()).toBeVisible({ timeout: 45_000 });
    expect(await steps.count()).toBeGreaterThan(0);

    // Plan summary + credit estimate are shown (trust: cost is disclosed upfront)
    await expect(page.getByText(/积分/).first()).toBeVisible();
  });
});
