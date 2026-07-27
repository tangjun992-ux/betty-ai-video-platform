import { APIRequestContext } from "@playwright/test";
import { execSync } from "child_process";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";

export const E2E_GUEST_ID = "e2e-timeline-guest-fixed-001";
const API_BASE = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "").endsWith("/api/v1")
  ? process.env.NEXT_PUBLIC_API_URL!.replace(/\/+$/, "")
  : `${(process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "")}/api/v1`;

function ensureDir(dir: string) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

function renderDemoClip(outPath: string, filter: string) {
  ensureDir(path.dirname(outPath));
  // FFmpeg is available on the CI/dev host; this avoids depending on backend Python/drawtext fonts.
  execSync(
    `ffmpeg -y -f lavfi -i "${filter}" -pix_fmt yuv420p -an "${outPath}"`,
    { encoding: "utf-8", timeout: 60_000, stdio: "ignore" },
  );
}

export async function waitForBackend(maxMs = 120_000): Promise<void> {
  const base = API_BASE.replace(/\/api\/v1$/, "");
  const deadline = Date.now() + maxMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`${base}/health`);
      if (res.ok) return;
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 1500));
  }
  throw new Error("Backend health check timed out");
}

/** Render short demo MP4s via host ffmpeg and upload into the E2E guest library. */
export async function seedTimelineVideos(request: APIRequestContext): Promise<string[]> {
  const cacheDir = path.join(os.tmpdir(), "betty-e2e-clips");
  const clipPaths = [
    path.join(cacheDir, "e2e-clip-a.mp4"),
    path.join(cacheDir, "e2e-clip-b.mp4"),
  ];

  renderDemoClip(clipPaths[0], "testsrc=duration=2:size=320x180:rate=1");
  renderDemoClip(clipPaths[1], "rgbtestsrc=duration=2:size=320x180:rate=1");

  const urls: string[] = [];
  for (let i = 0; i < clipPaths.length; i++) {
    const filePath = clipPaths[i];
    if (!fs.existsSync(filePath)) {
      throw new Error(`Demo video not found on disk: ${filePath}`);
    }
    const buf = fs.readFileSync(filePath);
    const upload = await request.post(`${API_BASE}/library/upload`, {
      headers: { "X-Guest-Id": E2E_GUEST_ID },
      multipart: {
        file: {
          name: `e2e-timeline-${i}.mp4`,
          mimeType: "video/mp4",
          buffer: buf,
        },
      },
    });
    if (!upload.ok()) {
      throw new Error(`Library upload failed: ${upload.status()} ${await upload.text()}`);
    }
    const item = await upload.json();
    urls.push(item.url);
  }
  return urls;
}
