import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
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
        folders: ["Campaign A"],
        folder_catalog: [{ name: "Campaign A", count: 0 }],
      }),
    })));
  });

  it("shows Multi Select, Today, and folder CRUD controls", async () => {
    wrap(<LibraryPage />);
    expect(screen.getByTestId("library-multi-select")).toBeInTheDocument();
    expect(screen.getByTestId("library-today")).toBeInTheDocument();
    expect(screen.getByTestId("library-folders")).toBeInTheDocument();
    expect(screen.getByTestId("library-new-folder")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId("library-folder-Campaign A")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("library-folder-Campaign A"));
    expect(screen.getByTestId("library-rename-folder")).toBeInTheDocument();
    expect(screen.getByTestId("library-delete-folder")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("library-multi-select"));
    expect(screen.getByTestId("library-selected-count")).toBeInTheDocument();
  });
});
