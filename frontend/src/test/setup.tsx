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

// Mock lucide-react — wrap every real named export so Vitest 4 + new pages stay green
vi.mock("lucide-react", async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  const wrapped: Record<string, unknown> = { ...actual };
  for (const [name, Comp] of Object.entries(actual)) {
    if (typeof Comp === "function") {
      wrapped[name] = (props: any) =>
        React.createElement("span", { "data-testid": `icon-${name.toLowerCase()}`, ...props });
    }
  }
  return wrapped;
});
