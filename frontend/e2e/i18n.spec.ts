import { test, expect } from "@playwright/test";

/**
 * i18n / internationalization coverage — non-flaky (no model generation).
 * Verifies that `?lang=en` is a real English entry point and `?lang=zh` is
 * Chinese across the monetization + creation surfaces we localized (P2).
 */

test.describe("i18n · sidebar image tools", () => {
  test("upscale tool renders in English with ?lang=en", async ({ page }) => {
    await page.goto("/create/upscale?lang=en");
    await expect(page.getByRole("heading", { name: "AI Upscale" })).toBeVisible();
    await expect(page.getByText("Upload image")).toBeVisible();
    await expect(page.getByText("Result", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Upscale" })).toBeVisible();
    // No Chinese tool labels leaking through in English mode.
    await expect(page.getByText("上传图片")).toHaveCount(0);
  });

  test("upscale tool renders in Chinese with ?lang=zh", async ({ page }) => {
    await page.goto("/create/upscale?lang=zh");
    await expect(page.getByRole("heading", { name: "AI 放大" })).toBeVisible();
    await expect(page.getByText("上传图片", { exact: true })).toBeVisible();
    await expect(page.getByText("开始放大")).toBeVisible();
  });

  test("image editor tool renders in English", async ({ page }) => {
    await page.goto("/create/image-editor?lang=en");
    await expect(page.getByRole("heading", { name: "AI Image Editor" })).toBeVisible();
    await expect(page.getByText("Edit instruction")).toBeVisible();
    await expect(page.getByRole("button", { name: "Apply edit" })).toBeVisible();
  });
});

test.describe("i18n · pricing (monetization)", () => {
  test("pricing renders in English with ?lang=en", async ({ page }) => {
    await page.goto("/pricing?lang=en");
    await expect(page.getByText("Every plan includes:")).toBeVisible();
    await expect(page.getByText("Most Popular")).toBeVisible();
    await expect(page.getByRole("button", { name: "Choose Starter" })).toBeVisible();
    await expect(page.getByText("Frequently asked questions")).toBeVisible();
    // Billing-cycle toggle localized.
    await expect(page.getByRole("radio", { name: "Monthly" })).toBeVisible();
  });

  test("pricing renders in Chinese with ?lang=zh", async ({ page }) => {
    await page.goto("/pricing?lang=zh");
    await expect(page.getByText("所有计划均包含：")).toBeVisible();
    await expect(page.getByText("常见问题")).toBeVisible();
    await expect(page.getByRole("radio", { name: "月付" })).toBeVisible();
  });
});

test.describe("i18n · creation surfaces", () => {
  test("image workspace title localizes", async ({ page }) => {
    await page.goto("/create/image?lang=en");
    await expect(page.getByRole("heading", { name: /Prompt · Edit · Compose pro images/i })).toBeVisible();
  });

  test("video workspace title localizes", async ({ page }) => {
    await page.goto("/create/video?lang=en");
    await expect(page.getByRole("heading", { name: /Prompt · Edit · Compose pro video/i })).toBeVisible();
  });
});
