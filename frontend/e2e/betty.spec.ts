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

  test("首页诚实条：尚未对公众收费开放", async ({ page }) => {
    await page.goto("/");
    const cookie = page.getByRole("button", { name: "接受全部" });
    if (await cookie.isVisible()) await cookie.click();
    await expect(page.getByTestId("home-commercial-honesty")).toBeVisible({ timeout: 10000 });
  });

  test("状态页展示商业开放裁决", async ({ page }) => {
    await page.goto("/status");
    const cookie = page.getByRole("button", { name: "接受全部" });
    try {
      if (await cookie.isVisible({ timeout: 2000 })) await cookie.click();
    } catch { /* banner already dismissed */ }
    await expect(page.getByTestId("status-commercial-open")).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/尚未商业开放|可对公众收费开放/)).toBeVisible();
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

test.describe("Studio 工具矩阵", () => {
  test("Video / Image 分区，入口真实且不含竞品名", async ({ page }) => {
    await page.goto("/tools");
    const cookie = page.getByRole("button", { name: "接受全部" });
    try { if (await cookie.isVisible({ timeout: 2000 })) await cookie.click(); } catch { /* ignore */ }
    await expect(page.getByTestId("tools-video-section")).toBeVisible();
    await expect(page.getByTestId("tools-image-section")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Video Tools" })).toBeVisible();
    await expect(page.getByRole("link", { name: /唇形同步/ })).toHaveAttribute("href", "/create/lipsync");
    await expect(page.getByRole("link", { name: /背景移除/ })).toHaveAttribute("href", "/create/bg-remove");
    await expect(page.getByText("Yapper-style")).toHaveCount(0);
  });
});

test.describe("首页工具路由", () => {
  test("放大与抠图指向独立 SKU 页", async ({ page }) => {
    await page.goto("/");
    const cookie = page.getByRole("button", { name: "接受全部" });
    try { if (await cookie.isVisible({ timeout: 2000 })) await cookie.click(); } catch { /* ignore */ }
    await expect(page.getByTestId("verified-model-marquee")).toBeVisible();
    await expect(page.getByTestId("home-tool--create-upscale")).toHaveAttribute("href", "/create/upscale");
    await expect(page.getByTestId("home-tool--create-bg-remove")).toHaveAttribute("href", "/create/bg-remove");
    await expect(page.getByTestId("home-tool--create-product")).toHaveAttribute("href", "/create/product");
  });
});
