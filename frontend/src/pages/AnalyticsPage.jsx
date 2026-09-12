import { lazy, Suspense, useEffect, useMemo, useState } from "react";

import {
  getAnalyticsAgeDistribution,
  getAnalyticsCategoryCounts,
  getAnalyticsForCategory,
  getAnalyticsPrizesByDecade,
  getAnalyticsSummary,
  getAnalyticsTopCountries,
  getAnalyticsWomenByEra,
  getCategories,
} from "../services/api";
import { getCountryFlag } from "../utils/countryFlags";

// react-simple-maps (and the d3-geo/topojson-client stack it pulls in)
// and the bundled world topojson are only needed once someone actually
// views this section, so they're split into their own chunk instead of
// shipping in the app's main bundle for every page.
const GeographyExplorer = lazy(() => import("../components/analytics/GeographyExplorer"));

// The map/list geography view needs the complete set of recorded birth
// countries (not just a short top-N slice) so every laureate contributes
// to the choropleth and the ranked list -- 200 comfortably covers the
// dataset's ~100 distinct birth countries, matching the backend's raised
// /top-countries limit ceiling.
const ALL_COUNTRIES_LIMIT = 200;

const CHART_COLORS = ["#7c4dff", "#b339e7", "#f04468", "#e8b83e", "#72c77b", "#43c1b5"];

// Mirrors the backend's MIN_NOBEL_YEAR / MAX_NOBEL_YEAR (backend/routes/analytics.py)
// so invalid years are caught here before a request is ever sent.
const MIN_ANALYTICS_YEAR = 1901;
const MAX_ANALYTICS_YEAR = 2100;

const DID_YOU_KNOW_FACTS = [
  "Marie Curie is the only person to win Nobel Prizes in two different sciences: Physics (1903) and Chemistry (1911).",
  "The youngest Nobel laureate was Malala Yousafzai, who was 17 years old when she won the Peace Prize in 2014.",
  "Linus Pauling is the only person to have won two unshared Nobel Prizes: Chemistry (1954) and Peace (1962).",
  "The Nobel Memorial Prize in Economic Sciences was added in 1968 and isn't one of the five original prizes from Alfred Nobel's will.",
  "In 1974, the Nobel Foundation decided prizes generally cannot be awarded posthumously.",
];

const DEEP_DIVE_TABS = [
  { id: "countries", label: "Countries" },
  { id: "states", label: "U.S. States" },
  { id: "institutions", label: "Institutions" },
  { id: "gender", label: "Gender" },
];

const DEFAULT_DEEP_DIVE_CATEGORY = "Physics";

// .panel-kicker is uppercased by CSS (text-transform: uppercase), so
// these helpers return natural casing and let the stylesheet do the
// visual all-caps treatment -- consistent with every other kicker on
// this page ("Birthplace", "Award-time affiliations", etc).
function formatYearRangeLabel(startYear, endYear) {
  if (startYear && endYear) return `${startYear}–${endYear}`;
  if (startYear) return `${startYear}–present`;
  if (endYear) return `1901–${endYear}`;
  return "1901–present";
}

// Eyebrow for every chart whose backend endpoint already supports the
// applied category/start_year/end_year filters, so the label never
// claims "all categories" for data that has actually been narrowed.
function formatFilterEyebrow(category, startYear, endYear) {
  const yearLabel = formatYearRangeLabel(startYear, endYear);
  if (!category) return `All categories · ${yearLabel}`;
  if (!startYear && !endYear) return category;
  return `${category} · ${yearLabel}`;
}

// "Laureates by Category" is an intentional exception -- it exists to
// compare categories against each other, so it never narrows by the
// applied category even though the KPIs and other charts do. It still
// respects the applied year range (its backend endpoint supports that),
// so the eyebrow reflects the year scope without implying a category
// filter was applied.
function formatCategoryComparisonEyebrow(startYear, endYear) {
  if (!startYear && !endYear) return "Category comparison";
  return `Category comparison · ${formatYearRangeLabel(startYear, endYear)}`;
}

function MetricCard({ icon, label, value, detail }) {
  return (
    <article className="analytics-metric">
      <span className="analytics-metric-icon" aria-hidden="true">{icon}</span>
      <div>
        <strong>{value}</strong>
        <p>{label}</p>
        <span>{detail}</span>
      </div>
    </article>
  );
}

function RankedBars({ data, labelKey, emptyMessage, limit = 8, showRank = false, showFlag = false }) {
  const visibleData = data.slice(0, limit);
  const maximum = Math.max(...visibleData.map((item) => item.laureate_count), 1);

  if (!visibleData.length) return <p className="analytics-empty">{emptyMessage}</p>;

  return (
    <ol className="ranked-bars">
      {visibleData.map((item, index) => {
        const flag = showFlag ? getCountryFlag(item[labelKey]) : null;
        return (
          <li key={item[labelKey]}>
            <div>
              <span>
                {showRank && <em>{index + 1}</em>}
                {flag && <span className="ranked-flag" aria-hidden="true">{flag}</span>}
                {item[labelKey]}
              </span>
              <strong>{item.laureate_count}</strong>
            </div>
            <span className="ranked-track" aria-hidden="true">
              <span style={{ width: `${(item.laureate_count / maximum) * 100}%` }} />
            </span>
          </li>
        );
      })}
    </ol>
  );
}

function CategoryDonut({ data }) {
  const total = data.reduce((sum, item) => sum + item.laureate_count, 0);
  let position = 0;
  const segments = data.map((item, index) => {
    const start = position;
    position += total ? (item.laureate_count / total) * 100 : 0;
    return `${CHART_COLORS[index % CHART_COLORS.length]} ${start}% ${position}%`;
  });

  return (
    <div className="category-chart-layout">
      <div className="donut-chart" style={{ background: `conic-gradient(${segments.join(", ")})` }} aria-label={`${total} distinct laureates across all categories`} role="img">
        <span><strong>{total}</strong><small>Total laureates</small></span>
      </div>
      <ul className="analytics-legend">
        {data.map((item, index) => (
          <li key={item.category}>
            <i style={{ background: CHART_COLORS[index % CHART_COLORS.length] }} />
            <span>{item.category}</span>
            <strong>{item.laureate_count}</strong>
            <small>{total ? `${Math.round((item.laureate_count / total) * 1000) / 10}%` : "0%"}</small>
          </li>
        ))}
      </ul>
    </div>
  );
}

// height defaults to the original compact ratio; panels whose CSS Grid row
// gets stretched much taller by a bigger sibling (e.g. this chart next to
// the donut+legend panel) can pass a taller value so the plot itself fills
// that space instead of leaving it blank below the x-axis. Panels that
// already pair with a similarly-sized sibling (e.g. this chart next to the
// fixed-height age-bar-chart) can leave it at the default.
function TrendLineChart({ data, xKey, yKey, formatX, formatY, formatTooltip, ariaLabel, emptyMessage, height = 160 }) {
  const width = 720;
  // topPadding reserves headroom above the highest point so its
  // larger point-value label doesn't clip the top of the viewBox.
  const topPadding = 34;
  const bottomPadding = 28;
  const maximum = Math.max(...data.map((item) => item[yKey]), 1);
  const points = data.map((item, index) => {
    const x = data.length === 1 ? width / 2 : 20 + (index / (data.length - 1)) * (width - 40);
    const y = height - bottomPadding - (item[yKey] / maximum) * (height - bottomPadding - topPadding);
    return { ...item, x, y };
  });

  if (!data.length) return <p className="analytics-empty">{emptyMessage}</p>;

  return (
    <div className="decade-chart">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel}>
        <line className="chart-axis" x1="20" x2={width - 20} y1={height - bottomPadding} y2={height - bottomPadding} />
        <polyline className="chart-line" points={points.map(({ x, y }) => `${x},${y}`).join(" ")} />
        {points.map((point, index) => (
          <g key={point[xKey]}>
            <circle className="chart-point" cx={point.x} cy={point.y} r="5">
              <title>{formatTooltip ? formatTooltip(point) : `${formatX(point[xKey])}: ${formatY(point[yKey])}`}</title>
            </circle>
            <text x={point.x} y={point.y - 14} textAnchor="middle" className="chart-point-value">{formatY(point[yKey])}</text>
            {(data.length <= 6 || index % 2 === 0 || index === points.length - 1) && (
              <text x={point.x} y={height - 6} textAnchor="middle">{formatX(point[xKey])}</text>
            )}
          </g>
        ))}
      </svg>
      {/* Concise accessible data summary: the SVG's role="img" makes its
          <text> labels opaque to screen readers, so the exact values are
          restated here as plain text instead of only being visible or
          only reachable via mouse-hover <title> tooltips. */}
      <ul className="visually-hidden">
        {points.map((point) => (
          <li key={point[xKey]}>{formatX(point[xKey])}: {formatY(point[yKey])}</li>
        ))}
      </ul>
    </div>
  );
}

function AgeBarChart({ data }) {
  const maximum = Math.max(...data.map((item) => item.percentage), 1);

  if (!data.length) return <p className="analytics-empty">No age data is available.</p>;

  return (
    // role="group" (not "img"): the percentage/age-group text below is
    // real, meaningful content -- role="img" would present this as one
    // opaque image and hide that text from screen readers entirely.
    <div className="age-bar-chart" role="group" aria-label="Distribution of award-age observations by approximate age group; a repeat winner may contribute more than one observation">
      {data.map((item) => (
        <div className="age-bar-column" key={item.age_group}>
          <span className="age-bar-value">{item.percentage}%</span>
          <span className="age-bar-track" aria-hidden="true">
            <span style={{ height: `${(item.percentage / maximum) * 100}%` }} />
          </span>
          <span className="age-bar-label">{item.age_group}</span>
        </div>
      ))}
    </div>
  );
}

function DidYouKnow() {
  const fact = useMemo(
    () => DID_YOU_KNOW_FACTS[Math.floor(Math.random() * DID_YOU_KNOW_FACTS.length)],
    [],
  );

  return (
    <aside className="did-you-know" aria-label="Did you know">
      <h2>💡 Did You Know?</h2>
      <p>{fact}</p>
    </aside>
  );
}

function DeepDiveTabs({ activeTab, onChange }) {
  function handleKeyDown(event) {
    const currentIndex = DEEP_DIVE_TABS.findIndex((tab) => tab.id === activeTab);
    let nextIndex = null;

    if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % DEEP_DIVE_TABS.length;
    if (event.key === "ArrowLeft") nextIndex = (currentIndex - 1 + DEEP_DIVE_TABS.length) % DEEP_DIVE_TABS.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = DEEP_DIVE_TABS.length - 1;
    if (nextIndex === null) return;

    event.preventDefault();
    onChange(DEEP_DIVE_TABS[nextIndex].id);
    event.currentTarget.parentElement.children[nextIndex].focus();
  }

  return (
    <div className="analytics-tabs" role="tablist" aria-label="Category deep-dive views">
      {DEEP_DIVE_TABS.map((tab) => (
        <button
          className={`analytics-tab${activeTab === tab.id ? " analytics-tab--active" : ""}`}
          id={`deep-dive-tab-${tab.id}`}
          type="button"
          role="tab"
          aria-controls={`deep-dive-panel-${tab.id}`}
          aria-selected={activeTab === tab.id}
          tabIndex={activeTab === tab.id ? 0 : -1}
          onClick={() => onChange(tab.id)}
          onKeyDown={handleKeyDown}
          key={tab.id}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

function AnalyticsPage() {
  const [summary, setSummary] = useState(null);
  const [categoryCounts, setCategoryCounts] = useState([]);
  const [prizesByDecade, setPrizesByDecade] = useState([]);
  const [topCountries, setTopCountries] = useState([]);
  const [ageDistribution, setAgeDistribution] = useState([]);
  const [womenByEra, setWomenByEra] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(DEFAULT_DEEP_DIVE_CATEGORY);
  const [categoryAnalytics, setCategoryAnalytics] = useState(null);
  const [deepDiveTab, setDeepDiveTab] = useState("countries");
  const [globalStatus, setGlobalStatus] = useState("loading");
  const [categoryStatus, setCategoryStatus] = useState("loading");
  const [retryKey, setRetryKey] = useState(0);

  // Filter UX fix: `draft*` state tracks whatever is currently in the
  // filter controls (updated on every keystroke/selection), while
  // `filter*` state is the APPLIED set the fetch effect below actually
  // depends on. Nothing reaches `filter*` without first passing
  // validateDraftFilters -- so the fetch effect can assume its inputs
  // are always either empty or a complete, in-range, correctly-ordered
  // year, and never needs to special-case an in-progress/partial value.
  // This is intentionally separate from `selectedCategory` below, which
  // always holds a real category and drives the category-required
  // deep-dive section further down the page.
  const [draftCategory, setDraftCategory] = useState("");
  const [draftStartYear, setDraftStartYear] = useState("");
  const [draftEndYear, setDraftEndYear] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [filterStartYear, setFilterStartYear] = useState("");
  const [filterEndYear, setFilterEndYear] = useState("");
  const [filterError, setFilterError] = useState(null);

  const hasDraftOrAppliedFilters = Boolean(
    draftCategory || draftStartYear || draftEndYear || filterCategory || filterStartYear || filterEndYear,
  );

  function validateYearField(value, label) {
    const trimmed = value.trim();
    if (!trimmed) return null;
    if (!/^\d+$/.test(trimmed)) return `${label} must be a valid year.`;
    const year = Number(trimmed);
    if (year < MIN_ANALYTICS_YEAR || year > MAX_ANALYTICS_YEAR) {
      return `${label} must be between ${MIN_ANALYTICS_YEAR} and ${MAX_ANALYTICS_YEAR}.`;
    }
    return null;
  }

  function validateDraftFilters(startYearValue, endYearValue) {
    const startError = validateYearField(startYearValue, "Start year");
    if (startError) return startError;
    const endError = validateYearField(endYearValue, "End year");
    if (endError) return endError;
    const trimmedStart = startYearValue.trim();
    const trimmedEnd = endYearValue.trim();
    if (trimmedStart && trimmedEnd && Number(trimmedStart) > Number(trimmedEnd)) {
      return "Start year must be earlier than or equal to end year.";
    }
    return null;
  }

  function applyFilters() {
    const error = validateDraftFilters(draftStartYear, draftEndYear);
    if (error) {
      setFilterError(error);
      return;
    }
    setFilterError(null);
    setFilterCategory(draftCategory);
    setFilterStartYear(draftStartYear.trim());
    setFilterEndYear(draftEndYear.trim());
    // Sync Deep Dive to the newly-applied global category so the two
    // don't visibly disagree right after Apply. Deep Dive stays an
    // independent control after this: the user can change it manually
    // afterward without that choice being overwritten until the next
    // Apply with a non-empty category.
    if (draftCategory) {
      setSelectedCategory(draftCategory);
    }
  }

  function resetFilters() {
    setDraftCategory("");
    setDraftStartYear("");
    setDraftEndYear("");
    setFilterCategory("");
    setFilterStartYear("");
    setFilterEndYear("");
    setFilterError(null);
    setSelectedCategory(DEFAULT_DEEP_DIVE_CATEGORY);
  }

  useEffect(() => {
    const controller = new AbortController();
    setGlobalStatus("loading");
    const filters = { category: filterCategory, startYear: filterStartYear, endYear: filterEndYear, signal: controller.signal };
    Promise.all([
      getAnalyticsSummary(filters),
      getAnalyticsCategoryCounts({ startYear: filterStartYear, endYear: filterEndYear, signal: controller.signal }),
      getAnalyticsPrizesByDecade(filters),
      getAnalyticsTopCountries({ limit: ALL_COUNTRIES_LIMIT, ...filters }),
      getAnalyticsAgeDistribution(filters),
      getAnalyticsWomenByEra(filters),
      getCategories({ signal: controller.signal }),
    ]).then(([summaryData, categoryData, decadeData, countryData, ageData, womenData, categoryOptions]) => {
      setSummary(summaryData);
      setCategoryCounts(categoryData);
      setPrizesByDecade(decadeData);
      setTopCountries(countryData);
      setAgeDistribution(ageData);
      setWomenByEra(womenData);
      setCategories(categoryOptions);
      if (!categoryOptions.some((item) => item.name === selectedCategory) && categoryOptions[0]) {
        setSelectedCategory(categoryOptions[0].name);
      }
      setGlobalStatus("success");
    }).catch((error) => {
      if (error.name !== "AbortError") {
        console.error("Unable to load analytics overview", error);
        setGlobalStatus("error");
      }
    });
    return () => controller.abort();
  }, [retryKey, filterCategory, filterStartYear, filterEndYear]);

  useEffect(() => {
    const controller = new AbortController();
    setCategoryStatus("loading");
    getAnalyticsForCategory(selectedCategory, { signal: controller.signal })
      .then((data) => { setCategoryAnalytics(data); setCategoryStatus("success"); })
      .catch((error) => {
        if (error.name !== "AbortError") {
          console.error("Unable to load category analytics", error);
          setCategoryStatus("error");
        }
      });
    return () => controller.abort();
  }, [selectedCategory, retryKey]);

  const personGenderTotal = useMemo(
    () => categoryAnalytics?.gender.reduce((sum, item) => sum + item.laureate_count, 0) || 0,
    [categoryAnalytics],
  );

  if (globalStatus === "error") {
    return <div className="analytics-page container"><div className="analytics-state" role="alert"><h1>Analytics are temporarily unavailable.</h1><button className="button button-primary" onClick={() => setRetryKey((key) => key + 1)} type="button">Try again</button></div></div>;
  }

  return (
    <div className="analytics-page">
      <header className="analytics-hero container">
        <div>
          <p className="eyebrow">Explore the data. Ask questions. Discover patterns.</p>
          <h1>Nobel Analytics ✨</h1>
          <p>Be inspired by a century of discovery, told through the numbers.</p>
        </div>
      </header>

      <section className="analytics-filter-bar container" aria-label="Filter dashboard totals and trends">
        <label className="analytics-category-control" htmlFor="dashboard-filter-category">
          Category
          <select id="dashboard-filter-category" value={draftCategory} onChange={(event) => setDraftCategory(event.target.value)}>
            <option value="">All categories</option>
            {categories.map((category) => <option key={category.category_id} value={category.name}>{category.name}</option>)}
          </select>
        </label>
        <label className="analytics-category-control" htmlFor="dashboard-filter-start-year">
          Start year
          <input id="dashboard-filter-start-year" type="text" inputMode="numeric" maxLength={4} placeholder="e.g. 1950" value={draftStartYear} onChange={(event) => setDraftStartYear(event.target.value)} />
        </label>
        <label className="analytics-category-control" htmlFor="dashboard-filter-end-year">
          End year
          <input id="dashboard-filter-end-year" type="text" inputMode="numeric" maxLength={4} placeholder="e.g. 2000" value={draftEndYear} onChange={(event) => setDraftEndYear(event.target.value)} />
        </label>
        <div className="analytics-filter-actions">
          <button className="button button-primary" type="button" onClick={applyFilters}>
            Apply Filters
          </button>
          <button className="button button-secondary" type="button" onClick={resetFilters} disabled={!hasDraftOrAppliedFilters}>
            Reset
          </button>
        </div>
        {filterError && <p className="analytics-filter-error" role="alert">{filterError}</p>}
      </section>

      {globalStatus === "loading" ? <div className="analytics-loading container" role="status">Loading Nobel analytics…</div> : (
        <main className="analytics-dashboard container">
          <section className="analytics-metrics" aria-label="Nobel Explorer totals">
            <MetricCard icon="🏆" label="Nobel Prizes" value={summary.total_prizes.toLocaleString()} detail="Awarded since 1901" />
            <MetricCard icon="👥" label="Laureates" value={summary.total_laureates.toLocaleString()} detail="Laureates honored (people and organizations)" />
            <MetricCard icon="🌍" label="Countries" value={summary.total_countries.toLocaleString()} detail="Represented" />
            <MetricCard icon="👩" label="Women Laureates" value={summary.women_laureates.toLocaleString()} detail={`${summary.women_percentage}% of total`} />
          </section>

          <section className="analytics-grid analytics-grid-top">
            <article className="analytics-panel" id="prizes-through-time"><header><div><p className="panel-kicker">{formatFilterEyebrow(filterCategory, filterStartYear, filterEndYear)}</p><h2>Nobel Prizes Through Time</h2></div></header><TrendLineChart data={prizesByDecade} xKey="decade" yKey="prize_count" formatX={(decade) => `${decade}s`} formatY={(count) => count} ariaLabel="Number of prizes awarded per decade" emptyMessage="No decade data is available." height={360} /></article>
            <article className="analytics-panel analytics-panel-wide" id="category-donut"><header><div><p className="panel-kicker">{formatCategoryComparisonEyebrow(filterStartYear, filterEndYear)}</p><h2>Laureates by Category</h2><p className="panel-note">All categories shown for comparison.</p></div></header><CategoryDonut data={categoryCounts} /></article>
          </section>

          <section className="analytics-grid analytics-grid-trends">
            <article className="analytics-panel" id="women-trend"><header><div><p className="panel-kicker">{formatFilterEyebrow(filterCategory, filterStartYear, filterEndYear)}</p><h2>Women in Nobel History</h2><p className="panel-note">Share of women among laureates with known gender, by era. Organizations excluded.</p></div></header><TrendLineChart data={womenByEra} xKey="era" yKey="percentage" formatX={(era) => era} formatY={(percentage) => `${percentage}%`} formatTooltip={(point) => `${point.era}: ${point.percentage}% (${point.women_count} of ${point.known_gender_count} known-gender laureates)`} ariaLabel="Percentage of known-gender person laureates who are women, by era" emptyMessage="No gender history data is available." /></article>
            <article className="analytics-panel" id="age-distribution"><header><div><p className="panel-kicker">{formatFilterEyebrow(filterCategory, filterStartYear, filterEndYear)}</p><h2>Age at the Time of Award</h2><p className="panel-note">Approximate age (award year minus birth year). Repeat winners may appear in more than one group.</p></div></header><AgeBarChart data={ageDistribution} /></article>
          </section>

          <section aria-labelledby="global-impact-title">
            <div className="analytics-section-heading">
              <p className="panel-kicker">Where laureates come from</p>
              <h2 id="global-impact-title">Explore Nobel Laureates Around the World</h2>
              <p className="panel-note">See where Nobel laureates were born and explore their global representation.</p>
            </div>
            <article className="analytics-panel analytics-panel-wide" id="geography-explorer"><header><div><p className="panel-kicker">{formatFilterEyebrow(filterCategory, filterStartYear, filterEndYear)}</p></div></header><Suspense fallback={<p className="analytics-loading geo-explorer-loading" role="status">Loading world map…</p>}><GeographyExplorer data={topCountries} emptyMessage="No country data is available." /></Suspense></article>
          </section>

          <section className="analytics-subsection-header">
            <div>
              <p className="panel-kicker">{selectedCategory} · All years</p>
              <h2>Explore One Category in Depth</h2>
              <p className="panel-note">Category detail uses all available years.</p>
            </div>
            <label className="analytics-category-control" htmlFor="deep-dive-category">
              Category
              <select id="deep-dive-category" value={selectedCategory} onChange={(event) => setSelectedCategory(event.target.value)} disabled={!categories.length}>
                {categories.map((category) => <option key={category.category_id} value={category.name}>{category.name}</option>)}
              </select>
            </label>
          </section>

          {categoryStatus === "loading" && <div className="analytics-loading" role="status">Loading {selectedCategory} insights…</div>}
          {categoryStatus === "error" && <div className="analytics-state" role="alert"><p>Could not load {selectedCategory} insights.</p><button className="button button-secondary" onClick={() => setRetryKey((key) => key + 1)} type="button">Retry</button></div>}
          {categoryStatus === "success" && (
            <div className="analytics-deep-dive" aria-label={`${selectedCategory} analytics`}>
              <DeepDiveTabs activeTab={deepDiveTab} onChange={setDeepDiveTab} />
              <div
                className="analytics-panel"
                id={`deep-dive-panel-${deepDiveTab}`}
                role="tabpanel"
                aria-labelledby={`deep-dive-tab-${deepDiveTab}`}
              >
                {deepDiveTab === "countries" && (
                  <>
                    <header><div><p className="panel-kicker">Birthplace</p><h2>{selectedCategory}: top countries</h2></div></header>
                    <RankedBars data={categoryAnalytics.countries} labelKey="country" emptyMessage="No birthplace country data is available." limit={5} showFlag />
                  </>
                )}
                {deepDiveTab === "states" && (
                  <>
                    <header><div><p className="panel-kicker">USA birthplace</p><h2>{selectedCategory}: top states</h2></div></header>
                    <RankedBars data={categoryAnalytics.states} labelKey="state" emptyMessage="No U.S. state data is available." limit={5} />
                  </>
                )}
                {deepDiveTab === "institutions" && (
                  <>
                    <header><div><p className="panel-kicker">Award-time affiliations</p><h2>{selectedCategory}: top U.S. institutions</h2></div></header>
                    <RankedBars data={categoryAnalytics.institutions} labelKey="institution" emptyMessage="No U.S. institution data is available." limit={5} />
                  </>
                )}
                {deepDiveTab === "gender" && (
                  <>
                    <header><div><p className="panel-kicker">Known person records</p><h2>{selectedCategory}: gender distribution</h2></div><span className="panel-total">{personGenderTotal}</span></header>
                    <RankedBars data={categoryAnalytics.gender} labelKey="gender" emptyMessage="No gender data is available." limit={6} />
                  </>
                )}
              </div>
            </div>
          )}

          <DidYouKnow />
        </main>
      )}
    </div>
  );
}

export default AnalyticsPage;
