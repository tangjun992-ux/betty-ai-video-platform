import { test, expect } from "@playwright/test";
import { E2E_GUEST_ID, seedTimelineVideos, waitForBackend } from "./helpers";

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  await waitForBackend();
  await seedTimelineVideos(request);
});

test.describe("时间线全链路", () => {
  test.beforeEach(async ({ page, request }) => {
    await page.addInitScript((gid) => {
      localStorage.removeItem("auth-store");
      localStorage.setItem("betty-guest-id", gid);
      document.cookie = `betty_guest_id=${encodeURIComponent(gid)};path=/;max-age=31536000;SameSite=Lax`;
    }, E2E_GUEST_ID);
    await seedTimelineVideos(request);
  });

  test("项目保存 → 深链恢复 → 字幕合成", async ({ page }) => {
    test.setTimeout(180_000);

    await page.goto("/create/timeline");
    const accept = page.getByRole("button", { name: /接受全部|Accept all/i });
    if (await accept.isVisible().catch(() => false)) await accept.click();
    await expect(page.getByTestId("timeline-page")).toBeVisible({ timeout: 30_000 });

    const libraryItems = page.getByTestId("timeline-library-item");
    await expect(page.getByTestId("timeline-library-grid")).toBeVisible({ timeout: 60_000 });
    await expect(libraryItems.first()).toBeVisible({ timeout: 30_000 });

    await libraryItems.nth(0).click();
    await libraryItems.nth(1).click();
    await expect(page.getByTestId("timeline-clip")).toHaveCount(2);

    const projectName = `E2E时间线 ${Date.now()}`;
    await page.getByTestId("timeline-project-name").fill(projectName);
    await page.getByTestId("timeline-subtitle-input").fill("E2E全链路字幕烧录");
    await expect(page.getByTestId("timeline-subtitle-preview")).toContainText("E2E全链路字幕烧录");

    await page.getByTestId("timeline-save-project").click();
    await expect(page).toHaveURL(/project=/, { timeout: 15_000 });

    const projectId = new URL(page.url()).searchParams.get("project");
    expect(projectId).toBeTruthy();

    // Deep-link reload should restore persisted clips + subtitle
    await page.goto(`/create/timeline?project=${projectId}`);
    await expect(page.getByTestId("timeline-clip")).toHaveCount(2, { timeout: 30_000 });
    await expect(page.getByText("加载项目…")).toHaveCount(0, { timeout: 30_000 });
    await expect(page.getByTestId("timeline-project-name")).toHaveValue(projectName);
    await expect(page.getByTestId("timeline-subtitle-input")).toHaveValue("E2E全链路字幕烧录");

    await page.getByTestId("timeline-compose").click();
    await expect(page.getByTestId("timeline-result-video")).toBeVisible({ timeout: 180_000 });

    const video = page.getByTestId("timeline-result-video");
    await expect(video).toHaveAttribute("src", /\/api\/v1\/media\//);
  });
});

test.describe("创作入口 smoke", () => {
  test("侧边栏可进入时间线", async ({ page }) => {
    await page.goto("/create/timeline");
    await expect(page).toHaveURL(/\/create\/timeline/);
    await expect(page.getByTestId("timeline-page")).toBeVisible();
  });
});
