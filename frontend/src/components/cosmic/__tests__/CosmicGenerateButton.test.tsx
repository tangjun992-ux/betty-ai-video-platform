import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CosmicGenerateButton } from "@/components/cosmic/CosmicGenerateButton";

describe("CosmicGenerateButton", () => {
  it("渲染默认 primary 变体", () => {
    render(<CosmicGenerateButton>生成</CosmicGenerateButton>);
    expect(screen.getByText("生成")).toBeInTheDocument();
  });

  it("渲染不同变体", () => {
    const variants = ["primary", "secondary", "ghost", "destructive", "outline-glow"] as const;
    for (const v of variants) {
      const { unmount } = render(<CosmicGenerateButton variant={v}>btn</CosmicGenerateButton>);
      expect(screen.getByText("btn")).toBeInTheDocument();
      unmount();
    }
  });

  it("渲染不同尺寸", () => {
    const sizes = ["sm", "md", "lg", "xl"] as const;
    for (const s of sizes) {
      const { unmount } = render(<CosmicGenerateButton size={s}>btn</CosmicGenerateButton>);
      expect(screen.getByText("btn")).toBeInTheDocument();
      unmount();
    }
  });

  it("loading 状态显示 spinner 且禁用点击", async () => {
    const onClick = vi.fn();
    render(<CosmicGenerateButton loading onClick={onClick}>生成</CosmicGenerateButton>);
    await userEvent.click(screen.getByRole("button"));
    expect(onClick).not.toHaveBeenCalled();
  });

  it("disabled 状态阻止点击", async () => {
    const onClick = vi.fn();
    render(<CosmicGenerateButton disabled onClick={onClick}>生成</CosmicGenerateButton>);
    await userEvent.click(screen.getByRole("button"));
    expect(onClick).not.toHaveBeenCalled();
  });

  it("点击触发 onClick", async () => {
    const onClick = vi.fn();
    render(<CosmicGenerateButton onClick={onClick}>生成</CosmicGenerateButton>);
    await userEvent.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("icon 模式仅渲染图标无文字", () => {
    render(<CosmicGenerateButton size="icon">隐藏文字</CosmicGenerateButton>);
    expect(screen.queryByText("隐藏文字")).toBeNull();
  });
});
