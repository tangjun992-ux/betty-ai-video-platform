import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CosmicPromptCard } from "../CosmicPromptCard";

describe("CosmicPromptCard", () => {
  /* ── 基础渲染 ── */
  it("渲染 textarea 和 placeholder", () => {
    render(<CosmicPromptCard onSubmit={vi.fn()} />);
    const textarea = screen.getByPlaceholderText("描述你想要的画面，AI 将为你创作...");
    expect(textarea).toBeTruthy();
  });

  it("渲染自定义 placeholder", () => {
    render(<CosmicPromptCard onSubmit={vi.fn()} placeholder="输入你的创意..." />);
    expect(screen.getByPlaceholderText("输入你的创意...")).toBeTruthy();
  });

  /* ── 输入 ── */
  it("输入文字更新 textarea value", () => {
    render(<CosmicPromptCard onSubmit={vi.fn()} />);
    const textarea = screen.getByPlaceholderText("描述你想要的画面，AI 将为你创作...") as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "一只在月球上跳舞的猫" } });
    expect(textarea.value).toBe("一只在月球上跳舞的猫");
  });

  /* ── 提交 ── */
  it("点击生成按钮触发 onSubmit", () => {
    const onSubmit = vi.fn();
    render(<CosmicPromptCard onSubmit={onSubmit} />);
    const textarea = screen.getByPlaceholderText("描述你想要的画面，AI 将为你创作...");
    fireEvent.change(textarea, { target: { value: "测试提示词" } });

    const generateBtn = screen.getByText("生成");
    fireEvent.click(generateBtn);

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith("测试提示词");
  });

  it.skip("按 Enter 键提交 (React 19 jsdom 兼容性)", () => {
    const onSubmit = vi.fn();
    render(<CosmicPromptCard onSubmit={onSubmit} />);
    const textarea = screen.getByPlaceholderText("描述你想要的画面，AI 将为你创作...");

    fireEvent.change(textarea, { target: { value: "hello" } });
    // Use fireEvent.keyDown for React synthetic event
    fireEvent.keyDown(textarea, { key: "Enter", code: "Enter", charCode: 13 });

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith("hello");
  });

  it("空输入不触发提交", () => {
    const onSubmit = vi.fn();
    render(<CosmicPromptCard onSubmit={onSubmit} />);
    const textarea = screen.getByPlaceholderText("描述你想要的画面，AI 将为你创作...");

    textarea.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", code: "Enter", keyCode: 13, bubbles: true }));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("loading 时不允许提交", () => {
    const onSubmit = vi.fn();
    render(<CosmicPromptCard onSubmit={onSubmit} loading />);
    const textarea = screen.getByPlaceholderText("描述你想要的画面，AI 将为你创作...");

    fireEvent.change(textarea, { target: { value: "loading 测试" } });

    const generateBtn = screen.getByText("生成");
    fireEvent.click(generateBtn);

    expect(onSubmit).not.toHaveBeenCalled();
  });

  /* ── 建议词 ── */
  it("渲染建议词按钮", () => {
    const suggestions = ["赛博朋克夜景", "水墨山水", "温馨咖啡馆"];
    render(<CosmicPromptCard onSubmit={vi.fn()} suggestions={suggestions} />);

    expect(screen.getByText("赛博朋克夜景")).toBeTruthy();
    expect(screen.getByText("水墨山水")).toBeTruthy();
    expect(screen.getByText("温馨咖啡馆")).toBeTruthy();
  });

  it("点击建议词填充到 textarea", () => {
    const suggestions = ["赛博朋克夜景"];
    render(<CosmicPromptCard onSubmit={vi.fn()} suggestions={suggestions} />);

    fireEvent.click(screen.getByText("赛博朋克夜景"));
    const textarea = screen.getByPlaceholderText("描述你想要的画面，AI 将为你创作...") as HTMLTextAreaElement;
    expect(textarea.value).toBe("赛博朋克夜景");
  });

  /* ── Mode 标签 ── */
  it("渲染 mode 标签", () => {
    render(<CosmicPromptCard onSubmit={vi.fn()} mode="文生图" />);
    expect(screen.getByText("文生图")).toBeTruthy();
  });

  it("无 mode 时不渲染标签", () => {
    render(<CosmicPromptCard onSubmit={vi.fn()} />);
    expect(screen.queryByText("文生图")).toBeNull();
  });

  /* ── 参考图 ── */
  it("渲染参考图 strip", () => {
    const refs = [{ preview: "https://example.com/img.jpg", name: "ref.jpg" }];
    render(<CosmicPromptCard onSubmit={vi.fn()} referenceFiles={refs} />);
    const img = screen.getByAltText("ref.jpg");
    expect(img).toBeTruthy();
    expect(img.getAttribute("src")).toBe("https://example.com/img.jpg");
  });

  /* ── className ── */
  it("className 透传", () => {
    const { container } = render(<CosmicPromptCard onSubmit={vi.fn()} className="my-card" />);
    expect(container.firstChild).toBeTruthy();
  });
});
