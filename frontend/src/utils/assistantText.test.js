import { describe, expect, it } from "vitest";

import { citedEvidenceIds, splitEmphasis, tokenizeAnswer } from "./assistantText";

const citations = (tokens) => tokens.filter((t) => t.type === "citations").map((t) => t.ids);
const markers = (tokens) => tokens.filter((t) => t.type === "marker").map((t) => t.marker);
const plain = (tokens) => tokens.filter((t) => t.type === "text").map((t) => t.value).join("");

describe("tokenizeAnswer", () => {
  it("recognises a single citation", () => {
    expect(tokenizeAnswer("Bertozzi won [E1].")).toEqual([
      { type: "text", value: "Bertozzi won " },
      { type: "citations", ids: ["E1"], raw: "[E1]" },
      { type: "text", value: "." },
    ]);
  });

  it("splits adjacent citations into separate groups", () => {
    expect(citations(tokenizeAnswer("A [E1][E2] B"))).toEqual([["E1"], ["E2"]]);
  });

  it("recognises grouped citations separated by commas or semicolons", () => {
    expect(citations(tokenizeAnswer("[E3, E4; E5]"))).toEqual([["E3", "E4", "E5"]]);
  });

  it("normalises case and whitespace", () => {
    expect(citations(tokenizeAnswer("x [ e3 ] y [e1 ,  E12]"))).toEqual([["E3"], ["E1", "E12"]]);
  });

  it("keeps unknown evidence ids as citation tokens (rendering decides whether they match)", () => {
    expect(citations(tokenizeAnswer("See [E99]."))).toEqual([["E99"]]);
  });

  it("recognises the validation markers case-insensitively", () => {
    expect(markers(tokenizeAnswer("a [unverified] b [Link Removed] c [UNVERIFIED]"))).toEqual([
      "unverified",
      "link_removed",
      "unverified",
    ]);
  });

  it("leaves other bracketed text literal", () => {
    const tokens = tokenizeAnswer("[note] [E] [E1 E2] [1] [E1,] [source](https://x.example)\nnext");
    expect(citations(tokens)).toEqual([]);
    expect(plain(tokens)).toBe("[note] [E] [E1 E2] [1] [E1,] [source](https://x.example)\nnext");
  });

  it("returns hostile HTML as literal text tokens", () => {
    const hostile = '<script>alert(1)</script><img src=x onerror="alert(2)"> [E1]';
    const tokens = tokenizeAnswer(hostile);
    expect(plain(tokens)).toBe('<script>alert(1)</script><img src=x onerror="alert(2)"> ');
    expect(citations(tokens)).toEqual([["E1"]]);
  });

  it("returns no tokens for empty or non-string input", () => {
    for (const value of ["", null, undefined, 42, {}, ["[E1]"]]) {
      expect(tokenizeAnswer(value)).toEqual([]);
    }
  });

  it("is stable across repeated calls (global regex state is reset)", () => {
    expect(tokenizeAnswer("[E1] x")).toEqual(tokenizeAnswer("[E1] x"));
  });
});

describe("citedEvidenceIds", () => {
  it("lists ids in first-appearance order without duplicates", () => {
    expect(citedEvidenceIds("x [E2] y [E1, E2] z [e3]")).toEqual(["E2", "E1", "E3"]);
  });
});

describe("splitEmphasis", () => {
  it("marks well-formed paired double asterisks", () => {
    expect(splitEmphasis("Einstein did **not** receive it.")).toEqual([
      { strong: false, text: "Einstein did " },
      { strong: true, text: "not" },
      { strong: false, text: " receive it." },
    ]);
    expect(splitEmphasis("**a** and **b c**").filter((s) => s.strong).map((s) => s.text)).toEqual(["a", "b c"]);
  });

  it.each([
    "an unmatched ** marker",
    "** spaced **",
    "**leading space**".replace("**l", "** l"),
    "**trailing space **",
    "****",
    "**across\nlines**",
    "single *asterisk* only",
    "**a ** b**",
  ])("keeps malformed emphasis literal: %j", (input) => {
    const segments = splitEmphasis(input);
    expect(segments.every((s) => !s.strong) || segments.some((s) => s.strong && !s.text.includes("**"))).toBe(true);
    expect(segments.map((s) => (s.strong ? `**${s.text}**` : s.text)).join("")).toBe(input);
  });

  it("never bolds across a newline and preserves whitespace exactly", () => {
    const text = "Line **one**\n\n  **two** end";
    expect(splitEmphasis(text).map((s) => (s.strong ? `**${s.text}**` : s.text)).join("")).toBe(text);
    expect(splitEmphasis(text).filter((s) => s.strong).map((s) => s.text)).toEqual(["one", "two"]);
  });

  it("leaves citations to the citation tokenizer, inside or next to emphasis", () => {
    const segments = splitEmphasis("**Karikó [E2]**[E1] and **[E3]**");
    expect(segments).toEqual([
      { strong: true, text: "Karikó [E2]" },
      { strong: false, text: "[E1] and " },
      { strong: true, text: "[E3]" },
    ]);
    expect(segments.flatMap((s) => tokenizeAnswer(s.text)).filter((t) => t.type === "citations").map((t) => t.ids))
      .toEqual([["E2"], ["E1"], ["E3"]]);
  });

  it("treats hostile content and other Markdown as plain text", () => {
    const segments = splitEmphasis("**<script>alert(1)</script>** [x](javascript:alert(1)) ![i](x) # h <b>b</b>");
    expect(segments[0]).toEqual({ strong: true, text: "<script>alert(1)</script>" });
    expect(segments[1].text).toBe(" [x](javascript:alert(1)) ![i](x) # h <b>b</b>");
  });

  it("returns no segments for empty or non-string input", () => {
    for (const value of ["", null, undefined, 3]) expect(splitEmphasis(value)).toEqual([]);
  });
});
