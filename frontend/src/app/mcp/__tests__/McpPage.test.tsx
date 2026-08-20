import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import type { ReactNode } from "react";
import McpPage from "../page";
import { LocaleProvider } from "@/i18n/LocaleProvider";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/mcp",
  useSearchParams: () => new URLSearchParams(),
}));

function wrap(ui: ReactNode) {
  return render(<LocaleProvider>{ui}</LocaleProvider>);
}

describe("MCP / API product page honesty", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/mcp/connector")) {
        return {
          ok: true,
          json: async () => ({
            endpoint: "http://127.0.0.1:8000/api/v1/mcp/connector",
            auth: { oauth: false },
            honesty: "API Key, not OAuth",
          }),
        };
      }
      if (url.includes("/public/models")) {
        return {
          ok: true,
          json: async () => ({
            active_count: 9,
            models: [
              { id: "seedance-2.0", display_name: "Seedance 2.0", media_types: ["video"] },
              { id: "nano-banana-2", display_name: "Nano Banana 2", media_types: ["image"] },
            ],
          }),
        };
      }
      return { ok: true, json: async () => ({}) };
    }));
  });

  it("sells MCP without 54+ or OAuth fiction", () => {
    wrap(<McpPage />);
    expect(screen.getByTestId("mcp-headline")).toBeInTheDocument();
    const honesty = screen.getByTestId("mcp-honesty").textContent || "";
    expect(honesty).toMatch(/API Key|密钥/);
    expect(honesty).toMatch(/不写 54\+|not 54\+/);
    expect(honesty).toMatch(/OAuth/);
    expect(honesty).toMatch(/不宣称 Seedance 2\.5|not Seedance 2\.5/);
    expect(screen.getByTestId("mcp-config").textContent).toMatch(/sk_betty_/);
    expect(screen.getByTestId("mcp-config").textContent).toMatch(/mcp\/connector/);
  });

  it("switches client tabs without leaving the page", () => {
    wrap(<McpPage />);
    fireEvent.click(screen.getByTestId("mcp-client-claude"));
    expect(screen.getByTestId("mcp-connect").textContent).toMatch(/OAuth/);
  });
});
