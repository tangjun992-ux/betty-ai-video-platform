import { test, expect } from "@playwright/test";

test.describe("首页", () => {
  test("加载并显示 Hero 创作台", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("h1")).toContainText(/让每个创意|Turn every idea/);
    await expect(page.getByRole("button", { name: /开始导演|Start directing|开始创作|Create/i }).first()).toBeVisible();
    await expect(page.getByText(/已验证模型|Verified models/i)).toBeVisible();
  });

  test("创作工具矩阵可见", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /创作工具|创作工具/i })).toBeVisible();
    const toolsSection = page.locator("section").filter({ hasText: /创作工具|创作工具/ });
    await expect(toolsSection.getByRole("link", { name: /AI Agent/i }).first()).toBeVisible({ timeout: 5000 });
    await expect(toolsSection.getByRole("link", { name: /视频创作|Video Creation/i }).first()).toBeVisible({ timeout: 5000 });
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
  test("加载 dzine 工作台布局", async ({ page }) => {
    await page.goto("/create/video");
    // dzine 式：模型下拉 + 统一参数面板 + 输入区
    await expect(page.getByTestId("video-model-select")).toBeVisible();
    await expect(page.getByTestId("video-param-select")).toBeVisible();
    await expect(page.locator("textarea").first()).toBeVisible();
  });

  test("Multi-Shot 按钮存在", async ({ page }) => {
    await page.goto("/create/video");
    await page.getByTestId("video-more-toggle").click();
    await expect(page.getByRole("button", { name: /Multi-Shot/i })).toBeVisible();
  });

  test("参数面板含质量/分辨率/时长", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/create/video");
    await page.getByTestId("video-model-select").waitFor();
    await page.waitForTimeout(800);
    await page.getByTestId("video-param-select").click();
    await expect(page.locator('button[title="16:9"]')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Resolution")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Duration")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Image Quality")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText("Count")).toBeVisible({ timeout: 10000 });
  });
});

test.describe("图片创作页", () => {
  test("加载 CosmicPromptCard 和参考图按钮", async ({ page }) => {
    await page.goto("/create/image");
    await expect(page.getByRole("button", { name: /添加参考图|Add reference/i }).first()).toBeVisible();
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
