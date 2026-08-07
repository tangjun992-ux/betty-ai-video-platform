import { test, expect } from "@playwright/test";
import {
  E2E_GUEST_ID,
  seedCompletedImageTask,
  submitImageTask,
  waitForBackend,
} from "./helpers";

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

test.describe("任务详情页", () => {
  test("已完成任务 → 详情页展示结果", async ({ page, request }) => {
    test.setTimeout(90_000);
    const taskId = await seedCompletedImageTask(request, E2E_GUEST_ID);

    await page.goto(`/tasks/${taskId}`);
    const accept = page.getByRole("button", { name: /接受全部|Accept all/i });
    if (await accept.isVisible().catch(() => false)) await accept.click();

    await expect(page.getByTestId("task-detail-page")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(/已完成|completed/i).first()).toBeVisible({ timeout: 15_000 });
  });

  test("进行中任务 → WebSocket/轮询进度指示", async ({ page, request }) => {
    test.setTimeout(60_000);
    const taskId = await submitImageTask(request, E2E_GUEST_ID);

    await page.goto(`/tasks/${taskId}`);
    const accept = page.getByRole("button", { name: /接受全部|Accept all/i });
    if (await accept.isVisible().catch(() => false)) await accept.click();

    await expect(page.getByTestId("task-detail-page")).toBeVisible({ timeout: 30_000 });
    const live = page.getByTestId("task-live-source");
    await expect(live).toBeVisible({ timeout: 15_000 });
    await expect(live).toContainText(/WebSocket|轮询/);
  });
});
