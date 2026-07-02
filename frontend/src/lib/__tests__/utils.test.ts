import { describe, it, expect, vi } from "vitest";
import { cn } from "@/lib/utils";

describe("cn (classname utility)", () => {
  it("合并多个类名", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("过滤 falsy 值", () => {
    expect(cn("a", false, undefined, null, "b")).toBe("a b");
  });

  it("处理条件类名", () => {
    expect(cn("base", true && "active", false && "hidden")).toBe("base active");
  });

  it("处理 tailwind-merge 冲突", () => {
    expect(cn("px-4", "px-6")).toBe("px-6");
  });

  it("空输入", () => {
    expect(cn()).toBe("");
  });
});
