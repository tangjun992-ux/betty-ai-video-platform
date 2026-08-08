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
  test("输入创意 → 创意变体 → 分镜 DAG + 积分披露", async ({ page }) => {
    test.setTimeout(90_000);

    await page.goto("/agent");

    const accept = page.getByRole("button", { name: /接受全部|Accept all/i });
    if (await accept.isVisible().catch(() => false)) await accept.click();

    const brief = page.getByTestId("agent-brief");
    await expect(brief).toBeVisible({ timeout: 30_000 });

    const idea = "做一个15秒的咖啡产品宣传片，电影级画质，竖屏抖音";
    await expect(async () => {
      await brief.fill(idea);
      await expect(brief).toHaveValue(idea, { timeout: 1000 });
    }).toPass({ timeout: 20_000 });

    // Phase 7+ uses one-click as primary CTA; plan-only path is via 创意变体 fan-out.
    const variantsBtn = page.getByTestId("agent-variants-btn");
    await expect(variantsBtn).toBeEnabled({ timeout: 10_000 });
    await variantsBtn.click();

    const cards = page.getByTestId("agent-variant-cards");
    await expect(cards).toBeVisible({ timeout: 45_000 });
    await expect(cards.locator("button").first()).toBeVisible({ timeout: 45_000 });

    // Total credits summary (Phase 10 UX)
    await expect(page.getByTestId("agent-variant-total-credits")).toBeVisible();

    await expect(page.getByTestId("agent-variant-compare-table")).toBeVisible();
    await expect(page.getByText(/钩子|CTA|Seed/).first()).toBeVisible();

    // Adopt first variant → planned DAG
    await cards.locator("button").first().click();

    await expect(page.getByTestId("agent-plan")).toBeVisible({ timeout: 15_000 });
    const steps = page.getByTestId("agent-step");
    await expect(steps.first()).toBeVisible({ timeout: 15_000 });
    expect(await steps.count()).toBeGreaterThan(0);

    await expect(page.getByText(/积分/).first()).toBeVisible();
  });

  test("一键成片按钮在填写 brief 后可用", async ({ page }) => {
    test.setTimeout(60_000);
    await page.goto("/agent");
    const accept = page.getByRole("button", { name: /接受全部|Accept all/i });
    if (await accept.isVisible().catch(() => false)) await accept.click();

    const brief = page.getByTestId("agent-brief");
    await expect(brief).toBeVisible({ timeout: 30_000 });
    await brief.fill("5秒产品特写短片");
    const oneclick = page.getByTestId("agent-oneclick-btn");
    await expect(oneclick).toBeEnabled({ timeout: 10_000 });
  });
});
