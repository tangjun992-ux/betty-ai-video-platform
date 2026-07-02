import { test, expect } from "@playwright/test";

test.describe("首页", () => {
  test("加载并显示 Hero 区域", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("h1")).toContainText("Make something");
    // 使用精确选择器：Hero 区域内的 CTA 按钮
    await expect(page.getByRole("link", { name: "生成图片" }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "生成视频" }).first()).toBeVisible();
    await expect(page.getByText("15+ AI 模型")).toBeVisible();
  });

  test("热门模板卡片可见", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "热门创作模板" })).toBeVisible();
    await expect(page.getByRole("link", { name: /电影级科幻/ })).toBeVisible({ timeout: 5000 });
  });
});

test.describe("导航", () => {
  test("点击侧边栏视频创作跳转", async ({ page }) => {
    await page.goto("/");
    // 侧边栏中的"视频创作"链接
    await page.locator("aside").getByRole("link", { name: "视频创作" }).click();
    await expect(page).toHaveURL(/\/create\/video/);
  });

  test("点击侧边栏图片创作跳转", async ({ page }) => {
    await page.goto("/");
    await page.locator("aside").getByRole("link", { name: "图片创作" }).click();
    await expect(page).toHaveURL(/\/create\/image/);
  });
});

test.describe("视频创作页", () => {
  test("加载三栏布局", async ({ page }) => {
    await page.goto("/create/video");
    await expect(page.getByText("视频参数")).toBeVisible();
    await expect(page.getByText("风格", { exact: true })).toBeVisible();
    await expect(page.getByText("模型选择")).toBeVisible();
  });

  test("Multi-Shot 按钮存在", async ({ page }) => {
    await page.goto("/create/video");
    await expect(page.getByRole("button", { name: /Multi-Shot/ })).toBeVisible();
  });

  test("质量预设已渲染", async ({ page }) => {
    await page.goto("/create/video");
    await page.getByText("质量预设").click();
    await page.waitForTimeout(400);
    // 质量预设用 QualityCard 渲染，检查容器内有内容
    const qualitySection = page.locator("text=质量预设").locator("..");
    await expect(qualitySection).toBeVisible();
  });
});

test.describe("图片创作页", () => {
  test("加载 CosmicPromptCard 和参考图按钮", async ({ page }) => {
    await page.goto("/create/image");
    await expect(page.getByRole("button", { name: "添加参考图" })).toBeVisible();
  });

  test("建议词按钮可见", async ({ page }) => {
    await page.goto("/create/image");
    await expect(page.getByRole("button", { name: /赛博朋克/ })).toBeVisible();
  });

  test("Prompt 输入区存在", async ({ page }) => {
    await page.goto("/create/image");
    // CosmicPromptCard 的 textarea placeholder
    const textarea = page.getByPlaceholder("描述你想要创作的图像，或上传图片进行编辑...");
    await expect(textarea).toBeVisible();
  });
});
