const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/$/, "");

export async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const errorBody = await response.json();
      message = errorBody.detail || message;
    } catch {
      // The response did not contain JSON, so retain the status-based message.
    }

    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export async function getLaureateById(laureateId, { signal } = {}) {
  return apiRequest(`/laureates/${encodeURIComponent(laureateId)}`, { signal });
}

export function getLaureateContributions(laureateId, { signal } = {}) {
  return apiRequest(
    `/laureates/${encodeURIComponent(laureateId)}/contributions`,
    { signal },
  );
}

export function getLearnTopics({ signal } = {}) {
  return apiRequest("/contributions", { signal });
}

export function getContributionById(contributionId, { signal } = {}) {
  return apiRequest(`/contributions/${encodeURIComponent(contributionId)}`, { signal });
}

export function getContributionConnections(contributionId, { signal } = {}) {
  return apiRequest(
    `/contributions/${encodeURIComponent(contributionId)}/connections`,
    { signal },
  );
}

export function getContributionExplanations(contributionId, { level = "", signal } = {}) {
  const params = new URLSearchParams();
  if (level) params.set("level", level);
  const query = params.toString();
  return apiRequest(
    `/contributions/${encodeURIComponent(contributionId)}/explanations${query ? `?${query}` : ""}`,
    { signal },
  );
}

export function getContributionQuiz(contributionId, { level = "", signal } = {}) {
  const params = new URLSearchParams();
  if (level) params.set("level", level);
  const query = params.toString();
  return apiRequest(
    `/contributions/${encodeURIComponent(contributionId)}/quiz${query ? `?${query}` : ""}`,
    { signal },
  );
}

export function checkQuizAnswer(questionId, selectedAnswer, { signal } = {}) {
  return apiRequest(`/quiz-questions/${encodeURIComponent(questionId)}/check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ selected_answer: selectedAnswer }),
    signal,
  });
}

export function getLaureates({
  limit = 20,
  offset = 0,
  search = "",
  category = "",
  year = "",
  country = "",
  gender = "",
  signal,
} = {}) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });

  const optionalParams = { search, category, year, country, gender };
  Object.entries(optionalParams).forEach(([key, value]) => {
    const normalizedValue = String(value).trim();
    if (normalizedValue) {
      params.set(key, normalizedValue);
    }
  });

  return apiRequest(`/laureates?${params.toString()}`, { signal });
}

export function getCategories({ signal } = {}) {
  return apiRequest("/categories", { signal });
}

export function getCategoryById(categoryId, { signal } = {}) {
  return apiRequest(`/categories/${encodeURIComponent(categoryId)}`, { signal });
}

export function getPrizes({
  limit = 20,
  offset = 0,
  category = "",
  year = "",
  signal,
} = {}) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });

  if (category.trim()) {
    params.set("category", category.trim());
  }
  if (String(year).trim()) {
    params.set("year", String(year).trim());
  }

  return apiRequest(`/prizes?${params.toString()}`, { signal });
}

export function getPrizeById(prizeId, { signal } = {}) {
  return apiRequest(`/prizes/${encodeURIComponent(prizeId)}`, { signal });
}

function analyticsRequest(path, params = {}, signal) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (String(value).trim()) searchParams.set(key, String(value).trim());
  });
  const query = searchParams.toString();
  return apiRequest(`/analytics/${path}${query ? `?${query}` : ""}`, { signal });
}

// Phase 10D: the small, consistent category/start_year/end_year filter
// set shared by the dashboard trend endpoints. All three are optional;
// omitted values are simply left out of the query string.
function withYearRangeFilters({ category = "", startYear = "", endYear = "" } = {}) {
  return { category, start_year: startYear, end_year: endYear };
}

export function getAnalyticsSummary({ category, startYear, endYear, signal } = {}) {
  return analyticsRequest(
    "summary",
    withYearRangeFilters({ category, startYear, endYear }),
    signal,
  );
}

export function getAnalyticsCategoryCounts({ startYear, endYear, signal } = {}) {
  return analyticsRequest(
    "laureates-by-category",
    withYearRangeFilters({ startYear, endYear }),
    signal,
  );
}

export function getAnalyticsDecades({ category, startYear, endYear, signal } = {}) {
  return analyticsRequest(
    "decades",
    withYearRangeFilters({ category, startYear, endYear }),
    signal,
  );
}

export function getAnalyticsPrizesByDecade({ category, startYear, endYear, signal } = {}) {
  return analyticsRequest(
    "prizes-by-decade",
    withYearRangeFilters({ category, startYear, endYear }),
    signal,
  );
}

export function getAnalyticsTopCountries({ limit = 5, category, startYear, endYear, signal } = {}) {
  return analyticsRequest(
    "top-countries",
    { limit, ...withYearRangeFilters({ category, startYear, endYear }) },
    signal,
  );
}

export function getAnalyticsAgeDistribution({ category, startYear, endYear, signal } = {}) {
  return analyticsRequest(
    "age-distribution",
    withYearRangeFilters({ category, startYear, endYear }),
    signal,
  );
}

export function getAnalyticsWomenByEra({ category, startYear, endYear, signal } = {}) {
  return analyticsRequest(
    "women-by-era",
    withYearRangeFilters({ category, startYear, endYear }),
    signal,
  );
}

export function getAnalyticsCategoriesByDecade({ category, startYear, endYear, signal } = {}) {
  return analyticsRequest(
    "categories-by-decade",
    withYearRangeFilters({ category, startYear, endYear }),
    signal,
  );
}

export function getAnalyticsForCategory(category, { signal } = {}) {
  return Promise.all([
    analyticsRequest("birth-countries", { category }, signal),
    analyticsRequest("us-birth-states", { category }, signal),
    analyticsRequest("institutions", { category, country: "USA" }, signal),
    analyticsRequest("gender", { category }, signal),
    analyticsRequest("average-age", { category }, signal),
  ]).then(([countries, states, institutions, gender, averageAge]) => ({
    countries,
    states,
    institutions,
    gender,
    averageAge,
  }));
}

// ---------------------------------------------------------------------------
// AI Research Assistant (POST /ai/chat)
//
// Unlike apiRequest, this never throws for HTTP errors: /ai/chat returns a
// structured ChatResponse for 200, 503, 502 and 500, and that body (status,
// answer, citations, error) is what the page needs. The result is a tagged
// object so every outcome can be rendered deliberately:
//   { kind: "response", httpStatus, response }      a ChatResponse body
//   { kind: "unavailable", httpStatus }            503 with {"detail": "..."}
//   { kind: "validation_error", httpStatus, message } 422 (string or list detail)
//   { kind: "aborted" }                            the browser request was cancelled
//   { kind: "network_error" }                      the server could not be reached
//   { kind: "malformed_response", httpStatus }     body was not valid JSON
//   { kind: "unexpected_response", httpStatus }    JSON of an unknown shape
// No automatic retries. The OpenAI key lives only on the server.

export const ASSISTANT_MAX_QUESTION_CHARS = 1000; // backend default AI_AGENT_MAX_QUESTION_CHARS

const ASSISTANT_STATUSES = new Set(["completed", "budget_exhausted", "timeout", "error", "unavailable"]);

function isChatResponse(body) {
  return (
    body !== null
    && typeof body === "object"
    && !Array.isArray(body)
    && typeof body.request_id === "string"
    && ASSISTANT_STATUSES.has(body.status)
    && (body.answer === null || body.answer === undefined || typeof body.answer === "string")
    && (body.citations === undefined || Array.isArray(body.citations))
    && (body.tool_calls === undefined || Array.isArray(body.tool_calls))
    && (body.evidence_limitations === undefined || Array.isArray(body.evidence_limitations))
  );
}

function validationMessage(detail) {
  if (typeof detail === "string" && detail.trim()) {
    return detail.trim();
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (item && typeof item.msg === "string" ? item.msg.trim() : ""))
      .filter(Boolean);
    if (messages.length) {
      return messages.join(" ");
    }
  }
  return "The question could not be accepted. Please check it and try again.";
}

function isAbortError(error, signal) {
  return Boolean(signal?.aborted) || error?.name === "AbortError";
}

export async function askResearchAssistant(question, { signal } = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}/ai/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ question }),
      signal,
    });
  } catch (error) {
    return isAbortError(error, signal) ? { kind: "aborted" } : { kind: "network_error" };
  }

  let text;
  try {
    text = await response.text();
  } catch (error) {
    return isAbortError(error, signal) ? { kind: "aborted" } : { kind: "network_error" };
  }

  let body;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    return { kind: "malformed_response", httpStatus: response.status };
  }

  if (isChatResponse(body)) {
    return { kind: "response", httpStatus: response.status, response: body };
  }
  if (response.status === 503) {
    // Invalid server configuration returns {"detail": "..."}; the detail is an
    // operator message, so it is not shown to visitors.
    return { kind: "unavailable", httpStatus: 503 };
  }
  if (response.status === 422) {
    return { kind: "validation_error", httpStatus: 422, message: validationMessage(body?.detail) };
  }
  return { kind: "unexpected_response", httpStatus: response.status };
}

export { API_BASE_URL };
