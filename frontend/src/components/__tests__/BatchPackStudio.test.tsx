import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { BatchPackStudio } from "../BatchPackStudio";

vi.mock("@/lib/api", () => ({
  listPhotoPacks: vi.fn(async () => ([
    {
      id: "product",
      label: "电商产品图",
      category: "product",
      desc: "白底套系",
      i2i: true,
      aspect: "1:1",
      variation_count: 4,
      variations: [{ label: "白底正面" }],
      model: "nano-banana",
      cost_per: 2,
      honesty: "N 个独立图像任务",
    },
  ])),
  quotePack: vi.fn(async () => ({
    pack_id: "product",
    count: 4,
    cost_per: 2,
    estimated_cost_credits: 8,
    resolved_model: "nano-banana",
    preferred_model: "gpt-image-2",
    affordable: true,
    honesty: "N 个独立图像任务（非单请求多图）。",
  })),
  generatePack: vi.fn(),
  getTaskStatus: vi.fn(),
  uploadImage: vi.fn(),
  publishShare: vi.fn(),
}));

describe("BatchPackStudio P2", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("shows pack honesty and quoted credits", async () => {
    render(
      <BatchPackStudio
        defaultPack="product"
        category="product"
        title="产品图批量生成"
        subtitle="测试"
      />,
    );
    await waitFor(() => {
      expect(screen.getByTestId("pack-honesty")).toBeInTheDocument();
    });
    expect(screen.getByTestId("pack-honesty").textContent).toMatch(/独立图像任务/);
    expect(screen.getByTestId("pack-honesty").textContent).toMatch(/8 积分/);
  });
});
