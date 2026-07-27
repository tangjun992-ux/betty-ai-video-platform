import "@testing-library/jest-dom/vitest";
import React from "react";
import { vi } from "vitest";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

// Mock next/link
vi.mock("next/link", () => ({
  default: ({ children, href, ...rest }: any) =>
    React.createElement("a", { href, ...rest }, children),
}));

// Mock framer-motion — return actual React components, not strings
const motionProxy = new Proxy(
  {},
  {
    get: (_target, prop: string) => {
      if (prop === "div" || prop === "button" || prop === "span" || prop === "aside" ||
          prop === "p" || prop === "h1" || prop === "h2" || prop === "h3") {
        return React.forwardRef((props: any, ref: any) =>
          React.createElement(prop, { ref, ...props })
        );
      }
      return React.forwardRef((props: any, ref: any) =>
        React.createElement("div", { ref, ...props })
      );
    },
  }
);

vi.mock("framer-motion", () => ({
  motion: motionProxy,
  AnimatePresence: ({ children }: any) => React.createElement(React.Fragment, null, children),
  useAnimation: () => ({}),
  useMotionValue: () => ({ get: () => 0 }),
  useTransform: () => 0,
}));

// Mock lucide-react — return simple React components
vi.mock("lucide-react", () => {
  const iconNames = [
    "Sparkles", "ImageIcon", "Video", "Send", "X", "Wand2", "Upload",
    "ImagePlus", "Bot", "Zap", "Star", "ArrowRight", "ChevronRight",
    "ChevronDown", "ChevronLeft", "Loader2", "Search", "Menu",
    "Sun", "Moon", "User", "Settings", "LogIn", "LogOut", "Home",
    "Film", "Music", "Mic", "Scissors", "Maximize2", "Camera",
    "Palette", "Layers", "RefreshCw", "Play", "GripHorizontal",
    "Plus", "Lightbulb", "Link2", "Info", "SlidersHorizontal",
    "Grid3X3", "Gauge", "Crown", "Settings2", "ExternalLink",
    "Clock", "Download", "CheckCircle2", "Timer", "Award",
    "TrendingUp", "Users", "FolderOpen", "LayoutDashboard",
  ];

  const exports: Record<string, any> = {};
  for (const name of iconNames) {
    exports[name] = (props: any) =>
      React.createElement("span", { "data-testid": `icon-${name.toLowerCase()}`, ...props });
  }
  return exports;
});
