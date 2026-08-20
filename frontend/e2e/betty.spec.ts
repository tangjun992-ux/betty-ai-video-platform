import { test, expect } from "@playwright/test";

test.describe("首页", () => {
  test("加载并显示 Hero 区域", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("h1")).toContainText(/让每个创意|Turn every idea/);
    await expect(page.getByRole("button", { name: /生成视频|Generate video/i }).first()).toBeVisible();
    // STATS 卡片与段落均含「已验证 AI 模型」— 取首个避免 strict mode
    await expect(page.getByText(/已验证 AI 模型|Verified AI models/i).first()).toBeVisible();
  });

  test("热门模板卡片可见", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /热门创作模板|Popular templates/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /电影级科幻|Cinematic sci-fi/i })).toBeVisible({ timeout: 5000 });
  });
});

test.describe("导航", () => {
  test("可直接访问视频创作页", async ({ page }) => {
    await page.goto("/create/video");
    await expect(page).toHaveURL(/\/create\/video/);
  });

  test("可直接访问图片创作页", async ({ page }) => {
    await page.goto("/create/image");
    await expect(page).toHaveURL(/\/create\/image/);
  });
});

test.describe("视频创作页", () => {
  test("加载 VideoComposer 参数条", async ({ page }) => {
    await page.goto("/create/video");
    await expect(page.getByTestId("video-prompt")).toBeVisible();
    await expect(page.getByText(/^模型$/).first()).toBeVisible();
    await expect(page.getByText(/^质量$/).first()).toBeVisible();
  });

  test("Multi-Shot 在「更多」菜单内", async ({ page }) => {
    await page.goto("/create/video");
    await page.getByText(/^更多$/).click();
    await expect(page.getByText(/多镜头分镜/)).toBeVisible();
  });

  test("质量预设已渲染", async ({ page }) => {
    await page.goto("/create/video");
    const qualityChip = page.getByText(/^质量$/).first();
    await expect(qualityChip).toBeVisible();
    await qualityChip.click();
    await expect(page.getByRole("button", { name: "快速", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "均衡", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "高清", exact: true })).toBeVisible();
  });
});

test.describe("Extract / Pricing 诚实边界", () => {
  test("Instagram 仅 URL 时禁用提交并显示提示", async ({ page }) => {
    await page.goto("/create/extract");
    await page.getByRole("button", { name: "接受全部" }).click();
    const urlInput = page.getByTestId("extract-url");
    await urlInput.click();
    await urlInput.fill("https://www.instagram.com/reel/abc123/");
    await expect(urlInput).toHaveValue(/instagram\.com/);
    await expect(page.getByTestId("extract-ig-honesty")).toBeVisible();
    await expect(page.getByTestId("extract-submit")).toBeDisabled();
  });

  test("Pricing 无 Stripe 时订阅按钮 disabled", async ({ page }) => {
    await page.goto("/pricing");
    const banner = page.getByTestId("pricing-stripe-honesty");
    if (await banner.isVisible()) {
      await expect(page.getByRole("button", { name: /选择|Choose|Creator/i }).first()).toBeDisabled();
    }
  });
});

test.describe("图片创作页", () => {
  test("加载 ImageComposer 与参考图入口", async ({ page }) => {
    await page.goto("/create/image");
    await expect(page.getByTitle("添加图片")).toBeVisible();
  });

  test("推荐词入口可见", async ({ page }) => {
    await page.goto("/create/image");
    await expect(page.getByRole("button", { name: /试试推荐词|Try a suggestion/i })).toBeVisible();
  });

  test("Prompt 输入区存在", async ({ page }) => {
    await page.goto("/create/image");
    const textarea = page.getByPlaceholder(/输入提示词|Describe the image/i);
    await expect(textarea).toBeVisible();
  });
});
