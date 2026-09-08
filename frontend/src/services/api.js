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

export function getAnalyticsSummary({ signal } = {}) {
  return analyticsRequest("summary", {}, signal);
}

// Phase 10D: the small, consistent category/start_year/end_year filter
// set shared by the dashboard trend endpoints. All three are optional;
// omitted values are simply left out of the query string.
function withYearRangeFilters({ category = "", startYear = "", endYear = "" } = {}) {
  return { category, start_year: startYear, end_year: endYear };
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

export { API_BASE_URL };
