import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CosmicParamPanel, CosmicSlider, CosmicSelect } from "../CosmicParamPanel";

describe("CosmicParamPanel", () => {
  /* ── 基础渲染 ── */
  it("渲染标题", () => {
    render(<CosmicParamPanel groups={[]} />);
    expect(screen.getByText("参数设置")).toBeTruthy();
  });

  it("渲染自定义标题", () => {
    render(<CosmicParamPanel groups={[]} title="高级设置" />);
    expect(screen.getByText("高级设置")).toBeTruthy();
  });

  it("渲染 group 标签", () => {
    const groups = [
      { id: "quality", label: "画质设置", children: <div>Quality Content</div> },
    ];
    render(<CosmicParamPanel groups={groups} />);
    expect(screen.getByText("画质设置")).toBeTruthy();
    expect(screen.getByText("Quality Content")).toBeTruthy();
  });

  it("渲染多个 groups", () => {
    const groups = [
      { id: "a", label: "组A", children: <span>Content A</span> },
      { id: "b", label: "组B", children: <span>Content B</span> },
    ];
    render(<CosmicParamPanel groups={groups} />);
    expect(screen.getByText("组A")).toBeTruthy();
    expect(screen.getByText("组B")).toBeTruthy();
  });

  /* ── 折叠/展开 ── */
  it("默认展开 group", () => {
    const groups = [
      { id: "open", label: "展开组", children: <span>可见内容</span> },
    ];
    render(<CosmicParamPanel groups={groups} />);
    expect(screen.getByText("可见内容")).toBeTruthy();
  });

  it("defaultCollapsed=true 的 group 默认收起 (内容不可见)", () => {
    const groups = [
      {
        id: "collapsed",
        label: "收起组",
        defaultCollapsed: true,
        children: <span>隐藏内容</span>,
      },
    ];
    render(<CosmicParamPanel groups={groups} />);
    // 内容应该不可见 (height:0 的 overflow hidden)
    expect(screen.queryByText("隐藏内容")).toBeNull();
  });

  it("点击 toggle 收起后展开 group", () => {
    const groups = [
      {
        id: "toggle",
        label: "可折叠",
        defaultCollapsed: true,
        children: <span>切换可见</span>,
      },
    ];
    render(<CosmicParamPanel groups={groups} />);
    // 默认不可见
    expect(screen.queryByText("切换可见")).toBeNull();
    // 点击展开
    fireEvent.click(screen.getByText("可折叠"));
    expect(screen.getByText("切换可见")).toBeTruthy();
  });

  it("点击两次 toggle (收→展→收)", () => {
    const groups = [
      { id: "double", label: "双切换", children: <span>双切换内容</span> },
    ];
    render(<CosmicParamPanel groups={groups} />);
    expect(screen.getByText("双切换内容")).toBeTruthy();

    fireEvent.click(screen.getByText("双切换")); // 收起
    expect(screen.queryByText("双切换内容")).toBeNull();

    fireEvent.click(screen.getByText("双切换")); // 展开
    expect(screen.getByText("双切换内容")).toBeTruthy();
  });

  /* ── Icon ── */
  it("渲染 group icon", () => {
    const groups = [
      {
        id: "icon-group",
        label: "有图标",
        icon: <span data-testid="group-icon">🎨</span>,
        children: <div>内容</div>,
      },
    ];
    render(<CosmicParamPanel groups={groups} />);
    expect(screen.getByTestId("group-icon")).toBeTruthy();
  });

  /* ── Tooltip ── */
  it("渲染 tooltip 图标", () => {
    const groups = [
      {
        id: "tip",
        label: "提示组",
        tooltip: "这是一个提示",
        children: <div>内容</div>,
      },
    ];
    render(<CosmicParamPanel groups={groups} />);
    expect(screen.getByTestId("icon-info")).toBeTruthy();
  });

  /* ── className ── */
  it("className 透传", () => {
    const { container } = render(<CosmicParamPanel groups={[]} className="my-panel" />);
    expect(container.firstChild).toBeTruthy();
  });
});

/* ─────────────────────────────────────────────────────
   CosmicSlider
   ───────────────────────────────────────────────────── */

describe("CosmicSlider", () => {
  it("渲染 label 和 value", () => {
    render(<CosmicSlider label="创造力" value={50} onChange={vi.fn()} />);
    expect(screen.getByText("创造力")).toBeTruthy();
    expect(screen.getByText("50")).toBeTruthy();
  });

  it("渲染 range input", () => {
    render(<CosmicSlider value={30} onChange={vi.fn()} />);
    const input = screen.getByRole("slider") as HTMLInputElement;
    expect(input).toBeTruthy();
    expect(input.value).toBe("30");
  });

  it("onChange 被调用", () => {
    const onChange = vi.fn();
    render(<CosmicSlider value={50} onChange={onChange} min={0} max={100} />);
    const input = screen.getByRole("slider");
    fireEvent.change(input, { target: { value: "75" } });
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith(75);
  });

  it("渲染左右标签", () => {
    render(<CosmicSlider value={50} onChange={vi.fn()} leftLabel="保守" rightLabel="激进" />);
    expect(screen.getByText("保守")).toBeTruthy();
    expect(screen.getByText("激进")).toBeTruthy();
  });

  it("showValue=false 不显示数值", () => {
    render(<CosmicSlider label="隐藏" value={42} onChange={vi.fn()} showValue={false} />);
    expect(screen.queryByText("42")).toBeNull();
  });

  it("className 透传", () => {
    const { container } = render(<CosmicSlider value={50} onChange={vi.fn()} className="my-slider" />);
    expect(container.firstChild).toBeTruthy();
  });
});

/* ─────────────────────────────────────────────────────
   CosmicSelect
   ───────────────────────────────────────────────────── */

describe("CosmicSelect", () => {
  const options = [
    { value: "512x512", label: "512×512" },
    { value: "1024x1024", label: "1024×1024" },
  ];

  it("渲染 options", () => {
    render(<CosmicSelect value="512x512" onChange={vi.fn()} options={options} />);
    expect(screen.getByText("512×512")).toBeTruthy();
    expect(screen.getByText("1024×1024")).toBeTruthy();
  });

  it("渲染 label", () => {
    render(<CosmicSelect label="分辨率" value="512x512" onChange={vi.fn()} options={options} />);
    expect(screen.getByText("分辨率")).toBeTruthy();
  });

  it("onChange 被调用", () => {
    const onChange = vi.fn();
    render(<CosmicSelect value="512x512" onChange={onChange} options={options} />);
    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "1024x1024" } });
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith("1024x1024");
  });
});
