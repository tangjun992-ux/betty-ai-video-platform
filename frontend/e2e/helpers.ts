import { APIRequestContext } from "@playwright/test";
import { execSync } from "child_process";
import * as fs from "fs";
import * as path from "path";

export const E2E_GUEST_ID = "e2e-timeline-guest-fixed-001";
const API_BASE = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "").endsWith("/api/v1")
  ? process.env.NEXT_PUBLIC_API_URL!.replace(/\/+$/, "")
  : `${(process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "")}/api/v1`;

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

/** Render demo MP4s via backend Python and upload into the E2E guest library. */
export async function seedTimelineVideos(request: APIRequestContext): Promise<string[]> {
  const backendDir = path.resolve(__dirname, "../../backend");
  const paths = execSync(
    `cd "${backendDir}" && python -c "` +
      "from app.adapters.demo_provider import render_demo_video, _local_media_path; " +
      "u1,_=render_demo_video('e2e clip a','320x180',2,'cinematic'); " +
      "u2,_=render_demo_video('e2e clip b','320x180',2,'sci-fi'); " +
      "print(_local_media_path(u1)); print(_local_media_path(u2))" +
      '"',
    { encoding: "utf-8", timeout: 180_000 },
  ).trim().split("\n").filter(Boolean);

  if (paths.length < 2) throw new Error("Failed to render E2E demo videos");

  const urls: string[] = [];
  for (let i = 0; i < paths.length; i++) {
    const filePath = paths[i].trim();
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
