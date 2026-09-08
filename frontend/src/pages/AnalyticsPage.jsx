import { useEffect, useMemo, useState } from "react";

import {
  getAnalyticsAgeDistribution,
  getAnalyticsCategoriesByDecade,
  getAnalyticsCategoryCounts,
  getAnalyticsForCategory,
  getAnalyticsPrizesByDecade,
  getAnalyticsSummary,
  getAnalyticsTopCountries,
  getAnalyticsWomenByEra,
  getCategories,
} from "../services/api";
import { getCountryFlag } from "../utils/countryFlags";

const CHART_COLORS = ["#7c4dff", "#b339e7", "#f04468", "#e8b83e", "#72c77b", "#43c1b5"];

const DISCOVERY_QUESTIONS = [
  { icon: "🌍", question: "Which countries have the most Nobel laureates?", target: "#top-countries" },
  { icon: "🏆", question: "Which category has the most Nobel Prizes?", target: "#category-donut" },
  { icon: "♀", question: "Has the number of women Nobel laureates changed over time?", target: "#women-trend" },
  { icon: "🎂", question: "What age are scientists typically when they receive a Nobel Prize?", target: "#age-distribution" },
  { icon: "📈", question: "Are more Nobel Prizes being awarded today than in the past?", target: "#prizes-through-time" },
  { icon: "🔬", question: "How has Nobel recognition across fields changed over time?", target: "#categories-through-time" },
];

const DID_YOU_KNOW_FACTS = [
  "Marie Curie is the only person to win Nobel Prizes in two different sciences: Physics (1903) and Chemistry (1911).",
  "The youngest Nobel laureate was Malala Yousafzai, who was 17 years old when she won the Peace Prize in 2014.",
  "Linus Pauling is the only person to have won two unshared Nobel Prizes: Chemistry (1954) and Peace (1962).",
  "The Nobel Memorial Prize in Economic Sciences was added in 1968 and isn't one of the five original prizes from Alfred Nobel's will.",
  "In 1974, the Nobel Foundation decided prizes generally cannot be awarded posthumously.",
];

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

function TrendLineChart({ data, xKey, yKey, formatX, formatY, formatTooltip, ariaLabel, emptyMessage }) {
  const width = 720;
  const height = 230;
  const maximum = Math.max(...data.map((item) => item[yKey]), 1);
  const points = data.map((item, index) => {
    const x = data.length === 1 ? width / 2 : 20 + (index / (data.length - 1)) * (width - 40);
    const y = height - 32 - (item[yKey] / maximum) * (height - 60);
    return { ...item, x, y };
  });

  if (!data.length) return <p className="analytics-empty">{emptyMessage}</p>;

  return (
    <div className="decade-chart">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel}>
        <line className="chart-axis" x1="20" x2={width - 20} y1={height - 32} y2={height - 32} />
        <polyline className="chart-line" points={points.map(({ x, y }) => `${x},${y}`).join(" ")} />
        {points.map((point, index) => (
          <g key={point[xKey]}>
            <circle className="chart-point" cx={point.x} cy={point.y} r="5">
              <title>{formatTooltip ? formatTooltip(point) : `${formatX(point[xKey])}: ${formatY(point[yKey])}`}</title>
            </circle>
            <text x={point.x} y={point.y - 14} textAnchor="middle" className="chart-point-value">{formatY(point[yKey])}</text>
            {(data.length <= 6 || index % 2 === 0 || index === points.length - 1) && (
              <text x={point.x} y={height - 10} textAnchor="middle">{formatX(point[xKey])}</text>
            )}
          </g>
        ))}
      </svg>
    </div>
  );
}

function CategoryTrendChart({ data, categoryColors, emptyMessage }) {
  const width = 720;
  const height = 230;

  if (!data.length) return <p className="analytics-empty">{emptyMessage}</p>;

  const decades = [...new Set(data.map((item) => item.decade))].sort((a, b) => a - b);
  const categoryNames = [...new Set(data.map((item) => item.category))];
  const lookup = new Map(data.map((item) => [`${item.decade}|${item.category}`, item.laureate_count]));
  const maximum = Math.max(...data.map((item) => item.laureate_count), 1);

  const xFor = (index) => (decades.length === 1 ? width / 2 : 20 + (index / (decades.length - 1)) * (width - 40));
  const yFor = (count) => height - 32 - (count / maximum) * (height - 60);

  const series = categoryNames.map((category) => ({
    category,
    color: categoryColors[category] || "#7c4dff",
    points: decades.map((decade, index) => {
      const count = lookup.get(`${decade}|${category}`) || 0;
      return { decade, count, x: xFor(index), y: yFor(count) };
    }),
  }));

  return (
    <div className="decade-chart">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Distinct laureates per category, by decade">
        <line className="chart-axis" x1="20" x2={width - 20} y1={height - 32} y2={height - 32} />
        {series.map((line) => (
          <g key={line.category}>
            <polyline className="chart-line" style={{ stroke: line.color }} points={line.points.map(({ x, y }) => `${x},${y}`).join(" ")} />
            {line.points.map((point) => (
              <circle className="category-trend-point" key={point.decade} cx={point.x} cy={point.y} r="3.5" style={{ fill: line.color }}>
                <title>{line.category}, {point.decade}s: {point.count} laureates</title>
              </circle>
            ))}
          </g>
        ))}
        {decades.map((decade, index) => (
          (decades.length <= 8 || index % 2 === 0 || index === decades.length - 1) && (
            <text key={decade} x={xFor(index)} y={height - 10} textAnchor="middle">{decade}s</text>
          )
        ))}
      </svg>
      <ul className="analytics-legend-inline">
        {series.map((line) => (
          <li key={line.category}>
            <i style={{ background: line.color }} />
            <span>{line.category}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function AgeBarChart({ data }) {
  const maximum = Math.max(...data.map((item) => item.percentage), 1);

  if (!data.length) return <p className="analytics-empty">No age data is available.</p>;

  return (
    <div className="age-bar-chart" role="img" aria-label="Distribution of award-age observations by approximate age group; a repeat winner may contribute more than one observation">
      {data.map((item) => (
        <div className="age-bar-column" key={item.age_group}>
          <span className="age-bar-value">{item.percentage}%</span>
          <span className="age-bar-track">
            <span style={{ height: `${(item.percentage / maximum) * 100}%` }} />
          </span>
          <span className="age-bar-label">{item.age_group}</span>
        </div>
      ))}
    </div>
  );
}

function DiscoveryQuestions() {
  return (
    <section className="discovery-section" aria-label="What can you discover from the data">
      <h2>🔎 What can you discover from the data?</h2>
      <div className="discovery-grid">
        {DISCOVERY_QUESTIONS.map((item) => (
          <a className="discovery-card" href={item.target} key={item.question}>
            <span aria-hidden="true">{item.icon}</span>
            <p>{item.question}</p>
          </a>
        ))}
      </div>
    </section>
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

function AnalyticsPage() {
  const [summary, setSummary] = useState(null);
  const [categoryCounts, setCategoryCounts] = useState([]);
  const [prizesByDecade, setPrizesByDecade] = useState([]);
  const [topCountries, setTopCountries] = useState([]);
  const [ageDistribution, setAgeDistribution] = useState([]);
  const [womenByEra, setWomenByEra] = useState([]);
  const [categoriesByDecade, setCategoriesByDecade] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState("Physics");
  const [categoryAnalytics, setCategoryAnalytics] = useState(null);
  const [globalStatus, setGlobalStatus] = useState("loading");
  const [categoryStatus, setCategoryStatus] = useState("loading");
  const [retryKey, setRetryKey] = useState(0);

  // Phase 10D: the small, consistent dashboard-wide filter set. Empty
  // string means "no filter" for all three -- this is intentionally
  // separate from `selectedCategory` below, which always holds a real
  // category and drives the category-required deep-dive section further
  // down the page.
  const [filterCategory, setFilterCategory] = useState("");
  const [filterStartYear, setFilterStartYear] = useState("");
  const [filterEndYear, setFilterEndYear] = useState("");

  const yearRangeInvalid = Boolean(
    filterStartYear && filterEndYear && Number(filterStartYear) > Number(filterEndYear),
  );

  const resetFilters = () => {
    setFilterCategory("");
    setFilterStartYear("");
    setFilterEndYear("");
  };

  useEffect(() => {
    if (yearRangeInvalid) {
      // If an in-flight request from a previous (valid) filter change
      // gets aborted by this effect re-running, its AbortError is
      // swallowed below and never resolves globalStatus out of
      // "loading" -- without this, an invalid range typed right after a
      // valid one could leave the page stuck on the loading spinner
      // forever. Falling back to "success" re-shows the last good
      // dashboard (with the inline range error already visible above
      // it) instead of a permanent spinner; only do this once real data
      // exists, so the very first page load never renders `summary` etc.
      // while still null.
      if (summary) setGlobalStatus("success");
      return undefined;
    }

    const controller = new AbortController();
    setGlobalStatus("loading");
    const filters = { category: filterCategory, startYear: filterStartYear, endYear: filterEndYear, signal: controller.signal };
    Promise.all([
      getAnalyticsSummary({ signal: controller.signal }),
      getAnalyticsCategoryCounts({ startYear: filterStartYear, endYear: filterEndYear, signal: controller.signal }),
      getAnalyticsPrizesByDecade(filters),
      getAnalyticsTopCountries({ limit: 5, ...filters }),
      getAnalyticsAgeDistribution(filters),
      getAnalyticsWomenByEra(filters),
      getAnalyticsCategoriesByDecade(filters),
      getCategories({ signal: controller.signal }),
    ]).then(([summaryData, categoryData, decadeData, countryData, ageData, womenData, categoryDecadeData, categoryOptions]) => {
      setSummary(summaryData);
      setCategoryCounts(categoryData);
      setPrizesByDecade(decadeData);
      setTopCountries(countryData);
      setAgeDistribution(ageData);
      setWomenByEra(womenData);
      setCategoriesByDecade(categoryDecadeData);
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
  }, [retryKey, filterCategory, filterStartYear, filterEndYear, yearRangeInvalid]);

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

  // Shared category -> color mapping so the donut and the categories-
  // by-decade trend chart use the same color for the same category.
  const categoryColors = useMemo(
    () => Object.fromEntries(categoryCounts.map((item, index) => [item.category, CHART_COLORS[index % CHART_COLORS.length]])),
    [categoryCounts],
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
        <label className="analytics-category-control">Explore category<select value={selectedCategory} onChange={(event) => setSelectedCategory(event.target.value)} disabled={!categories.length}>{categories.map((category) => <option key={category.category_id} value={category.name}>{category.name}</option>)}</select></label>
      </header>

      <section className="analytics-filter-bar container" aria-label="Filter dashboard totals and trends">
        <label className="analytics-category-control" htmlFor="dashboard-filter-category">
          Category
          <select id="dashboard-filter-category" value={filterCategory} onChange={(event) => setFilterCategory(event.target.value)}>
            <option value="">All categories</option>
            {categories.map((category) => <option key={category.category_id} value={category.name}>{category.name}</option>)}
          </select>
        </label>
        <label className="analytics-category-control" htmlFor="dashboard-filter-start-year">
          Start year
          <input id="dashboard-filter-start-year" type="number" inputMode="numeric" min="1901" max="2100" placeholder="e.g. 1950" value={filterStartYear} onChange={(event) => setFilterStartYear(event.target.value)} />
        </label>
        <label className="analytics-category-control" htmlFor="dashboard-filter-end-year">
          End year
          <input id="dashboard-filter-end-year" type="number" inputMode="numeric" min="1901" max="2100" placeholder="e.g. 2000" value={filterEndYear} onChange={(event) => setFilterEndYear(event.target.value)} />
        </label>
        <div className="analytics-filter-actions">
          <button className="button button-secondary" type="button" onClick={resetFilters} disabled={!filterCategory && !filterStartYear && !filterEndYear}>
            Reset
          </button>
        </div>
        {yearRangeInvalid && <p className="analytics-filter-error" role="alert">Start year must be on or before end year.</p>}
      </section>

      {globalStatus === "loading" ? <div className="analytics-loading container" role="status">Loading Nobel analytics…</div> : (
        <main className="analytics-dashboard container">
          <section className="analytics-metrics" aria-label="Nobel Explorer totals">
            <MetricCard icon="🏆" label="Nobel Prizes" value={summary.total_prizes.toLocaleString()} detail="Awarded since 1901" />
            <MetricCard icon="👥" label="Laureates" value={summary.total_laureates.toLocaleString()} detail="Laureates honored (people and organizations)" />
            <MetricCard icon="🌍" label="Countries" value={summary.total_countries.toLocaleString()} detail="Represented" />
            <MetricCard icon="♀" label="Women Laureates" value={summary.women_laureates.toLocaleString()} detail={`${summary.women_percentage}% of total`} />
          </section>

          <section className="analytics-grid analytics-grid-top">
            <article className="analytics-panel" id="prizes-through-time"><header><div><p className="panel-kicker">1901–present</p><h2>Nobel Prizes Through Time</h2></div></header><TrendLineChart data={prizesByDecade} xKey="decade" yKey="prize_count" formatX={(decade) => `${decade}s`} formatY={(count) => count} ariaLabel="Number of prizes awarded per decade" emptyMessage="No decade data is available." /></article>
            <article className="analytics-panel analytics-panel-wide" id="category-donut"><header><div><p className="panel-kicker">All categories</p><h2>Laureates by Category</h2></div></header><CategoryDonut data={categoryCounts} /></article>
          </section>

          <section className="analytics-grid analytics-grid-single" id="categories-through-time">
            <article className="analytics-panel">
              <header><div><p className="panel-kicker">{filterCategory || "All categories"}</p><h2>Nobel Recognition Across Fields</h2><p className="panel-note">Distinct laureates per category, by decade{filterCategory ? "" : " (use the Category filter above to focus on one field)"}.</p></div></header>
              <CategoryTrendChart data={categoriesByDecade} categoryColors={categoryColors} emptyMessage="No category-by-decade data is available." />
            </article>
          </section>

          <section className="analytics-grid analytics-grid-trends">
            <article className="analytics-panel" id="women-trend"><header><div><p className="panel-kicker">1901–present</p><h2>Women in Nobel History</h2><p className="panel-note">Share of women among laureates with known gender, by era. Organizations excluded.</p></div></header><TrendLineChart data={womenByEra} xKey="era" yKey="percentage" formatX={(era) => era} formatY={(percentage) => `${percentage}%`} formatTooltip={(point) => `${point.era}: ${point.percentage}% (${point.women_count} of ${point.known_gender_count} known-gender laureates)`} ariaLabel="Percentage of known-gender person laureates who are women, by era" emptyMessage="No gender history data is available." /></article>
            <article className="analytics-panel" id="age-distribution"><header><div><p className="panel-kicker">All categories</p><h2>Age at the Time of Award</h2><p className="panel-note">Approximate age (award year minus birth year). Repeat winners may appear in more than one group.</p></div></header><AgeBarChart data={ageDistribution} /></article>
          </section>

          <section className="analytics-grid analytics-grid-single" id="top-countries">
            <article className="analytics-panel"><header><div><p className="panel-kicker">Birthplace</p><h2>Top Countries by Laureates</h2></div></header><RankedBars data={topCountries} labelKey="country" emptyMessage="No country data is available." limit={5} showRank showFlag /></article>
          </section>

          {categoryStatus === "loading" && <div className="analytics-loading" role="status">Loading {selectedCategory} insights…</div>}
          {categoryStatus === "error" && <div className="analytics-state" role="alert"><p>Could not load {selectedCategory} insights.</p><button className="button button-secondary" onClick={() => setRetryKey((key) => key + 1)} type="button">Retry</button></div>}
          {categoryStatus === "success" && (
            <section className="analytics-grid analytics-grid-details" aria-label={`${selectedCategory} analytics`}>
              <article className="analytics-panel"><header><div><p className="panel-kicker">Birthplace</p><h2>{selectedCategory}: top countries</h2></div></header><RankedBars data={categoryAnalytics.countries} labelKey="country" emptyMessage="No birthplace country data is available." showFlag /></article>
              <article className="analytics-panel"><header><div><p className="panel-kicker">USA birthplace</p><h2>{selectedCategory}: top states</h2></div></header><RankedBars data={categoryAnalytics.states} labelKey="state" emptyMessage="No U.S. state data is available." /></article>
              <article className="analytics-panel"><header><div><p className="panel-kicker">Award-time affiliations</p><h2>{selectedCategory}: top U.S. institutions</h2></div></header><RankedBars data={categoryAnalytics.institutions} labelKey="institution" emptyMessage="No U.S. institution data is available." /></article>
              <article className="analytics-panel"><header><div><p className="panel-kicker">Known person records</p><h2>{selectedCategory}: gender distribution</h2></div><span className="panel-total">{personGenderTotal}</span></header><RankedBars data={categoryAnalytics.gender} labelKey="gender" emptyMessage="No gender data is available." limit={6} /></article>
            </section>
          )}

          <DiscoveryQuestions />
          <DidYouKnow />
        </main>
      )}
    </div>
  );
}

export default AnalyticsPage;
