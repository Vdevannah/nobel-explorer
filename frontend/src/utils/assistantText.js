// Tokenise an AI assistant answer into plain text, citation groups and
// validation markers. The output is data only: components render every
// token as escaped React text, so nothing in an answer is ever treated as HTML.
//
// Recognised (case-insensitive):
//   [E1]  [E1][E2]  [E1, E2]  [E1; E2]   -> { type: "citations", ids: ["E1", "E2"] }
//   [unverified]                         -> { type: "marker", marker: "unverified" }
//   [link removed]                       -> { type: "marker", marker: "link_removed" }
// Any other bracketed text stays literal text.

const TOKEN_PATTERN = /\[\s*(E\d+(?:\s*[,;]\s*E\d+)*)\s*\]|\[(unverified)\]|\[(link removed)\]/gi;

export function tokenizeAnswer(text) {
  if (typeof text !== "string" || text === "") {
    return [];
  }

  const tokens = [];
  let lastIndex = 0;
  TOKEN_PATTERN.lastIndex = 0;

  for (const match of text.matchAll(TOKEN_PATTERN)) {
    if (match.index > lastIndex) {
      tokens.push({ type: "text", value: text.slice(lastIndex, match.index) });
    }
    if (match[1]) {
      const ids = match[1].split(/[,;]/).map((id) => id.trim().toUpperCase()).filter(Boolean);
      tokens.push({ type: "citations", ids, raw: match[0] });
    } else if (match[2]) {
      tokens.push({ type: "marker", marker: "unverified", raw: match[0] });
    } else {
      tokens.push({ type: "marker", marker: "link_removed", raw: match[0] });
    }
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    tokens.push({ type: "text", value: text.slice(lastIndex) });
  }
  return tokens;
}

// Evidence ids cited in the answer, in first-appearance order (deduplicated).
export function citedEvidenceIds(text) {
  const seen = [];
  for (const token of tokenizeAnswer(text)) {
    if (token.type === "citations") {
      for (const id of token.ids) {
        if (!seen.includes(id)) seen.push(id);
      }
    }
  }
  return seen;
}

// Minimal, safe inline emphasis: well-formed **bold** only. No other Markdown is
// interpreted (links, images, headings and HTML stay literal text), and the result
// is data for React to render, never HTML.
//
// A span is emphasised only when the opening ** is followed by a non-space,
// non-asterisk character, the closing ** is preceded by one, the content stays on
// one line and contains no further **. Anything else (unmatched or malformed
// markers) remains literal text. Citation tokens are found inside each segment
// afterwards, so "[E1]" works inside or next to emphasis.
const EMPHASIS_PATTERN = /\*\*(?=[^\s*])([^\n]*?[^\s*])\*\*/g;

export function splitEmphasis(text) {
  if (typeof text !== "string" || text === "") return [];
  const segments = [];
  let plainStart = 0;
  EMPHASIS_PATTERN.lastIndex = 0;
  for (const match of text.matchAll(EMPHASIS_PATTERN)) {
    if (match[1].includes("**")) continue; // ambiguous nesting: keep literal
    if (match.index > plainStart) segments.push({ strong: false, text: text.slice(plainStart, match.index) });
    segments.push({ strong: true, text: match[1] });
    plainStart = match.index + match[0].length;
  }
  if (plainStart < text.length) segments.push({ strong: false, text: text.slice(plainStart) });
  return segments;
}

// ------------------------------------------------------------------ learner view
//
// The public page hides evidence ids (E1, E2 ...) from the answer text. The
// citations themselves are unchanged in the response; the Sources panel shows
// which statements each source supports (claimsByEvidence).

const CITATION_GROUP = /\s*\[\s*E\d+(?:\s*[,;]\s*E\d+)*\s*\]/gi;
// A citation that opens a line or an (opening) emphasis span also takes the space after it,
// so "**[E3] Karikó**" stays well-formed bold ("**Karikó**").
const LEADING_CITATION = /(^|(?<=^|\s)\*\*)[ \t]*\[\s*E\d+(?:\s*[,;]\s*E\d+)*\s*\][ \t]*/gim;

/** Answer text without evidence-id citations (validation markers are kept). */
export function stripCitations(text) {
  if (typeof text !== "string") return "";
  return text.replace(LEADING_CITATION, "$1").replace(CITATION_GROUP, "").replace(/^[ \t]+/gm, "");
}

/** Clean text for copying: no evidence ids and no ** emphasis markers. */
export function plainAnswerText(text) {
  return splitEmphasis(stripCitations(text)).map((segment) => segment.text).join("");
}

const SENTENCE_BREAK = /(?<=[.!?])\s+|\n+/;
const MAX_CLAIM_CHARS = 220;

/**
 * Evidence id -> statements (sentences) in the answer that cite it, in order.
 * A citation-only fragment such as "… possible. [E4]" belongs to the sentence
 * before it. Statements are returned without citations and lightly shortened.
 */
export function claimsByEvidence(text) {
  const result = {};
  if (typeof text !== "string" || !text.trim()) return result;
  const sentences = [];
  for (const raw of text.split(SENTENCE_BREAK)) {
    const ids = [];
    for (const token of tokenizeAnswer(raw)) if (token.type === "citations") ids.push(...token.ids);
    const claim = splitEmphasis(stripCitations(raw)).map((segment) => segment.text).join("").trim()
      .replace(/^[-•]\s+/, "");
    if (!claim.replace(/[.,;:!?\s]/g, "") && sentences.length) {
      sentences[sentences.length - 1].ids.push(...ids); // citation-only fragment
    } else if (claim) {
      sentences.push({ claim, ids });
    }
  }
  for (const { claim, ids } of sentences) {
    const shown = claim.length > MAX_CLAIM_CHARS ? `${claim.slice(0, MAX_CLAIM_CHARS - 1).trimEnd()}…` : claim;
    for (const id of new Set(ids)) {
      result[id] = result[id] || [];
      if (!result[id].includes(shown)) result[id].push(shown);
    }
  }
  return result;
}
