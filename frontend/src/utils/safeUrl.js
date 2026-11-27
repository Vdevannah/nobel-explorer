// Pure validation for external links taken from citation records.
// Only absolute http(s) URLs pass. Model-generated answer text is never
// passed through here: the answer is rendered as plain text, never linked.

const MAX_URL_LENGTH = 2048;
// C0 and C1 control characters and DEL. The URL parser silently strips tabs and
// newlines, so they are rejected before parsing rather than normalised away.
// eslint-disable-next-line no-control-regex
const CONTROL_CHARACTERS = /[\u0000-\u001F\u007F-\u009F]/;
// Requires an explicit scheme followed by "//". This rejects relative and
// protocol-relative URLs and forms such as "https:example.com" that the parser
// would otherwise accept. Backslashes and whitespace are refused outright.
const ABSOLUTE_HTTP = /^https?:\/\/[^\s\\]+$/i;
const ALLOWED_PROTOCOLS = new Set(["http:", "https:"]);

/**
 * Returns a normalised absolute http(s) URL string, or null when the value is
 * missing, malformed, uses another scheme or carries embedded credentials.
 */
export function safeExternalUrl(value) {
  if (typeof value !== "string") return null;
  if (value.length === 0 || value.length > MAX_URL_LENGTH) return null;
  if (CONTROL_CHARACTERS.test(value)) return null;
  if (!ABSOLUTE_HTTP.test(value)) return null;

  let parsed;
  try {
    parsed = new URL(value);
  } catch {
    return null;
  }

  if (!ALLOWED_PROTOCOLS.has(parsed.protocol)) return null;
  if (!parsed.hostname) return null;
  if (parsed.username || parsed.password) return null;
  return parsed.href;
}

/** Readable host for display next to a link, e.g. "www.nobelprize.org". */
export function displayHost(safeUrl) {
  try {
    return new URL(safeUrl).host;
  } catch {
    return "";
  }
}
