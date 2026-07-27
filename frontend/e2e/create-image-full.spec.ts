import { test, expect, Page } from "@playwright/test";

const GUEST = "e2e-create-image-full-001";
const PIXEL_GIF =
  "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";
const PIXEL_PNG_BASE64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";

async function seedGuest(page: Page) {
  await page.addInitScript((gid) => {
    localStorage.removeItem("auth-store");
    localStorage.setItem("betty-guest-id", gid);
    document.cookie = `betty_guest_id=${encodeURIComponent(gid)};path=/;max-age=31536000;SameSite=Lax`;
  }, GUEST);
}

async function openPage(page: Page) {
  const modelsResp = page
    .waitForResponse((r) => r.url().includes("/api/v1/models/"), { timeout: 8000 })
    .catch(() => null);
  await page.goto("/create/image");
  const accept = page.getByRole("button", { name: /接受全部|Accept all/i });
  if (await accept.isVisible().catch(() => false)) await accept.click();
  await modelsResp;
  await expect(page.getByTestId("image-prompt-input")).toBeVisible();
}

async function selectOption(page: Page, testId: string, optionLabel: string) {
  await page.getByTestId(testId).click();
  await page
    .getByRole("button", { name: new RegExp(`^${optionLabel}$`) })
    .first()
    .click();
}

// dzine 统一参数面板：比例(形状按钮) / 尺寸 / 质量
async function selectAspect(page: Page, id: string) {
  await page.getByTestId("param-select").click();
  await page.locator(`button[title="${id}"]`).click();
  await page.keyboard.press("Escape");
}
async function selectSize(page: Page, s: string) {
  await page.getByTestId("param-select").click();
  await page.getByRole("button", { name: s, exact: true }).first().click();
  await page.keyboard.press("Escape");
}
async function selectQuality(page: Page, label: string) {
  await page.getByTestId("param-select").click();
  await page.getByRole("button", { name: label, exact: true }).first().click();
  await page.keyboard.press("Escape");
}

/** Mock /generate + /tasks + /upload so contract tests never consume credits. */
async function mockBackend(page: Page, captured: Array<Record<string, unknown>>) {
  await page.route("**/api/v1/generate/", async (route) => {
    const body = route.request().postDataJSON() as Record<string, unknown>;
    captured.push(body);
    const id = `mock-task-${captured.length}`;
    await route.fulfill({
      json: {
        task_id: id,
        status: "queued",
        estimated_model: "mock-model",
        estimated_time_seconds: 1,
        estimated_cost_credits: 1,
        poll_url: `/api/v1/tasks/${id}`,
      },
    });
  });
  await page.route("**/api/v1/tasks/mock-task-*", async (route) => {
    await route.fulfill({
      json: {
        task_id: "mock-task",
        status: "completed",
        results: [{ url: PIXEL_GIF, type: "image", model: "mock-model", seed: 123456 }],
        cost_credits: 1,
      },
    });
  });
  await page.route("**/api/v1/upload", async (route) => {
    await route.fulfill({ json: { url: "https://cdn.example.com/e2e-ref.png" } });
  });
}

test.describe("图像生成页 · UI 结构与交互", () => {
  test.beforeEach(async ({ page }) => {
    await seedGuest(page);
    await openPage(page);
  });

  test("页面结构完整：标题/Tab/工具栏/提交", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /提示词 · 编辑 · 合并专业图片/ })).toBeVisible();
    await expect(page.getByRole("button", { name: "Prompt", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "编辑", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "合并图像", exact: true })).toBeVisible();

    await expect(page.getByTestId("model-select")).toBeVisible();
    await expect(page.getByTestId("param-select")).toBeVisible();
    await expect(page.getByTestId("count-select")).toBeVisible();
    await expect(page.getByTestId("more-toggle")).toBeVisible();
    await expect(page.getByRole("button", { name: "添加参考图" }).first()).toBeVisible();

    await expect(page.getByTestId("image-submit")).toBeDisabled();
    await page.getByTestId("image-prompt-input").fill("test");
    await expect(page.getByTestId("image-submit")).toBeEnabled();
  });

  test("下拉一次点击开/关，支持外部点击与 Escape", async ({ page }) => {
    const modelBtn = page.getByTestId("model-select");
    await modelBtn.click();
    await expect(page.getByText("Model", { exact: true })).toBeVisible({ timeout: 10000 });
    await modelBtn.click();
    await expect(page.getByText("Model", { exact: true })).toHaveCount(0);

    await modelBtn.click();
    await expect(page.getByText("Model", { exact: true })).toBeVisible({ timeout: 10000 });
    await page.keyboard.press("Escape");
    await expect(page.getByText("Model", { exact: true })).toHaveCount(0);

    await page.getByTestId("param-select").click();
    await expect(page.locator('button[title="16:9"]')).toBeVisible();
    await page.mouse.click(10, 10);
    await expect(page.locator('button[title="16:9"]')).toHaveCount(0);
  });

  test("「更多」与参数并行，互不影响", async ({ page }) => {
    await page.getByTestId("more-toggle").click();
    await expect(page.getByText("风格").first()).toBeVisible({ timeout: 10000 });
    await page.getByTestId("param-select").click();
    await expect(page.locator('button[title="16:9"]')).toBeVisible();
    await page.keyboard.press("Escape");

    await page.getByTestId("more-toggle").click();
    await page.getByTestId("model-select").click();
    await expect(page.getByText("Model", { exact: true })).toBeVisible({ timeout: 10000 });
  });

  test("建议词填充 + Image Apps 可见", async ({ page }) => {
    await page.getByRole("button", { name: /赛博朋克城市夜景/ }).click();
    await expect(page.getByTestId("image-prompt-input")).toHaveValue(/赛博朋克/);
    await expect(page.getByText("Image Apps")).toBeVisible();
    await expect(page.getByRole("button", { name: /图片编辑器/ })).toBeVisible();
  });
});

test.describe("图像生成页 · 参数 → API 契约映射", () => {
  test.beforeEach(async ({ page }) => {
    await seedGuest(page);
  });

  test("比例映射到 resolution", async ({ page }) => {
    const captured: Array<Record<string, unknown>> = [];
    await mockBackend(page, captured);
    await openPage(page);
    await page.getByTestId("image-prompt-input").fill("contract test");

    const cases: Array<[string, string]> = [
      ["1:1", "2048x2048"],
      ["16:9", "2048x1152"],
      ["9:16", "1152x2048"],
      ["4:3", "2048x1536"],
      ["3:2", "2048x1368"],
    ];
    for (const [aspect, expected] of cases) {
      await selectAspect(page, aspect);
      await expect(page.getByTestId("image-submit")).toBeEnabled({ timeout: 10000 });
      await page.getByTestId("image-submit").click();
      await expect(page.getByTestId("image-submit")).toBeEnabled({ timeout: 10000 });
      expect(captured.length).toBeGreaterThan(0);
      expect(captured[captured.length - 1].resolution).toBe(expected);
      expect(captured[captured.length - 1].media_type).toBe("image");
    }
  });

  test("质量 / 数量 / 模型映射", async ({ page }) => {
    const captured: Array<Record<string, unknown>> = [];
    await mockBackend(page, captured);
    await openPage(page);
    await page.getByTestId("image-prompt-input").fill("contract test");

    await selectQuality(page, "高质量");
    await selectOption(page, "count-select", "4");
    await expect(page.getByTestId("image-submit")).toBeEnabled({ timeout: 10000 });
    await page.getByTestId("image-submit").click();
    await expect(page.getByTestId("image-submit")).toBeEnabled({ timeout: 10000 });
    let last = captured[captured.length - 1];
    expect(last.quality).toBe("high");
    expect(last.count).toBe(4);
    expect(last.model).toBe("auto");

    await page.getByTestId("model-select").click();
    await page.getByText("GPT Image 2").first().click();
    await expect(page.getByTestId("image-submit")).toBeEnabled({ timeout: 10000 });
    await page.getByTestId("image-submit").click();
    await expect(page.getByTestId("image-submit")).toBeEnabled({ timeout: 10000 });
    last = captured[captured.length - 1];
    expect(String(last.model)).toMatch(/gpt-image-2/);
  });

  test("参考图上传后进入 reference_images", async ({ page }) => {
    const captured: Array<Record<string, unknown>> = [];
    await mockBackend(page, captured);
    await openPage(page);
    await page.getByTestId("image-prompt-input").fill("with reference");

    await page.locator('input[type="file"]').setInputFiles({
      name: "ref.png",
      mimeType: "image/png",
      buffer: Buffer.from(PIXEL_PNG_BASE64, "base64"),
    });
    await expect(page.locator('img[alt="参考图"]')).toBeVisible();
    await expect(page.getByTestId("image-submit")).toBeEnabled({ timeout: 10000 });
    await page.getByTestId("image-submit").click();
    await expect(page.getByTestId("image-submit")).toBeEnabled({ timeout: 10000 });
    const last = captured[captured.length - 1];
    expect(Array.isArray(last.reference_images)).toBe(true);
    expect((last.reference_images as string[])[0]).toBe("https://cdn.example.com/e2e-ref.png");
    expect(last.image_url).toBe("https://cdn.example.com/e2e-ref.png");
  });
});

test.describe("图像生成页 · 编辑/合并 Tab（对标 Yapper）", () => {
  test.beforeEach(async ({ page }) => {
    await seedGuest(page);
  });

  test("编辑 Tab：需要 1 张参考图，提交走 i2i 且关闭提示词改写", async ({ page }) => {
    const captured: Array<Record<string, unknown>> = [];
    await mockBackend(page, captured);
    await openPage(page);

    await page.getByRole("button", { name: "编辑", exact: true }).click();
    await page.getByTestId("image-prompt-input").fill("把背景换成海边日落");
    await expect(page.getByTestId("image-submit")).toBeDisabled();

    await page.locator('input[type="file"]').setInputFiles({
      name: "ref.png",
      mimeType: "image/png",
      buffer: Buffer.from(PIXEL_PNG_BASE64, "base64"),
    });
    await expect(page.locator('img[alt="参考图"]')).toBeVisible();
    await expect(page.getByTestId("image-submit")).toBeEnabled({ timeout: 10000 });
    await page.getByTestId("image-submit").click();
    await expect(page.getByTestId("image-submit")).toBeEnabled({ timeout: 10000 });

    const last = captured[captured.length - 1];
    expect((last.reference_images as string[]).length).toBe(1);
    expect(last.enhance_prompt).toBe(false);
    expect(last.media_type).toBe("image");
  });

  test("合并 Tab：需要 2 张参考图，多图进入 reference_images", async ({ page }) => {
    const captured: Array<Record<string, unknown>> = [];
    await mockBackend(page, captured);
    await openPage(page);

    await page.getByRole("button", { name: "合并图像", exact: true }).click();
    await page.getByTestId("image-prompt-input").fill("把图1的人物放进图2的场景");
    await expect(page.getByTestId("image-submit")).toBeDisabled();

    const file = {
      name: "ref.png",
      mimeType: "image/png",
      buffer: Buffer.from(PIXEL_PNG_BASE64, "base64"),
    };
    await page.locator('input[type="file"]').setInputFiles([file, file]);
    await expect(page.locator('img[alt="参考图"]')).toHaveCount(2);
    await expect(page.getByTestId("image-submit")).toBeEnabled({ timeout: 10000 });
    await page.getByTestId("image-submit").click();
    await expect(page.getByTestId("image-submit")).toBeEnabled({ timeout: 10000 });

    const last = captured[captured.length - 1];
    expect((last.reference_images as string[]).length).toBe(2);
    expect(last.enhance_prompt).toBe(false);
  });
});

test.describe("图像生成页 · 进度 / 重试 / 内容过滤（对标 Yapper）", () => {
  test.beforeEach(async ({ page }) => {
    await seedGuest(page);
  });

  test("生成中显示结果位骨架与百分比", async ({ page }) => {
    await page.route("**/api/v1/generate/", async (route) => {
      await route.fulfill({ json: { task_id: "slow-1", status: "queued", estimated_model: "m", estimated_time_seconds: 30, estimated_cost_credits: 1, poll_url: "/api/v1/tasks/slow-1" } });
    });
    let polls = 0;
    await page.route("**/api/v1/tasks/slow-1", async (route) => {
      polls++;
      if (polls < 3) {
        await route.fulfill({ json: { task_id: "slow-1", status: "generating", progress: 50, current_stage: "模型推理中" } });
      } else {
        await route.fulfill({ json: { task_id: "slow-1", status: "completed", results: [{ url: PIXEL_GIF, type: "image", model: "m", seed: 1 }], cost_credits: 1 } });
      }
    });
    await openPage(page);
    await selectOption(page, "count-select", "2");
    await page.getByTestId("image-prompt-input").fill("progress skeleton test");
    await page.getByTestId("image-submit").click();

    await expect(page.getByTestId("progress-skeleton")).toHaveCount(2);
    await expect(page.getByText(/\d+%/)).toBeVisible();
    await expect(page.getByTestId("image-results")).toBeVisible({ timeout: 15000 });
  });

  test("失败后自动重试，最多 3 次后成功", async ({ page }) => {
    let genCount = 0;
    await page.route("**/api/v1/generate/", async (route) => {
      genCount++;
      const id = genCount < 3 ? `fail-${genCount}` : "ok-3";
      await route.fulfill({ json: { task_id: id, status: "queued", estimated_model: "m", estimated_time_seconds: 1, estimated_cost_credits: 1, poll_url: `/api/v1/tasks/${id}` } });
    });
    await page.route("**/api/v1/tasks/**", async (route) => {
      const url = route.request().url();
      if (url.includes("ok-3")) {
        await route.fulfill({ json: { task_id: "ok-3", status: "completed", results: [{ url: PIXEL_GIF, type: "image", model: "m", seed: 1 }], cost_credits: 1 } });
      } else {
        await route.fulfill({ json: { task_id: "x", status: "failed", error_message: "provider error" } });
      }
    });
    await openPage(page);
    await page.getByTestId("image-prompt-input").fill("retry test");
    await page.getByTestId("image-submit").click();

    await expect(page.getByTestId("image-results")).toBeVisible({ timeout: 20000 });
    expect(genCount).toBe(3);
  });

  test("内容安全过滤：不重试，显示专属提示与政策链接", async ({ page }) => {
    let genCount = 0;
    await page.route("**/api/v1/generate/", async (route) => {
      genCount++;
      await route.fulfill({
        status: 400,
        json: { detail: { code: "CONTENT_MODERATION_BLOCKED", message: "提示词包含受限内容，请修改后重试" } },
      });
    });
    await openPage(page);
    await page.getByTestId("image-prompt-input").fill("some blocked prompt");
    await page.getByTestId("image-submit").click();

    await expect(page.getByTestId("moderation-notice")).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId("moderation-notice").getByText(/包含受限内容/)).toBeVisible();
    await expect(page.getByRole("link", { name: "查看内容政策" })).toBeVisible();
    expect(genCount).toBe(1);
    await expect(page.getByTestId("image-submit")).toBeEnabled({ timeout: 10000 });
  });
});

test.describe("图像生成页 · 真实生成（消耗少量 Credits）", () => {
  test.skip(process.env.E2E_REAL !== "1", "仅在 E2E_REAL=1 且配置 KIE_API_KEY 时运行");

  test("UI 端到端真实生成 1 张图", async ({ page }) => {
    test.setTimeout(120_000);
    await seedGuest(page);
    await openPage(page);

    await selectOption(page, "quality-select", "快速");
    await page.getByTestId("image-prompt-input").fill("a red apple on a white table, studio lighting");

    const started = Date.now();
    await page.getByTestId("image-submit").click();

    await expect(page.getByTestId("image-results")).toBeVisible({ timeout: 90_000 });
    const img = page.getByTestId("image-results").locator("img").first();
    await expect(img).toBeVisible({ timeout: 30_000 });
    const src = await img.getAttribute("src");
    expect(src).toMatch(/\/api\/v1\/media\//);

    const elapsed = Math.round((Date.now() - started) / 1000);
    console.log(`[real-generate] completed in ${elapsed}s, src=${src}`);
  });
});
