// ChatResponse fixtures shared by the assistant tests.
// "real-*" fixtures reuse answers, titles, URLs and tool arguments recorded in
// ai_index/agent_eval_openai_stage2_full.json (real gpt-6-luna Stage 2 run);
// fields that file does not record (source names, related_source, ids, latency)
// are filled in and marked SIMULATED. Everything else is synthetic.
const base = (over) => ({
  request_id: "req-internal-request-id", status: "completed", answer: null, grounding: null, citations: [], tool_calls: [],
  evidence_limitations: [], model: "gpt-6-luna", model_calls: 2,
  usage: { input_tokens: 9422, output_tokens: 150, total_tokens: 9572, cached_input_tokens: 5042 },
  latency_ms: 12015.9, error: null, ...over,
});
const NOBEL_SOURCE = "Nobel Prize API v2.1 (imported by Nobel Explorer ETL)"; // SIMULATED name
const tc = (id, name, args, ok, evidence_ids = [], error_type = null) =>
  ({ id, name, arguments: args, ok, error_type, evidence_ids, latency_ms: 97.81 });

export const fixtures = {
  // R04: structured_record + source_linked, cited.
  "real-r04": base({
    grounding: "cited",
    answer: "Katalin Karikó and Drew Weissman shared the 2023 Physiology or Medicine prize [E1][E2]. They discovered that modifying nucleosides in synthetic mRNA can reduce unwanted immune activation, helping cells translate the mRNA into protein and enabling effective mRNA vaccines against COVID-19 [E3].",
    citations: [
      { evidence_id: "E1", tool: "search_laureates", kind: "laureate_record", title: "Drew Weissman", citation_status: "structured_record",
        source: null, source_name: NOBEL_SOURCE, related_source: null, reference: { laureate_id: 1024, nobel_laureate_id: 1025 } },
      { evidence_id: "E2", tool: "search_laureates", kind: "laureate_record", title: "Katalin Karikó", citation_status: "structured_record",
        source: null, source_name: NOBEL_SOURCE, related_source: null, reference: { laureate_id: 1023, nobel_laureate_id: 1024 } },
      { evidence_id: "E3", tool: "search_nobel_knowledge", kind: "knowledge:contribution", title: "Nucleoside Base Modifications and mRNA Vaccines",
        citation_status: "source_linked", source: { name: "The Nobel Prize in Physiology or Medicine 2023 – Summary", url: "https://www.nobelprize.org/prizes/medicine/2023/summary/" },
        source_name: null, related_source: null, reference: { doc_id: "contribution:7", chunk_id: "contribution:7#0", similarity: 0.71, weak_match: false } },
    ],
    tool_calls: [
      tc("call_nUjSPz08f2Paq4fRo7rwsXL9", "search_laureates", { year: 2023, category: "Physiology or Medicine", limit: 10 }, true, ["E1", "E2"]),
      tc("call_internal_tool_call_id", "search_nobel_knowledge", { query: "What did Katalin Karikó and Drew Weissman discover? nucleoside base modifications enabling mRNA vaccines against COVID-19", k: 3 }, true, ["E3", "E4", "E5"]),
    ],
  }),
  // R03: unverified_educational with related source (related_source SIMULATED).
  "real-r03": base({
    grounding: "cited",
    answer: "In Nobel Explorer’s simple explanation, click chemistry is like connecting LEGO pieces: chemists choose molecular building blocks that join together quickly and reliably. Scientists can use these reactions to attach chemical tags to molecules and study what they do in living systems.[E1]",
    citations: [{ evidence_id: "E1", tool: "search_nobel_knowledge", kind: "knowledge:explanation", title: "Click Chemistry and Bioorthogonal Chemistry - Simple explanation",
      citation_status: "unverified_educational", source: null, source_name: null,
      related_source: { name: "The Nobel Prize in Chemistry 2022 – Summary", url: "https://www.nobelprize.org/prizes/chemistry/2022/summary/" },
      reference: { doc_id: "explanation:3:Simple", chunk_id: "explanation:3:Simple#0", similarity: 0.62, weak_match: false } }],
    evidence_limitations: ["Cited explanations are unverified educational content without stored citations; related sources are context only."],
    tool_calls: [tc("call_r03", "search_nobel_knowledge", { query: "Explain click chemistry in simple terms.", level: "Simple", k: 5, dedupe_by_document: true }, true, ["E1", "E2", "E3"])],
  }),
  // R05: statistic (title is the operation name).
  "real-r05": base({
    grounding: "cited",
    answer: "The top three birth countries are the USA, with 296 distinct person laureates; the United Kingdom, with 94; and Germany, with 80. [E1]",
    citations: [{ evidence_id: "E1", tool: "get_nobel_statistics", kind: "statistic", title: "top_birth_countries", citation_status: "structured_record",
      source: null, source_name: "Nobel Explorer database", related_source: null,
      reference: { operation: "top_birth_countries", applied_filters: { limit: 3 }, counting_unit: "distinct_person_laureates" } }],
    tool_calls: [tc("call_r05", "get_nobel_statistics", { operation: "top_birth_countries", limit: 3 }, true, ["E1"])],
  }),
  // R07: source_linked connection.
  "real-r07": base({
    grounding: "cited",
    answer: "Solar cells use semiconductor materials to turn light into electrical current. Photons absorbed by the semiconductor generate mobile charge carriers—electrons and “holes.” The cell’s structure separates and collects these charges, making them flow through an external circuit as electric current. [E1]\n\nThis is related to light-to-electricity physics, but it is not simply the same as light knocking electrons out of a metal in the photoelectric effect. [E1]",
    citations: [{ evidence_id: "E1", tool: "search_nobel_knowledge", kind: "knowledge:connection", title: "Photoelectric Effect - Solar Panels / Photovoltaic Technology",
      citation_status: "source_linked", source: { name: "Solar Photovoltaic Cell Basics", url: "https://www.energy.gov/cmei/systems/solar-photovoltaic-cell-basics" },
      source_name: null, related_source: null, reference: { doc_id: "connection:4", chunk_id: "connection:4#0", similarity: 0.58, weak_match: false } }],
    tool_calls: [tc("call_r07", "search_nobel_knowledge", { query: "Explain how solar cells convert sunlight into electricity", level: null, k: 5, dedupe_by_document: true }, true, ["E1", "E2"])],
  }),
  // R06: correct abstention, no_evidence, failed tool call.
  "real-r06": base({
    grounding: "no_evidence",
    answer: "There is no Nobel Prize in Mathematics, so no one won it in 1950. The Nobel Prize categories are Chemistry, Economic Sciences, Literature, Peace, Physics, and Physiology or Medicine.",
    evidence_limitations: ["Some tool calls failed: search_laureates: validation_error.", "No tool evidence was retrieved; the answer is not grounded in Nobel Explorer data."],
    tool_calls: [tc("call_r06", "search_laureates", { year: 1950, category: "Mathematics", limit: 10 }, false, [], "validation_error")],
  }),
  // R09: uncited.
  "real-r09": base({
    grounding: "uncited",
    answer: "Nobel Explorer has no reliable evidence about sourdough fermentation; its search returned only weakly related material.",
    evidence_limitations: ["Semantic search returned only weak matches (similarity below the provisional 0.40 threshold) for: Explain sourdough fermentation. Treat this as insufficient evidence.", "The answer does not cite any retrieved evidence."],
    tool_calls: [tc("call_r09", "search_nobel_knowledge", { query: "Explain sourdough fermentation", k: 5, dedupe_by_document: true }, true, ["E1", "E2"])],
  }),
  // SYNTHETIC: partially cited with markers and a duplicated limitation.
  "partial": base({
    grounding: "partially_cited",
    answer: "Katalin Karikó and Drew Weissman shared the 2023 prize [E1][E2]. Karikó was born in Hungary [unverified]. Read more at [link removed].",
    citations: [
      { evidence_id: "E1", tool: "search_laureates", kind: "laureate_record", title: "Drew Weissman", citation_status: "structured_record", source: null, source_name: NOBEL_SOURCE, related_source: null, reference: { laureate_id: 1024 } },
      { evidence_id: "E2", tool: "search_laureates", kind: "laureate_record", title: "Katalin Karikó", citation_status: "structured_record", source: null, source_name: NOBEL_SOURCE, related_source: null, reference: { laureate_id: 1023 } },
    ],
    evidence_limitations: [
      "Removed citation references not backed by tool evidence: E7. Statements marked [unverified] are not supported by retrieved evidence.",
      "Removed 1 URL(s) that no tool returned (shown as [link removed]).",
      "Removed 1 URL(s) that no tool returned (shown as [link removed]).",
      "  ", 42, null,
    ],
    tool_calls: [tc("call_p", "search_laureates", { year: 2023, category: "Physiology or Medicine" }, true, ["E1", "E2"])],
  }),
  // SYNTHETIC: malformed / hostile provenance and tool records.
  "malformed": base({
    grounding: "mystery_value",
    answer: "Alpha [E1] beta [E2] gamma [E3] delta [E4] epsilon [E5] zeta [E6] eta [E9]. https://evil.example/phish javascript:alert(1)",
    citations: [
      { evidence_id: "E1", tool: "search_nobel_knowledge", kind: "knowledge:contribution", title: "Unknown status record", citation_status: "mystery", source: { name: "Should not link", url: "https://example.org/x" }, reference: { laureate_id: "12" } },
      { evidence_id: "E1", tool: "x", kind: "x", title: "DUPLICATE E1 SHOULD NOT RENDER", citation_status: "structured_record", reference: {} },
      { evidence_id: "E2", title: "JS link", citation_status: "source_linked", source: { name: "Script source", url: "javascript:alert(document.cookie)" }, reference: { laureate_id: -4 } },
      { evidence_id: "E3", title: "Credential link", citation_status: "source_linked", source: { name: "Cred source", url: "https://user:pass@example.org/" }, reference: { laureate_id: 1.5 } },
      { evidence_id: "E4", title: "Protocol relative", citation_status: "source_linked", source: { name: "PR source", url: "//evil.example/x" }, reference: null },
      { evidence_id: "E5", title: "<img src=x onerror=alert(1)>" + "Very long title ".repeat(20), citation_status: "source_linked",
        source: { name: "Long URL source", url: "https://www.example.org/" + "very-long-path-segment/".repeat(12) + "?q=" + "x".repeat(80) }, reference: { laureate_id: 2 } },
      { evidence_id: "E6", title: "Missing status", reference: { laureate_id: 3000000000 } },
      { evidence_id: "bad id\"><script>", title: "BAD ID SHOULD NOT RENDER", citation_status: "structured_record" },
      "not an object", null,
    ],
    tool_calls: [
      tc("call_internal_A", "search_laureates", { name: "Curie", api_key: "FAKE-CREDENTIAL-PLACEHOLDER", laureate_id: 6, nested: { a: 1 }, limit: 5, extra: "HIDDEN_EXTRA" }, true, ["E1", "bogus"]),
      tc("call_internal_B", "rm_rf_tool", { query: "UNKNOWN TOOL QUERY SHOULD NOT SHOW" }, false, [], "unknown_tool"),
      tc("call_internal_C", "get_laureate_details", { laureate_id: 6, include_explanation_level: "Simple" }, false, [], "internal_error"),
      tc("call_internal_D", "get_nobel_statistics", { operation: "DROP TABLE", category: ["Physics"], start_year: 1901 }, false, [], "tool_budget_exceeded"),
      "junk",
    ],
  }),
  "budget": base({
    status: "budget_exhausted", grounding: null,
    answer: "I could not complete this request within the configured model-call limit. Please try a narrower question.",
    evidence_limitations: ["The model-call limit was reached before a final answer was produced."],
    error: { type: "model_call_limit", message: "The configured model-call limit was reached." },
    tool_calls: [tc("call_b", "search_laureates", { name: "Einstein" }, true, ["E1"])],
  }),
  "hostile": base({
    grounding: "cited",
    answer: "<script>window.__xss=1</script><img src=x onerror=\"window.__xss=2\"> [click](javascript:window.__xss=3) https://evil.example **bold** [E1]",
    citations: [{ evidence_id: "E1", tool: "search_laureates", kind: "laureate_record", title: "</button><script>window.__xss=4</script>", citation_status: "structured_record",
      source: null, source_name: "<b>bold source</b>", related_source: null, reference: { laureate_id: 6 } }],
  }),
};

// REPLAYED real-model responses (Phase 4D.2, gpt-6-luna, prompt 2026-11-26.3), sanitized:
// request and tool-call ids replaced. Used as regression fixtures; not new model executions.
export const replayedFixtures = {
  "replayed-p4-r03": {
    "request_id": "replayed-fixture",
    "status": "completed",
    "answer": "The 2023 Nobel Prize in Physiology or Medicine was shared by Katalin Karikó and Drew Weissman [E1][E2]. They discovered that modifying nucleosides in synthetic mRNA reduces unwanted immune activation, helping make effective mRNA vaccines against COVID-19 possible [E4][E9].",
    "grounding": "cited",
    "citations": [
      {
        "evidence_id": "E1",
        "tool": "search_laureates",
        "kind": "laureate_record",
        "title": "Drew Weissman",
        "citation_status": "structured_record",
        "source": null,
        "source_name": "Nobel Prize API v2.1 (imported by Nobel Explorer ETL)",
        "related_source": null,
        "reference": {
          "laureate_id": 428,
          "nobel_laureate_id": "1025"
        }
      },
      {
        "evidence_id": "E2",
        "tool": "search_laureates",
        "kind": "laureate_record",
        "title": "Katalin Karikó",
        "citation_status": "structured_record",
        "source": null,
        "source_name": "Nobel Prize API v2.1 (imported by Nobel Explorer ETL)",
        "related_source": null,
        "reference": {
          "laureate_id": 774,
          "nobel_laureate_id": "1024"
        }
      },
      {
        "evidence_id": "E4",
        "tool": "get_laureate_details",
        "kind": "contribution",
        "title": "Nucleoside Base Modifications and mRNA Vaccines",
        "citation_status": "source_linked",
        "source": {
          "name": "NobelPrize.org",
          "url": "https://www.nobelprize.org/prizes/medicine/2023/summary/"
        },
        "source_name": null,
        "related_source": null,
        "reference": {
          "contribution_id": 609
        }
      },
      {
        "evidence_id": "E9",
        "tool": "get_laureate_details",
        "kind": "contribution",
        "title": "Nucleoside Base Modifications and mRNA Vaccines",
        "citation_status": "source_linked",
        "source": {
          "name": "NobelPrize.org",
          "url": "https://www.nobelprize.org/prizes/medicine/2023/summary/"
        },
        "source_name": null,
        "related_source": null,
        "reference": {
          "contribution_id": 609
        }
      }
    ],
    "tool_calls": [
      {
        "name": "search_laureates",
        "arguments": {
          "year": 2023,
          "category": "Physiology or Medicine",
          "limit": 5
        },
        "ok": true,
        "error_type": null,
        "evidence_ids": [
          "E1",
          "E2"
        ],
        "latency_ms": 85.65,
        "id": "call_replayed_0"
      },
      {
        "name": "get_laureate_details",
        "arguments": {
          "laureate_id": 428
        },
        "ok": true,
        "error_type": null,
        "evidence_ids": [
          "E3",
          "E4",
          "E5",
          "E6",
          "E7"
        ],
        "latency_ms": 66.93,
        "id": "call_replayed_1"
      },
      {
        "name": "get_laureate_details",
        "arguments": {
          "laureate_id": 774
        },
        "ok": true,
        "error_type": null,
        "evidence_ids": [
          "E8",
          "E9",
          "E10",
          "E11",
          "E12"
        ],
        "latency_ms": 68.08,
        "id": "call_replayed_2"
      }
    ],
    "evidence_limitations": [],
    "model": "gpt-6-luna",
    "model_calls": 3,
    "usage": {
      "input_tokens": 10387,
      "output_tokens": 158,
      "total_tokens": 10545,
      "cached_input_tokens": 5136
    },
    "latency_ms": 6112,
    "error": null
  },
  "replayed-p4-r09": {
    "request_id": "replayed-fixture",
    "status": "completed",
    "answer": "Einstein did **not** receive the Nobel Prize for relativity. His 1921 Physics Prize recognized his contributions to theoretical physics, especially his discovery of the law of the photoelectric effect [E1]. Nobel Explorer’s record specifically distinguishes that work from general relativity, which was not the work cited for the prize [E2].",
    "grounding": "cited",
    "citations": [
      {
        "evidence_id": "E1",
        "tool": "search_laureates",
        "kind": "laureate_record",
        "title": "Albert Einstein",
        "citation_status": "structured_record",
        "source": null,
        "source_name": "Nobel Prize API v2.1 (imported by Nobel Explorer ETL)",
        "related_source": null,
        "reference": {
          "laureate_id": 249,
          "nobel_laureate_id": "26"
        }
      },
      {
        "evidence_id": "E2",
        "tool": "search_nobel_knowledge",
        "kind": "knowledge:contribution",
        "title": "Photoelectric Effect",
        "citation_status": "source_linked",
        "source": {
          "name": "NobelPrize.org",
          "url": "https://www.nobelprize.org/prizes/physics/1921/summary/"
        },
        "source_name": null,
        "related_source": null,
        "reference": {
          "doc_id": "contribution:38",
          "chunk_id": "contribution:38#c0",
          "similarity": 0.8284,
          "weak_match": false
        }
      }
    ],
    "tool_calls": [
      {
        "name": "search_laureates",
        "arguments": {
          "name": "Einstein",
          "limit": 10
        },
        "ok": true,
        "error_type": null,
        "evidence_ids": [
          "E1"
        ],
        "latency_ms": 61.41,
        "id": "call_replayed_0"
      },
      {
        "name": "search_nobel_knowledge",
        "arguments": {
          "query": "Why did Albert Einstein win the Nobel Prize for relativity? Explain official motivation photoelectric effect and relation to relativity",
          "laureate_id": 249,
          "k": 5
        },
        "ok": true,
        "error_type": null,
        "evidence_ids": [
          "E2",
          "E3",
          "E4",
          "E5",
          "E6"
        ],
        "latency_ms": 27.83,
        "id": "call_replayed_1"
      }
    ],
    "evidence_limitations": [],
    "model": "gpt-6-luna",
    "model_calls": 3,
    "usage": {
      "input_tokens": 9176,
      "output_tokens": 148,
      "total_tokens": 9324,
      "cached_input_tokens": 7043
    },
    "latency_ms": 3487.9,
    "error": null
  }
};
