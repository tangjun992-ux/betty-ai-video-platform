import { test, expect } from "@playwright/test";
import { waitForBackend } from "./helpers";

test.beforeAll(async () => {
  await waitForBackend();
});

test.describe("能力诚实披露", () => {
  test("唇形页展示能力提示", async ({ page }) => {
    await page.goto("/create/lipsync");
    const accept = page.getByRole("button", { name: /接受全部|Accept all/i });
    if (await accept.isVisible().catch(() => false)) await accept.click();
    const notice = page.getByTestId("capability-notice-lipsync");
    await expect(notice).toBeVisible({ timeout: 60_000 });
    await expect(notice).toHaveAttribute("data-loading", "false", { timeout: 15_000 });
    // Demo copy must be explicit that it is not real lip-sync
    if ((await notice.getAttribute("data-demo")) === "true") {
      await expect(notice).toContainText(/并非真实口型|Ken Burns/);
    } else {
      await expect(notice).toContainText(/真实|可用/);
    }
  });

  test("运动页展示能力提示（演示模式禁用提交 / 真实模式可提交）", async ({ page }) => {
    await page.goto("/create/motion");
    const accept = page.getByRole("button", { name: /接受全部|Accept all/i });
    if (await accept.isVisible().catch(() => false)) await accept.click();
    const notice = page.getByTestId("capability-notice-motion");
    await expect(notice).toBeVisible({ timeout: 60_000 });
    await expect(notice).toHaveAttribute("data-loading", "false", { timeout: 15_000 });

    if ((await notice.getAttribute("data-demo")) === "true") {
      await expect(notice).toContainText(/需要真实模型能力|配置|模型 Key/);
      // Submit CTA reflects the blocked state
      await expect(page.getByRole("button", { name: /需配置模型 Key 后可用/ })).toBeVisible();
    } else {
      await expect(notice).toContainText(/Kling Motion|真实生成|原生/);
      await expect(page.getByRole("button", { name: /开始运动|运动控制|运动迁移/ })).toBeVisible();
    }
  });
});

test.describe("模型目录治理", () => {
  test("默认模型列表仅含已验证模型", async ({ request }) => {
    const base = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1")
      .replace(/\/+$/, "");
    const api = base.endsWith("/api/v1") ? base : `${base}/api/v1`;
    const res = await request.get(`${api}/models/`);
    expect(res.ok()).toBeTruthy();
    const data = await res.json();
    expect(Array.isArray(data.models)).toBeTruthy();
    for (const m of data.models) {
      expect(m.status).toBe("active");
      expect(m.verified).toBe(true);
    }
    // Beta models still exist but are quarantined out of the default list
    expect(data.beta_count).toBeGreaterThan(0);
  });
});
