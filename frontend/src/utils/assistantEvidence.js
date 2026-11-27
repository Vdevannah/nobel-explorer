// Pure helpers that turn a ChatResponse into display-ready data. Every
// function tolerates missing or malformed fields and never throws.
// Field names follow backend/ai/agent/schemas.py (Citation, ToolCallSummary).

import { tokenizeAnswer } from "./assistantText";
import { safeExternalUrl } from "./safeUrl";

const EVIDENCE_ID = /^E\d{1,6}$/;
const MAX_LAUREATE_ID = 2_000_000_000; // backend PositiveId upper bound

export const EXTENDED_WAIT_SECONDS = 8;
export const EXTENDED_WAIT_MESSAGE =
  "Some questions take longer while the research engine initializes or retrieves additional information.";

const isObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
// Own-property lookup so backend or model strings such as "__proto__" or
// "toString" never resolve to Object.prototype members.
const lookup = (table, key) => (typeof key === "string" && Object.hasOwn(table, key) ? table[key] : undefined);
const text = (value) => (typeof value === "string" ? value.trim() : "");

// --------------------------------------------------------------- citations

const PROVENANCE = {
  structured_record: { key: "structured_record", label: "Nobel Explorer database record" },
  source_linked: { key: "source_linked", label: "Linked source" },
  // Neutral label; the card and the Sources notice still state that there is no stored external citation.
  unverified_educational: { key: "unverified_educational", label: "Educational explanation" },
};
const UNKNOWN_PROVENANCE = { key: "unknown", label: "Source not specified" };

const STATISTIC_TITLES = {
  summary: "Nobel Prize summary statistics",
  laureates_by_category: "Laureates by category",
  laureates_by_gender: "Laureates by gender",
  prizes_by_decade: "Prizes by decade",
  laureates_by_decade: "Laureates by decade",
  top_birth_countries: "Top birth countries of laureates",
  women_by_era: "Women laureates by era",
  average_age_at_award: "Average age at award",
  laureates_by_affiliation_institution: "Laureates by affiliated institution",
};

export function laureateIdOf(reference) {
  if (!isObject(reference)) return null;
  const id = reference.laureate_id;
  return Number.isSafeInteger(id) && id > 0 && id <= MAX_LAUREATE_ID ? id : null;
}

function sourceRef(value) {
  if (!isObject(value)) return null;
  const name = text(value.name);
  const url = safeExternalUrl(value.url);
  if (!name && !url) return null;
  return { name, url };
}

/**
 * Validates, de-duplicates (first record wins) and normalises citations.
 * Records without a well-formed evidence id are dropped because they cannot be
 * referenced from the answer or given a safe DOM id.
 */
export function normalizeCitations(citations) {
  if (!Array.isArray(citations)) return [];
  const seen = new Set();
  const result = [];
  for (const raw of citations) {
    if (!isObject(raw)) continue;
    const id = text(raw.evidence_id).toUpperCase();
    if (!EVIDENCE_ID.test(id) || seen.has(id)) continue;
    seen.add(id);

    const provenance = lookup(PROVENANCE, raw.citation_status) ?? UNKNOWN_PROVENANCE;
    const kind = text(raw.kind);
    let title = text(raw.title);
    if (kind === "statistic" && lookup(STATISTIC_TITLES, title)) title = lookup(STATISTIC_TITLES, title);

    result.push({
      id,
      title: title || "Untitled evidence",
      identity: evidenceIdentity(raw),
      provenance,
      // Each provenance shows only the fields that belong to it.
      sourceName: provenance.key === "structured_record" ? text(raw.source_name) : "",
      source: provenance.key === "source_linked" ? sourceRef(raw.source) : null,
      relatedSourceName: provenance.key === "unverified_educational" ? text(raw.related_source?.name) : "",
      laureateId: laureateIdOf(raw.reference),
    });
  }
  return result;
}

// ------------------------------------------------------- evidence grouping
//
// The backend issues a new evidence id each time a tool returns a record, so
// one record retrieved twice (for example the same contribution from two
// get_laureate_details calls) gets two ids. Grouping is presentation only: the
// backend ids, citations and counts are unchanged, and every id stays visible.
//
// Stable identity comes from the citation's reference fields, which are set by
// backend/ai/agent/evidence.py for each evidence kind. Records without a
// recognised identity are never grouped.
const IDENTITY_FIELDS = {
  laureate_record: ["laureate_id"],
  contribution: ["contribution_id"],
  connection: ["connection_id"],
  explanation: ["contribution_id", "level"],
  statistic: ["operation", "applied_filters", "counting_unit"],
};
const KNOWLEDGE_FIELDS = ["doc_id", "chunk_id"];

function stableValue(value) {
  if (value === null || typeof value !== "object") return value;
  if (Array.isArray(value)) return value.map(stableValue);
  return Object.keys(value).sort().map((key) => [key, stableValue(value[key])]);
}

function evidenceIdentity(raw) {
  const kind = text(raw.kind);
  const tool = text(raw.tool);
  const fields = kind.startsWith("knowledge:") ? KNOWLEDGE_FIELDS : lookup(IDENTITY_FIELDS, kind);
  if (!fields || !tool || !isObject(raw.reference)) return null;
  const values = fields.map((field) => raw.reference[field]);
  if (values.some((value) => value === undefined || value === null || value === "")) return null;
  return JSON.stringify([tool, kind, ...values.map(stableValue)]);
}

/**
 * Groups normalised cards that are the same record: identical stable identity
 * AND identical provenance, title and source fields. Returns groups in first-
 * appearance order; each group lists every original evidence id.
 */
export function groupEvidence(cards) {
  const groups = [];
  const byKey = new Map();
  for (const card of Array.isArray(cards) ? cards : []) {
    const key = card.identity === null || card.identity === undefined ? null : JSON.stringify([
      card.identity, card.provenance.key, card.title, card.sourceName, card.source?.name ?? null,
      card.source?.url ?? null, card.relatedSourceName, card.laureateId,
    ]);
    const existing = key ? byKey.get(key) : undefined;
    if (existing) {
      existing.ids.push(card.id);
      continue;
    }
    const group = { ...card, ids: [card.id] };
    groups.push(group);
    if (key) byKey.set(key, group);
  }
  return groups;
}

// ------------------------------------------------------------- limitations

export function uniqueLimitations(limitations) {
  if (!Array.isArray(limitations)) return [];
  const seen = new Set();
  const result = [];
  for (const item of limitations) {
    const value = text(item);
    if (!value || seen.has(value)) continue;
    seen.add(value);
    result.push(value);
  }
  return result;
}

// Friendly limitation wording. Each pattern matches a template produced by
// backend/ai/agent/service.py (LIMITATION_TEXT and _limitations). Meaning is
// preserved: uncertainty is restated, never removed. Unrecognised messages are
// shown verbatim when they look like plain prose and replaced by a generic
// notice otherwise, so internal diagnostics are never echoed.

const TOOL_NAMES = {
  search_laureates: "Laureate search",
  get_laureate_details: "Laureate details lookup",
  get_nobel_statistics: "Statistics lookup",
  search_nobel_knowledge: "Knowledge search",
};

const TOOL_FAILURES = {
  validation_error: "the requested search parameters could not be processed",
  not_found: "the requested record was not found",
  database_error: "Nobel Explorer's records could not be queried",
  database_unavailable: "Nobel Explorer's records could not be queried",
  index_error: "the knowledge search was unavailable",
  index_incompatible: "the knowledge search was unavailable",
  index_unavailable: "the knowledge search was unavailable",
  tool_budget_exceeded: "it was not run because the tool-call limit was reached",
  not_executed: "it was not run",
  deadline_exceeded: "it stopped when the time limit was reached",
  unknown_tool: "the assistant asked for a tool that does not exist",
};

const BUDGET_NOTE = "tool-call budget reached; some requested calls were not executed";

function friendlyToolFailures(details) {
  const parts = [];
  let rest = details;
  if (rest.includes(BUDGET_NOTE)) {
    parts.push("The tool-call limit was reached, so some requested lookups were not run.");
    rest = rest.replace(BUDGET_NOTE, "");
  }
  for (const entry of rest.split(";").map((item) => item.trim()).filter(Boolean)) {
    const match = /^([a-z_]+): ([a-z_]+)$/.exec(entry);
    const tool = match ? lookup(TOOL_NAMES, match[1]) : undefined;
    const reason = match ? lookup(TOOL_FAILURES, match[2]) : undefined;
    if (tool) parts.push(`${tool} did not complete: ${reason ?? "an unexpected problem occurred"}.`);
    else if (match && reason) parts.push(`A requested lookup did not complete: ${reason}.`);
    else parts.push("A requested lookup did not complete.");
  }
  return parts;
}

function friendlyEmptyResult(detail) {
  if (detail.startsWith("search_laureates")) return "No matching laureates were found in Nobel Explorer's records.";
  if (detail.startsWith("get_nobel_statistics")) return "The requested statistic returned no data.";
  if (detail.startsWith("search_nobel_knowledge")) return "No related educational or scientific content was found.";
  return "Relevant information was not found in Nobel Explorer's records.";
}

const LIMITATION_RULES = [
  [/^Some tool calls failed: (.+)\.$/s, (m) => friendlyToolFailures(m[1])],
  [/^Semantic search returned only weak matches\b.*Treat this as insufficient evidence\.$/s,
    () => ["The available Nobel Explorer content may not closely match this question, so it was treated as insufficient evidence."]],
  [/^A name matched several laureates \('(.{1,120})' matched (\d+) laureates\)/s,
    (m) => [`The name "${m[1]}" matched ${m[2]} laureates, so the answer may need clarification.`]],
  [/^A name matched several laureates/,
    () => ["A name matched several laureates, so the answer may need clarification."]],
  [/^No matching records: (.+)\.$/s, (m) => m[1].split("; ").map(friendlyEmptyResult)],
  [/^Results were truncated: [a-z_]+ returned (\d+) of (\d+) matches/,
    (m) => [`Only some of the matching records were used (${m[1]} of ${m[2]}).`]],
  [/^Results were truncated/, () => ["Only some of the matching records were used."]],
  [/^No educational explanations are stored for (.{1,200})\.$/s,
    (m) => [`Nobel Explorer has no detailed educational explanations for ${m[1]}.`]],
  [/^Cited explanations are unverified educational content/,
    () => [EDUCATIONAL_PROVENANCE_NOTICE]],
  [/^Removed citation references not backed by tool evidence/,
    () => ["Some citation references did not match the retrieved evidence and were removed. Statements marked [unverified] are not supported by the evidence found."]],
  [/^Removed \d+ URL\(s\) that no tool returned/,
    () => ["Links that did not come from Nobel Explorer's records were removed (shown as [link removed])."]],
  [/^Removed related-source URL\(s\) presented as citations/,
    () => ["Related-source links were removed from the answer because they provide context only, not direct evidence."]],
  [/^No tool evidence was retrieved/,
    () => ["No supporting evidence was retrieved, so this answer is not based on Nobel Explorer data."]],
  [/^The answer does not cite any retrieved evidence\.$/,
    () => ["The answer does not reference any of the evidence that was retrieved."]],
  [/^The request time limit was reached before an answer was produced\.$/,
    () => ["The time limit was reached before a complete answer was produced."]],
  [/^The (?:time limit|model-call limit|step limit) was reached before a final answer was produced\.$/,
    () => ["The assistant reached a processing limit before producing a final answer."]],
];

const MAX_VERBATIM_CHARS = 300;
// eslint-disable-next-line no-control-regex
const DIAGNOSTIC_HINTS = /Traceback|Exception|Error\b|sk-[A-Za-z0-9]|[{}<>]|https?:\/\/|\b[a-z]+_[a-z_]+\b|[\u0000-\u0008\u000B-\u001F\u007F]/;
export const GENERIC_LIMITATION = "The assistant reported an additional limitation for this answer.";

export function friendlyLimitation(message) {
  const value = text(message);
  if (!value) return [];
  for (const [pattern, translate] of LIMITATION_RULES) {
    const match = pattern.exec(value);
    if (match) return translate(match);
  }
  if (value.length > MAX_VERBATIM_CHARS || DIAGNOSTIC_HINTS.test(value)) return [GENERIC_LIMITATION];
  return [value];
}

/** De-duplicated, user-friendly limitations in their original order. */
export function friendlyLimitations(limitations) {
  const seen = new Set();
  const result = [];
  for (const raw of uniqueLimitations(limitations)) {
    for (const item of friendlyLimitation(raw)) {
      if (seen.has(item)) continue;
      seen.add(item);
      result.push(item);
    }
  }
  return result;
}

// ---------------------------------------------------------------- grounding

// Provenance notice for answers that cite educational explanations. Shown in the
// collapsed Sources panel rather than under the answer; meaning is unchanged.
export const EDUCATIONAL_PROVENANCE_NOTICE =
  "Educational explanations are Nobel Explorer's own teaching content and have no stored external citation. "
  + "Related sources are shown for context only.";

export const ACCURACY_DISCLAIMER = "AI-generated answers may contain errors.";
export const CITATION_DISCLAIMER =
  "Citations indicate referenced information but do not guarantee factual correctness.";

const GROUNDING = {
  cited: {
    tone: "info",
    label: "Includes evidence references",
    detail: "Statements in this answer reference the evidence listed below.",
  },
  partially_cited: {
    tone: "warning",
    label: "Some references could not be validated",
    detail: "Statements marked [unverified] or [link removed] could not be matched to retrieved evidence.",
  },
  uncited: {
    tone: "warning",
    label: "No evidence references provided",
    detail: "This answer does not reference the evidence that was retrieved. Please check it independently.",
  },
  no_evidence: {
    tone: "neutral",
    label: "No supporting evidence retrieved",
    detail: "Nobel Explorer returned no matching records for this question, so the answer is not based on its data.",
  },
};

/** Returns null for null or unknown values: no classification is inferred. */
export function describeGrounding(grounding) {
  return lookup(GROUNDING, grounding) ?? null;
}

// ------------------------------------------------- general scientific knowledge
//
// Prompt 2026-11-27.2 lets the model answer relevant science questions from general
// knowledge when retrieved evidence does not cover them; such statements carry no
// citations. These helpers decide which subtle note to show under an answer:
//   "general": no valid citations and not an abstention
//   "mixed":   cited answer with at least one substantial paragraph without citations
// Abstentions ("Nobel Explorer has no records for 2026 ...") keep the normal warnings.

export const GENERAL_KNOWLEDGE_NOTE = "General scientific knowledge · No retrieved source";
export const MIXED_KNOWLEDGE_NOTE = "Partly sourced · Some statements use general scientific knowledge";

const ABSTENTION_HINT = new RegExp([
  String.raw`\b(?:no|not any)\s+(?:reliable\s+|relevant\s+|matching\s+)?(?:record|records|information|evidence|data|explanation)\b`,
  String.raw`\bhas no information\b`,
  String.raw`\b(?:does not|doesn't|do not|don't)\s+(?:have|contain|include)\b[^.]{0,60}\b(?:record|records|information|evidence|explanation|data)\b`,
  String.raw`\bonly covers?\b`,
  String.raw`\bcovers?\b[^.]{0,40}\b(?:through|until|up to)\s+\d{4}\b`,
  String.raw`\b(?:can't|cannot|unable to)\s+(?:answer|explain|help|confirm)\b`,
  String.raw`\boutside (?:the )?scope\b`,
  String.raw`\bnot (?:able|confident)\b`,
].join("|"), "i");
const MAX_ABSTENTION_CHARS = 400;
const MIN_GENERAL_PARAGRAPH_CHARS = 40;

export function looksLikeAbstention(answer) {
  const value = text(answer).replace(/[\u2018\u2019]/g, "'");
  return Boolean(value) && value.length <= MAX_ABSTENTION_CHARS && ABSTENTION_HINT.test(value);
}

const hasCitation = (paragraph) => tokenizeAnswer(paragraph).some((token) => token.type === "citations");

/** "general", "mixed" or null for an answer and its backend grounding value. */
export function knowledgeKind(answer, grounding) {
  const value = text(answer);
  if (!value || looksLikeAbstention(value)) return null;
  if (grounding === "uncited" || grounding === "no_evidence") return "general";
  if (grounding === "cited" || grounding === "partially_cited") {
    const paragraphs = value.split(/\n\s*\n/).map((item) => item.trim()).filter(Boolean);
    const uncited = paragraphs.some((item) => item.length >= MIN_GENERAL_PARAGRAPH_CHARS && !hasCitation(item)
      && !looksLikeAbstention(item));
    return paragraphs.length > 1 && uncited ? "mixed" : null;
  }
  return null;
}

// Limitations that only restate "no matching evidence"; the general-knowledge note
// already says this, so they are hidden for general answers.
export const RESTATES_NO_MATCH = new Set([
  "No supporting evidence was retrieved, so this answer is not based on Nobel Explorer data.",
  "The answer does not reference any of the evidence that was retrieved.",
  "The available Nobel Explorer content may not closely match this question, so it was treated as insufficient evidence.",
  "No related educational or scientific content was found.",
]);

// ---------------------------------------------------------------- tool calls

const TOOLS = {
  search_laureates: {
    label: "Search Nobel laureates",
    description: "Looks up laureates in the Nobel Explorer database by name, year, category or other filters.",
  },
  get_laureate_details: {
    label: "Retrieve laureate details",
    description: "Reads one laureate's record, prizes and any educational content.",
  },
  get_nobel_statistics: {
    label: "Analyze Nobel Prize statistics",
    description: "Computes aggregate figures from Nobel Explorer records.",
  },
  search_nobel_knowledge: {
    label: "Search scientific knowledge",
    description: "Searches Nobel Explorer's educational and scientific content by meaning.",
  },
};
const UNKNOWN_TOOL = { label: "Unrecognized tool", description: "The assistant requested a tool that is not available." };

// Explicit allowlist: argument key -> display label. Anything else (ids,
// limits, flags, unexpected keys) is never shown.
const ARGUMENT_LABELS = [
  ["name", "Name"],
  ["query", "Search"],
  ["operation", "Statistic"],
  ["year", "Year"],
  ["start_year", "From"],
  ["end_year", "To"],
  ["category", "Category"],
  ["birth_country", "Birth country"],
  ["affiliation_country", "Institution country"],
  ["gender", "Gender"],
  ["level", "Explanation level"],
  ["include_explanation_level", "Explanation level"],
];
const MAX_ARGUMENT_CHARS = 160;

const FAILURE_REASONS = {
  tool_budget_exceeded: "Not run: the tool-call limit was reached",
  validation_error: "Not run: the search parameters were not accepted",
  not_found: "No matching record was found",
  deadline_exceeded: "Stopped: the time limit was reached",
};

function displayValue(key, value) {
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  if (typeof value !== "string") return "";
  let result = value.replace(/\s+/g, " ").trim();
  if (key === "operation") result = lookup(STATISTIC_TITLES, result) ?? "";
  if (result.length > MAX_ARGUMENT_CHARS) result = `${result.slice(0, MAX_ARGUMENT_CHARS - 1)}…`;
  return result;
}

export function safeToolArguments(args) {
  if (!isObject(args)) return [];
  const result = [];
  const usedLabels = new Set();
  for (const [key, label] of ARGUMENT_LABELS) {
    if (!Object.hasOwn(args, key) || usedLabels.has(label)) continue;
    const value = displayValue(key, args[key]);
    if (!value) continue;
    usedLabels.add(label);
    result.push({ key, label, value });
  }
  return result;
}

/** Display-ready tool activity. Ids, latency and raw error types are dropped. */
export function normalizeToolCalls(toolCalls) {
  if (!Array.isArray(toolCalls)) return [];
  return toolCalls.filter(isObject).map((call, index) => {
    const known = lookup(TOOLS, call.name);
    const tool = known ?? UNKNOWN_TOOL;
    const ok = call.ok === true;
    const evidenceCount = Array.isArray(call.evidence_ids)
      ? call.evidence_ids.filter((id) => typeof id === "string" && EVIDENCE_ID.test(id.toUpperCase())).length
      : null;
    return {
      key: index,
      label: tool.label,
      description: tool.description,
      arguments: known ? safeToolArguments(call.arguments) : [],
      ok,
      statusText: ok ? "Completed" : (lookup(FAILURE_REASONS, call.error_type) ?? "Did not complete"),
      evidenceCount: ok ? evidenceCount : null,
    };
  });
}
