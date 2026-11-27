import { describe, expect, it } from "vitest";

import { fixtures, replayedFixtures } from "../test/chatResponses";
import {
  CITATION_DISCLAIMER,
  describeGrounding,
  friendlyLimitation,
  friendlyLimitations,
  GENERIC_LIMITATION,
  groupEvidence,
  knowledgeKind,
  looksLikeAbstention,
  laureateIdOf,
  normalizeCitations,
  normalizeToolCalls,
  safeToolArguments,
  uniqueLimitations,
} from "./assistantEvidence";

const PROTOTYPE_KEYS = ["__proto__", "constructor", "toString", "hasOwnProperty", "valueOf"];

describe("normalizeCitations", () => {
  it("classifies each provenance and keeps only the fields that belong to it", () => {
    const [weissman, , source] = normalizeCitations(fixtures["real-r04"].citations);
    expect(weissman).toMatchObject({
      id: "E1",
      title: "Drew Weissman",
      provenance: { key: "structured_record", label: "Nobel Explorer database record" },
      sourceName: "Nobel Prize API v2.1 (imported by Nobel Explorer ETL)",
      source: null,
      laureateId: 1024,
    });
    expect(source).toMatchObject({
      provenance: { key: "source_linked", label: "Linked source" },
      sourceName: "",
      source: { name: "The Nobel Prize in Physiology or Medicine 2023 – Summary", url: "https://www.nobelprize.org/prizes/medicine/2023/summary/" },
      laureateId: null,
    });

    const [explanation] = normalizeCitations(fixtures["real-r03"].citations);
    expect(explanation).toMatchObject({
      provenance: { key: "unverified_educational", label: "Educational explanation" },
      relatedSourceName: "The Nobel Prize in Chemistry 2022 – Summary",
      source: null,
    });
    expect(JSON.stringify(explanation)).not.toContain("nobelprize.org/prizes/chemistry");
  });

  it("treats missing, unknown and prototype-key statuses as unknown provenance without links", () => {
    const cards = normalizeCitations([
      { evidence_id: "E1", title: "a", citation_status: "mystery", source: { name: "x", url: "https://example.org" } },
      { evidence_id: "E2", title: "b" },
      ...PROTOTYPE_KEYS.map((status, i) => ({ evidence_id: `E${i + 3}`, title: "c", citation_status: status })),
    ]);
    expect(cards.map((c) => c.provenance.key)).toEqual(Array(cards.length).fill("unknown"));
    expect(cards.every((c) => c.source === null && c.provenance.label === "Source not specified")).toBe(true);
  });

  it("keeps the first record for duplicate ids and drops malformed records", () => {
    const cards = normalizeCitations(fixtures.malformed.citations);
    expect(cards.map((c) => c.id)).toEqual(["E1", "E2", "E3", "E4", "E5", "E6"]);
    expect(cards.map((c) => c.title)).not.toContain("DUPLICATE E1 SHOULD NOT RENDER");
    expect(cards.map((c) => c.title)).not.toContain("BAD ID SHOULD NOT RENDER");
  });

  it("drops unsafe source URLs but keeps the source name", () => {
    const cards = normalizeCitations(fixtures.malformed.citations);
    expect(cards[1].source).toEqual({ name: "Script source", url: null });
    expect(cards[2].source).toEqual({ name: "Cred source", url: null });
    expect(cards[3].source).toEqual({ name: "PR source", url: null });
    expect(cards[4].source.url).toMatch(/^https:\/\/www\.example\.org\//);
  });

  it("uppercases ids, supplies a fallback title and gives statistics readable titles", () => {
    expect(normalizeCitations([{ evidence_id: " e7 ", citation_status: "structured_record" }])[0]).toMatchObject({
      id: "E7",
      title: "Untitled evidence",
    });
    expect(normalizeCitations(fixtures["real-r05"].citations)[0].title).toBe("Top birth countries of laureates");
    expect(normalizeCitations([{ evidence_id: "E1", kind: "statistic", title: "constructor" }])[0].title).toBe("constructor");
  });

  it.each([null, undefined, "x", 5, {}])("returns [] for %j", (value) => {
    expect(normalizeCitations(value)).toEqual([]);
  });
});

describe("laureateIdOf", () => {
  it.each([
    [{ laureate_id: 6 }, 6],
    [{ laureate_id: 2_000_000_000 }, 2_000_000_000],
    [{ laureate_id: 2_000_000_001 }, null],
    [{ laureate_id: 0 }, null],
    [{ laureate_id: -4 }, null],
    [{ laureate_id: 1.5 }, null],
    [{ laureate_id: "12" }, null],
    [{ laureate_id: true }, null],
    [{}, null],
    [null, null],
    [[6], null],
  ])("%j -> %j", (reference, expected) => {
    expect(laureateIdOf(reference)).toBe(expected);
  });
});

describe("limitations", () => {
  it("trims, de-duplicates and drops non-string entries", () => {
    expect(uniqueLimitations(fixtures.partial.evidence_limitations)).toHaveLength(2);
    expect(uniqueLimitations(undefined)).toEqual([]);
    expect(uniqueLimitations(["  a ", "a", "", null, 3])).toEqual(["a"]);
  });

  it.each([
    ["Some tool calls failed: search_laureates: validation_error.",
      ["Laureate search did not complete: the requested search parameters could not be processed."]],
    ["Some tool calls failed: search_nobel_knowledge: index_unavailable; get_laureate_details: internal_error.",
      ["Knowledge search did not complete: the knowledge search was unavailable.",
        "Laureate details lookup did not complete: an unexpected problem occurred."]],
    ["Some tool calls failed: rm_rf: unknown_tool; tool-call budget reached; some requested calls were not executed.",
      ["The tool-call limit was reached, so some requested lookups were not run.",
        "A requested lookup did not complete: the assistant asked for a tool that does not exist."]],
    ["Semantic search returned only weak matches (similarity below the provisional 0.40 threshold) for: Explain sourdough fermentation. Treat this as insufficient evidence.",
      ["The available Nobel Explorer content may not closely match this question, so it was treated as insufficient evidence."]],
    ["No matching records: search_laureates found no matching laureates.",
      ["No matching laureates were found in Nobel Explorer's records."]],
    ["No matching records: get_nobel_statistics(summary) returned no data; search_nobel_knowledge returned no results.",
      ["The requested statistic returned no data.", "No related educational or scientific content was found."]],
    ["A name matched several laureates ('Curie' matched 4 laureates); the answer may need clarification.",
      ['The name "Curie" matched 4 laureates, so the answer may need clarification.']],
    ["Results were truncated: search_laureates returned 10 of 25 matches.", ["Only some of the matching records were used (10 of 25)."]],
    ["No educational explanations are stored for Marie Curie.", ["Nobel Explorer has no detailed educational explanations for Marie Curie."]],
    ["Cited explanations are unverified educational content without stored citations; related sources are context only.",
      ["Educational explanations are Nobel Explorer's own teaching content and have no stored external citation. Related sources are shown for context only."]],
    ["Removed citation references not backed by tool evidence: E7. Statements marked [unverified] are not supported by retrieved evidence.",
      ["Some citation references did not match the retrieved evidence and were removed. Statements marked [unverified] are not supported by the evidence found."]],
    ["Removed 2 URL(s) that no tool returned (shown as [link removed]).",
      ["Links that did not come from Nobel Explorer's records were removed (shown as [link removed])."]],
    ["Removed related-source URL(s) presented as citations; they are context only.",
      ["Related-source links were removed from the answer because they provide context only, not direct evidence."]],
    ["No tool evidence was retrieved; the answer is not grounded in Nobel Explorer data.",
      ["No supporting evidence was retrieved, so this answer is not based on Nobel Explorer data."]],
    ["The answer does not cite any retrieved evidence.", ["The answer does not reference any of the evidence that was retrieved."]],
    ["The request time limit was reached before an answer was produced.", ["The time limit was reached before a complete answer was produced."]],
    ["The model-call limit was reached before a final answer was produced.", ["The assistant reached a processing limit before producing a final answer."]],
  ])("translates backend template %j", (raw, expected) => {
    expect(friendlyLimitation(raw)).toEqual(expected);
  });

  it("shows unknown plain-prose limitations verbatim", () => {
    expect(friendlyLimitation("Coverage is limited for early prizes.")).toEqual(["Coverage is limited for early prizes."]);
  });

  it.each([
    "Traceback (most recent call last): File x",
    "OperationalError: (2003) Can't connect",
    "raw search_laureates payload",
    "see https://internal.example/log",
    "{\"type\": \"database_error\"}",
    `token ${"sk"}-${"abcdef0123456789"}`, // built at runtime so secret scanners do not flag test data
    "x".repeat(301),
  ])("replaces diagnostic-looking unknown limitation %j with a generic notice", (raw) => {
    expect(friendlyLimitation(raw)).toEqual([GENERIC_LIMITATION]);
  });

  it("de-duplicates after translation and preserves order", () => {
    expect(friendlyLimitations([
      "The answer does not cite any retrieved evidence.",
      "Removed 1 URL(s) that no tool returned (shown as [link removed]).",
      "Removed 3 URL(s) that no tool returned (shown as [link removed]).",
      "  ",
      null,
    ])).toEqual([
      "The answer does not reference any of the evidence that was retrieved.",
      "Links that did not come from Nobel Explorer's records were removed (shown as [link removed]).",
    ]);
  });
});

describe("describeGrounding", () => {
  it.each([
    ["cited", "Includes evidence references", "info"],
    ["partially_cited", "Some references could not be validated", "warning"],
    ["uncited", "No evidence references provided", "warning"],
    ["no_evidence", "No supporting evidence retrieved", "neutral"],
  ])("%s -> %s", (value, label, tone) => {
    expect(describeGrounding(value)).toMatchObject({ label, tone });
  });

  it.each([null, undefined, "", "mystery", ...PROTOTYPE_KEYS])("does not classify %j", (value) => {
    expect(describeGrounding(value)).toBeNull();
  });

  it("never uses overclaiming wording", () => {
    const all = JSON.stringify(["cited", "partially_cited", "uncited", "no_evidence"].map(describeGrounding)) + CITATION_DISCLAIMER;
    expect(all).not.toMatch(/fully grounded|verified answer|100%|confiden/i);
  });
});

describe("tool activity", () => {
  it("shows only allow-listed arguments with readable labels", () => {
    expect(safeToolArguments({
      name: "Curie", api_key: "FAKE-CREDENTIAL-PLACEHOLDER", laureate_id: 6, nested: { a: 1 }, limit: 5, k: 3, extra: "x",
    })).toEqual([{ key: "name", label: "Name", value: "Curie" }]);
    expect(safeToolArguments({ year: 2023, category: "Physiology or Medicine", birth_country: "USA", gender: "female" }).map((a) => a.label))
      .toEqual(["Year", "Category", "Birth country", "Gender"]);
  });

  it("drops non-primitive values, unknown operations and prototype keys; truncates long text", () => {
    expect(safeToolArguments({ category: ["Physics"], year: { $gt: 1 }, operation: "DROP TABLE" })).toEqual([]);
    expect(safeToolArguments({ operation: "__proto__" })).toEqual([]);
    expect(safeToolArguments({ operation: "top_birth_countries" })[0].value).toBe("Top birth countries of laureates");
    const long = safeToolArguments({ query: "q".repeat(500) })[0].value;
    expect(long).toHaveLength(160);
    expect(long.endsWith("…")).toBe(true);
    for (const value of [null, undefined, "x", []]) expect(safeToolArguments(value)).toEqual([]);
  });

  it("maps tools to friendly names, statuses and evidence counts without internal fields", () => {
    const calls = normalizeToolCalls(fixtures.malformed.tool_calls);
    expect(calls.map((c) => c.label)).toEqual([
      "Search Nobel laureates", "Unrecognized tool", "Retrieve laureate details", "Analyze Nobel Prize statistics",
    ]);
    expect(calls.map((c) => c.statusText)).toEqual([
      "Completed", "Did not complete", "Did not complete", "Not run: the tool-call limit was reached",
    ]);
    expect(calls[0].evidenceCount).toBe(1);
    expect(calls[1].arguments).toEqual([]);
    expect(calls[2].evidenceCount).toBeNull();
    expect(JSON.stringify(calls)).not.toMatch(/call_|FAKE-CREDENTIAL|HIDDEN|latency|internal_error|unknown_tool|rm_rf_tool/);
  });

  it("describes each of the four tools", () => {
    const names = ["search_laureates", "get_laureate_details", "get_nobel_statistics", "search_nobel_knowledge"];
    const calls = normalizeToolCalls(names.map((name) => ({ name, ok: true, arguments: {}, evidence_ids: [] })));
    expect(calls.map((c) => c.label)).toEqual([
      "Search Nobel laureates", "Retrieve laureate details", "Analyze Nobel Prize statistics", "Search scientific knowledge",
    ]);
    expect(calls.every((c) => c.description.length > 20)).toBe(true);
  });

  it.each([
    ["validation_error", "Not run: the search parameters were not accepted"],
    ["not_found", "No matching record was found"],
    ["deadline_exceeded", "Stopped: the time limit was reached"],
    ["database_error", "Did not complete"],
    ["__proto__", "Did not complete"],
  ])("failure %s -> %s", (errorType, text) => {
    expect(normalizeToolCalls([{ name: "search_laureates", ok: false, error_type: errorType }])[0].statusText).toBe(text);
  });

  it("treats prototype-key tool names as unrecognized", () => {
    for (const name of PROTOTYPE_KEYS) {
      expect(normalizeToolCalls([{ name, ok: true, arguments: { query: "x" } }])[0]).toMatchObject({
        label: "Unrecognized tool", arguments: [],
      });
    }
  });

  it.each([null, undefined, {}, "x"])("returns [] for %j", (value) => {
    expect(normalizeToolCalls(value)).toEqual([]);
  });
});

describe("groupEvidence", () => {
  const contribution = (id, over = {}) => ({
    evidence_id: id, tool: "get_laureate_details", kind: "contribution", title: "Nucleoside Base Modifications and mRNA Vaccines",
    citation_status: "source_linked", source: { name: "NobelPrize.org", url: "https://www.nobelprize.org/prizes/medicine/2023/summary/" },
    reference: { contribution_id: 609 }, ...over,
  });
  const groupsOf = (citations) => groupEvidence(normalizeCitations(citations)).map((g) => g.ids);

  it("groups the real P4-R03 duplicate (E4 and E9, contribution 609) and keeps every id", () => {
    const groups = groupEvidence(normalizeCitations(replayedFixtures["replayed-p4-r03"].citations));
    expect(groups.map((g) => g.ids)).toEqual([["E1"], ["E2"], ["E4", "E9"]]);
    expect(groups[2]).toMatchObject({ id: "E4", provenance: { key: "source_linked" }, title: "Nucleoside Base Modifications and mRNA Vaccines" });
  });

  it("does not group records that only share a title", () => {
    expect(groupsOf([contribution("E1"), contribution("E2", { reference: { contribution_id: 610 } })])).toEqual([["E1"], ["E2"]]);
  });

  it("does not group records that only share a URL", () => {
    expect(groupsOf([
      contribution("E1"),
      contribution("E2", { title: "Another contribution", reference: { contribution_id: 611 } }),
    ])).toEqual([["E1"], ["E2"]]);
  });

  it("does not merge different provenance, even with the same identity", () => {
    expect(groupsOf([contribution("E1"), contribution("E2", { citation_status: "unverified_educational", source: null })]))
      .toEqual([["E1"], ["E2"]]);
  });

  it("does not merge the same identity returned by a different tool or kind", () => {
    expect(groupsOf([contribution("E1"), contribution("E2", { tool: "search_nobel_knowledge" })])).toEqual([["E1"], ["E2"]]);
    expect(groupsOf([contribution("E1"), contribution("E2", { kind: "connection" })])).toEqual([["E1"], ["E2"]]);
  });

  it("does not merge records whose source differs", () => {
    expect(groupsOf([contribution("E1"), contribution("E2", { source: { name: "Other", url: "https://example.org/" } })]))
      .toEqual([["E1"], ["E2"]]);
  });

  it.each([
    ["missing reference", { reference: undefined }],
    ["empty reference", { reference: {} }],
    ["null id", { reference: { contribution_id: null } }],
    ["unknown kind", { kind: "mystery" }],
    ["prototype-key kind", { kind: "__proto__" }],
    ["missing tool", { tool: undefined }],
  ])("keeps separate cards when identity cannot be established (%s)", (_name, over) => {
    expect(groupsOf([contribution("E1", over), contribution("E2", over)])).toEqual([["E1"], ["E2"]]);
  });

  it("groups knowledge chunks only on the same document and chunk", () => {
    const chunk = (id, chunkId) => ({ evidence_id: id, tool: "search_nobel_knowledge", kind: "knowledge:connection", title: "T",
      citation_status: "source_linked", source: { name: "DOE", url: "https://www.energy.gov/x" }, reference: { doc_id: "connection:24", chunk_id: chunkId, similarity: 0.5 } });
    expect(groupsOf([chunk("E1", "connection:24#c0"), chunk("E2", "connection:24#c0"), chunk("E3", "connection:24#c1")]))
      .toEqual([["E1", "E2"], ["E3"]]);
  });

  it("groups identical statistics regardless of filter key order", () => {
    const stat = (id, filters) => ({ evidence_id: id, tool: "get_nobel_statistics", kind: "statistic", title: "summary",
      citation_status: "structured_record", source_name: "DB", reference: { operation: "summary", applied_filters: filters, counting_unit: "mixed" } });
    expect(groupsOf([stat("E1", { a: 1, b: 2 }), stat("E2", { b: 2, a: 1 }), stat("E3", { a: 2 })])).toEqual([["E1", "E2"], ["E3"]]);
  });

  it.each([null, undefined, "x"])("returns [] for %j", (value) => {
    expect(groupEvidence(value)).toEqual([]);
  });
});

describe("general-knowledge classification", () => {
  it.each([
    "Nobel Explorer’s database only covers prizes awarded through 2025, so it has no information on who won the 2026 Chemistry Prize.",
    "Nobel Explorer has no reliable evidence about sourdough fermentation; its search returned only weakly related material.",
    "Nobel Explorer’s knowledge base doesn’t contain a relevant explanation of that, so I can’t explain it from the available evidence.",
    "That question is outside the scope of Nobel Explorer.",
    "I cannot answer questions about current events.",
  ])("recognises abstention %#", (answer) => {
    expect(looksLikeAbstention(answer)).toBe(true);
    expect(knowledgeKind(answer, "no_evidence")).toBeNull();
  });

  it.each([
    ["There is no Nobel Prize in Mathematics. The six categories are Chemistry, Economic Sciences, Literature, Peace, Physics and Physiology or Medicine.", "no_evidence"],
    ["Photosynthesis converts light energy into chemical energy stored in sugars.", "uncited"],
  ])("marks an uncited non-abstention answer as general (%#)", (answer, grounding) => {
    expect(knowledgeKind(answer, grounding)).toBe("general");
  });

  it("detects a mixed answer only when a substantial paragraph has no citation", () => {
    const cited = "Karikó and Weissman shared the 2023 prize [E1][E2].";
    expect(knowledgeKind(`${cited}\n\nVaccines train the immune system to recognise a pathogen safely.`, "cited")).toBe("mixed");
    expect(knowledgeKind(`${cited} They modified nucleosides [E4].`, "cited")).toBeNull();
    expect(knowledgeKind(`${cited}\n\nShort aside.`, "cited")).toBeNull();
    expect(knowledgeKind(`First paragraph cites [E1].\n\nSecond paragraph also cites evidence here [E2].`, "cited")).toBeNull();
  });

  it.each([[null, "uncited"], ["", "no_evidence"], ["Some answer text that is long enough.", null], ["Some answer text.", "mystery"]])(
    "returns null for %j / %j", (answer, grounding) => {
      expect(knowledgeKind(answer, grounding)).toBeNull();
    },
  );
});
