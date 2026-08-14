import { describe, it, expect } from "vitest";
import { formatApiDetail } from "@/lib/api";

describe("formatApiDetail", () => {
  it("uses string detail", () => {
    expect(formatApiDetail("积分不足", "fallback")).toBe("积分不足");
  });

  it("unpacks 429 concurrency object", () => {
    expect(formatApiDetail({
      error: "concurrency_limit",
      message: "并发已满（4/4）。升级 Personal 可同时跑 6 个任务",
      retry_after: 30,
    }, "fail")).toContain("并发已满");
  });

  it("falls back", () => {
    expect(formatApiDetail(null, "生成请求失败: 500")).toBe("生成请求失败: 500");
  });
});
