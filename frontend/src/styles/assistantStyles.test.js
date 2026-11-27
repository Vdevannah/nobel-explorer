import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";

// Regression for the Phase 4C bug: collapsed disclosure panels stayed visible
// because `display: grid` on their classes overrode the `hidden` attribute.
// jsdom cannot reproduce that cascade, so the stylesheet itself is checked.
const css = readFileSync(resolve(__dirname, "assistant.css"), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");

function rulesFor(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return [...css.matchAll(new RegExp(`(^|[\\s,}])${escaped}\\s*(,[^{]*)?\\{([^}]*)\\}`, "g"))].map((m) => m[3]);
}

describe("assistant.css", () => {
  it("lets the hidden attribute win inside the assistant page", () => {
    const rules = rulesFor(".assistant-page [hidden]");
    expect(rules.length).toBeGreaterThan(0);
    expect(rules.join(";")).toMatch(/display\s*:\s*none/);
  });

  it.each([".assistant-tools-panel", ".assistant-evidence-list"])(
    "%s sets a display value, so it depends on the [hidden] override (more specific selector)",
    (selector) => {
      expect(rulesFor(selector).join(";")).toMatch(/display\s*:/);
      // ".assistant-page [hidden]" (0,2,0) outranks a single class (0,1,0).
      expect(selector.split(".").length - 1).toBe(1);
    },
  );

  it("stops the welcome illustration's motion for reduced-motion users", () => {
    const reduced = css.slice(css.indexOf("@media (prefers-reduced-motion: reduce)"));
    expect(reduced).toMatch(/\.assistant-atom-orbits,\s*\.assistant-network-node\s*\{\s*animation:\s*none/);
  });

  it("disables the pending animation for reduced-motion users", () => {
    expect(css).toMatch(/@media \(prefers-reduced-motion: reduce\)\s*\{\s*\.assistant-pending-dot\s*\{[^}]*animation:\s*none/);
  });
});
