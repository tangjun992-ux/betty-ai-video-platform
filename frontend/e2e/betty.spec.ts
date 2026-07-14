import { test, expect } from "@playwright/test";

test.describe("首页", () => {
  test("加载并显示 Hero 区域", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("h1")).toContainText(/让每个创意|Turn every idea/);
    await expect(page.getByRole("button", { name: /生成视频|Generate video/i }).first()).toBeVisible();
    await expect(page.getByText(/已验证 AI 模型|Verified AI models/i)).toBeVisible();
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
  test("加载三栏布局", async ({ page }) => {
    await page.goto("/create/video");
    await expect(page.getByText(/视频参数|Video settings/i)).toBeVisible();
    await expect(page.getByText(/风格|Style/i).first()).toBeVisible();
    await expect(page.getByText(/模型选择|Model/i)).toBeVisible();
  });

  test("Multi-Shot 按钮存在", async ({ page }) => {
    await page.goto("/create/video");
    await expect(page.getByRole("button", { name: /Multi-Shot/i })).toBeVisible();
  });

  test("质量预设已渲染", async ({ page }) => {
    await page.goto("/create/video");
    const qualityLabel = page.getByText(/质量预设|Quality preset/i);
    await expect(qualityLabel).toBeVisible();
    await qualityLabel.click();
    await expect(qualityLabel.locator("..")).toBeVisible();
  });
});

test.describe("图片创作页", () => {
  test("加载 CosmicPromptCard 和参考图按钮", async ({ page }) => {
    await page.goto("/create/image");
    await expect(page.getByRole("button", { name: /添加参考图|Add reference/i })).toBeVisible();
  });

  test("建议词按钮可见", async ({ page }) => {
    await page.goto("/create/image");
    await expect(page.getByRole("button", { name: /赛博朋克|Cyberpunk/i })).toBeVisible();
  });

  test("Prompt 输入区存在", async ({ page }) => {
    await page.goto("/create/image");
    const textarea = page.getByPlaceholder(/描述你想要创作的图像|Describe the image/i);
    await expect(textarea).toBeVisible();
  });
});
