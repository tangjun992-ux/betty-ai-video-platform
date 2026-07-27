import { test, expect, type Page } from "@playwright/test";

const PROMPT = "一只红色的熊猫在竹林中漫步，电影级画质，柔和自然光，正面推进镜头";

async function dismissOverlays(page: Page) {
  await page.evaluate(() => {
    try {
      localStorage.setItem("betty-theme", "dark");
      localStorage.setItem("betty-cookie-consent", JSON.stringify({ value: "all", at: Date.now() }));
      localStorage.setItem("betty-demo-dismissed", "1");
    } catch {}
  });
}

async function gotoAndSettle(page: Page, path: string) {
  await page.goto(path, { waitUntil: "networkidle" });
  await dismissOverlays(page);
  await page.reload({ waitUntil: "networkidle" });
}

test.describe("create video real end-to-end smoke", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("home → create/video → submit → backend responds → polling starts", async ({ page }) => {
    // 1. Home: select video mode and fill prompt
    await gotoAndSettle(page, "http://localhost:3000/");
    await page.getByRole("button", { name: "视频", exact: true }).click();
    await page.locator("textarea").first().fill(PROMPT);

    // 2. Click home CTA and verify navigation with prompt param
    const navigatePromise = page.waitForURL(/\/create\/video\?prompt=/, { timeout: 10_000 });
    await page.getByRole("button", { name: "开始创作" }).click();
    await navigatePromise;
    await expect(page).toHaveURL(/\/create\/video\?prompt=/);

    // 3. On /create/video: prompt should be prefilled
    await gotoAndSettle(page, page.url());
    const promptTextarea = page.locator("textarea").first();
    await expect(promptTextarea).toHaveValue(PROMPT);

    // 4. Intercept the generate POST and first task status poll
    const generateResponsePromise = page.waitForResponse(
      (r) => r.url().includes("/api/v1/generate/") && r.request().method() === "POST",
      { timeout: 10_000 }
    );

    // 5. Click generate video
    await page.getByRole("button", { name: /生成视频/ }).click();

    // 6. Verify backend accepted the request and returned a task_id
    const generateResponse = await generateResponsePromise;
    expect(generateResponse.ok(), "generate/ API should return 2xx").toBeTruthy();
    const generateBody = await generateResponse.json();
    expect(generateBody.task_id, "response should contain task_id").toBeTruthy();
    expect(generateBody.task_id).toMatch(/^[a-zA-Z0-9_-]+$/);
    expect(generateBody.estimated_model, "response should include estimated_model").toBeTruthy();
    expect(typeof generateBody.estimated_cost_credits).toBe("number");

    // 7. Verify UI enters submitting state (progress card + task ID + loading text)
    await expect(page.getByText(/AI 正在生成视频/)).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/任务 ID/)).toBeVisible();
    await expect(page.getByText(/视频生成 1-5 分钟/)).toBeVisible();

    // 8. Verify frontend actually polls task status (real integration checkpoint)
    const statusResponsePromise = page.waitForResponse(
      (r) => r.url().includes(`/api/v1/tasks/${generateBody.task_id}`),
      { timeout: 15_000 }
    );
    const statusResponse = await statusResponsePromise;
    expect(statusResponse.ok(), "tasks/{id} status endpoint should return 2xx").toBeTruthy();
    const statusBody = await statusResponse.json();
    expect(statusBody.status, "task status should be a known state").toMatch(
      /queued|running|generating|uploading|processing|completed|failed|pending/
    );

    // 9. Final screenshot for human verification
    await page.screenshot({ path: "test-results/create-video-smoke.png" });
  });
});
