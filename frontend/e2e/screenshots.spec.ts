import { test, type Page } from "@playwright/test";
import * as path from "path";
import * as fs from "fs";

const OUT_DIR = path.resolve(__dirname, "../test-results/screenshots");

type Shot = {
  name: string;
  path: string;
  fullPage?: boolean;
};

const SHOTS: Shot[] = [
  { name: "home", path: "/", fullPage: true },
  { name: "tools", path: "/tools", fullPage: true },
  { name: "agent", path: "/agent", fullPage: false },
  { name: "create-video", path: "/create/video", fullPage: false },
  { name: "pricing", path: "/pricing", fullPage: true },
  { name: "explore", path: "/explore", fullPage: true },
];

async function dismissOverlays(page: Page) {
  await page.evaluate(() => {
    try {
      localStorage.setItem("betty-cookie-consent", JSON.stringify({ value: "all", at: Date.now() }));
      localStorage.setItem("betty-demo-dismissed", "1");
    } catch {}
  });
}

async function setTheme(page: Page, theme: "dark" | "light") {
  await page.evaluate((t) => {
    try {
      localStorage.setItem("betty-theme", t);
    } catch {}
    const root = document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(t);
  }, theme);
  // Wait for React theme context to re-apply and settle
  await page.waitForTimeout(200);
}

async function screenshotPage(
  page: Page,
  theme: "dark" | "light",
  vp: "desktop" | "mobile",
  shot: Shot
) {
  const dir = path.join(OUT_DIR, `${theme}-${vp}`);
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `${shot.name}.png`);

  await page.goto(`http://localhost:3000${shot.path}`, {
    waitUntil: "networkidle",
    timeout: 60_000,
  });

  // Persist theme and dismiss overlays in the target origin, then reload clean.
  await page.evaluate((t) => {
    try {
      localStorage.setItem("betty-theme", t);
      localStorage.setItem("betty-cookie-consent", JSON.stringify({ value: "all", at: Date.now() }));
      localStorage.setItem("betty-demo-dismissed", "1");
    } catch {}
  }, theme);
  await page.reload({ waitUntil: "networkidle", timeout: 60_000 });

  // Final fallback: force-hide any overlay that still sneaks through.
  await page.addStyleTag({
    content: `
      [role="dialog"][aria-label="Cookie 同意"],
      [class*="demo-banner"],
      [class*="CookieConsent"] {
        display: none !important;
      }
    `,
  });

  await page.screenshot({
    path: file,
    fullPage: shot.fullPage ?? false,
    type: "png",
  });
}

test.describe("desktop screenshots", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  for (const theme of ["dark", "light"] as const) {
    for (const shot of SHOTS) {
      test(`${theme} /${shot.name}`, async ({ page }) => {
        await screenshotPage(page, theme, "desktop", shot);
      });
    }
  }
});

test.describe("mobile screenshots", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  for (const theme of ["dark", "light"] as const) {
    for (const shot of SHOTS) {
      test(`${theme} mobile /${shot.name}`, async ({ page }) => {
        await screenshotPage(page, theme, "mobile", shot);
      });
    }
  }
});
