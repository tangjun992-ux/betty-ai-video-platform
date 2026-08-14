import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import type { ReactNode } from "react";
import LibraryPage from "../page";
import { LocaleProvider } from "@/i18n/LocaleProvider";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/library",
  useSearchParams: () => new URLSearchParams(),
}));

function wrap(ui: ReactNode) {
  return render(<LocaleProvider>{ui}</LocaleProvider>);
}

describe("Library P1 Yapper assets", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true,
      json: async () => ({
        items: [],
        total: 0,
        counts: { all: 0, image: 0, video: 0, audio: 0, upload: 0, generated: 0, favorite: 0, today: 2, upscale: 0, motion: 0, lipsync: 0 },
        folders: [],
      }),
    })));
  });

  it("shows Multi Select and Today filters", () => {
    wrap(<LibraryPage />);
    expect(screen.getByTestId("library-multi-select")).toBeInTheDocument();
    expect(screen.getByTestId("library-today")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("library-multi-select"));
    expect(screen.getByTestId("library-selected-count")).toBeInTheDocument();
  });
});
