import { describe, expect, it } from "vitest";

import { displayHost, safeExternalUrl } from "./safeUrl";

describe("safeExternalUrl", () => {
  it.each([
    ["https://www.nobelprize.org/prizes/medicine/2023/summary/", "https://www.nobelprize.org/prizes/medicine/2023/summary/"],
    ["http://example.org", "http://example.org/"],
    ["HTTPS://Example.ORG/a?b=c#d", "https://example.org/a?b=c#d"],
    ["https://example.org:8443/path", "https://example.org:8443/path"],
  ])("accepts absolute http(s) URL %s", (input, expected) => {
    expect(safeExternalUrl(input)).toBe(expected);
  });

  it.each([
    "javascript:alert(1)",
    "JaVaScRiPt:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "file:///etc/passwd",
    "blob:https://example.org/123",
    "ftp://example.org/file",
    "mailto:someone@example.org",
    "vbscript:msgbox(1)",
  ])("rejects unsafe scheme %s", (input) => {
    expect(safeExternalUrl(input)).toBeNull();
  });

  it.each(["/laureates/1", "laureates/1", "?q=1", "#top", "//evil.example/x", "https:evil.example", "https:/evil.example"])(
    "rejects relative or protocol-relative URL %s",
    (input) => {
      expect(safeExternalUrl(input)).toBeNull();
    },
  );

  it.each(["https://user:pass@example.org/", "https://user@example.org/", "http://:secret@example.org/"])(
    "rejects embedded credentials in %s",
    (input) => {
      expect(safeExternalUrl(input)).toBeNull();
    },
  );

  it.each([
    "https://exa\nmple.org",
    "https://example.org/\t",
    "https://example.org/\u0000",
    "https://example.org/\u007f",
    "https://example.org/\u0085",
  ])("rejects control characters (%j)", (input) => {
    expect(safeExternalUrl(input)).toBeNull();
  });

  it.each([" https://example.org", "https://exa mple.org", "https:\\\\evil.example", "http://\\evil.example", "https://example.org\\path"])(
    "rejects whitespace and backslashes (%j)",
    (input) => {
      expect(safeExternalUrl(input)).toBeNull();
    },
  );

  it.each(["https://", "http://[::1", "https://exa%mple.org", ""])("rejects malformed URL %j", (input) => {
    expect(safeExternalUrl(input)).toBeNull();
  });

  it.each([null, undefined, 42, true, {}, ["https://example.org"], { toString: () => "https://example.org" }])(
    "rejects non-string value %j",
    (input) => {
      expect(safeExternalUrl(input)).toBeNull();
    },
  );

  it("rejects URLs longer than 2,048 characters", () => {
    const base = "https://example.org/";
    expect(safeExternalUrl(base + "a".repeat(2048 - base.length))).not.toBeNull();
    expect(safeExternalUrl(base + "a".repeat(2049 - base.length))).toBeNull();
  });
});

describe("displayHost", () => {
  it("returns the host of a URL and an empty string for invalid input", () => {
    expect(displayHost("https://www.energy.gov/x")).toBe("www.energy.gov");
    expect(displayHost("not a url")).toBe("");
  });
});
