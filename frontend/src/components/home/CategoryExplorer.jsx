import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getCategories } from "../../services/api";

const MIN_YEAR = 1901;
const MAX_YEAR = 2025;
const CATEGORY_ORDER = [
  "Physics",
  "Chemistry",
  "Physiology or Medicine",
  "Literature",
  "Peace",
  "Economic Sciences",
];

const categoryDisplay = {
  Physics: { icon: "⚛️", label: "Physics" },
  Chemistry: { icon: "🧪", label: "Chemistry" },
  "Physiology or Medicine": { icon: "❤️", label: "Medicine" },
  Literature: { icon: "📖", label: "Literature" },
  Peace: { icon: "🕊️", label: "Peace" },
  "Economic Sciences": { icon: "📊", label: "Economic Sciences" },
};

function CategoryExplorer() {
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [selectedYear, setSelectedYear] = useState(String(MAX_YEAR));
  const [error, setError] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    getCategories({ signal: controller.signal })
      .then((categoryData) => {
        const orderedCategories = [...categoryData].sort(
          (first, second) => CATEGORY_ORDER.indexOf(first.name) - CATEGORY_ORDER.indexOf(second.name),
        );
        setCategories(orderedCategories);
        setSelectedCategory((current) => current || orderedCategories[0] || null);
      })
      .catch((requestError) => {
        if (requestError.name !== "AbortError") {
          console.error("Unable to load homepage categories", requestError);
          setError(true);
        }
      });
    return () => controller.abort();
  }, []);

  const numericYear = Number(selectedYear);
  const hasValidYear = Number.isInteger(numericYear) && numericYear >= MIN_YEAR && numericYear <= MAX_YEAR;
  const exploreTarget = selectedCategory
    ? `/categories/${selectedCategory.category_id}?year=${encodeURIComponent(selectedYear)}`
    : null;

  function normalizeYear() {
    if (!selectedYear || !Number.isFinite(numericYear)) {
      setSelectedYear(String(MAX_YEAR));
      return;
    }
    setSelectedYear(String(Math.min(MAX_YEAR, Math.max(MIN_YEAR, Math.round(numericYear)))));
  }

  return (
    <section className="home-section category-section" aria-labelledby="categories-title">
      <div className="container">
        <div className="category-explorer-panel">
          <p className="eyebrow">Pick a prize</p>
          <h2 id="categories-title">Start exploring <span aria-hidden="true">✨</span></h2>
          <p className="category-explorer-description">
            Choose a category and year, then meet the laureates who won it.
          </p>
          {categories.length > 0 && (
            <div className="category-selector-grid" role="group" aria-label="Choose a Nobel Prize category">
              {categories.map((category) => {
                const display = categoryDisplay[category.name] || { icon: "✦", label: category.name };
                const isSelected = selectedCategory?.category_id === category.category_id;
                return (
                  <button
                    aria-pressed={isSelected}
                    className={`category-selector${isSelected ? " category-selector-selected" : ""}`}
                    key={category.category_id}
                    onClick={() => setSelectedCategory(category)}
                    type="button"
                  >
                    <span className="category-selector-icon" aria-hidden="true">{display.icon}</span>
                    <span>{display.label}</span>
                    {isSelected && <span className="visually-hidden">Selected</span>}
                  </button>
                );
              })}
            </div>
          )}
          {!categories.length && !error && (
            <p className="category-loading" role="status">Loading Nobel Prize categories…</p>
          )}
          {error && (
            <p className="category-loading" role="alert">Categories are temporarily unavailable.</p>
          )}
          <div className="category-explorer-actions">
            <div className="year-selector" aria-label="Choose a Nobel Prize year">
              <button aria-label="Decrease year" disabled={!hasValidYear || numericYear <= MIN_YEAR} onClick={() => setSelectedYear(String(numericYear - 1))} type="button">−</button>
              <input
                aria-label="Nobel Prize year"
                inputMode="numeric"
                max={MAX_YEAR}
                min={MIN_YEAR}
                onBlur={normalizeYear}
                onChange={(event) => setSelectedYear(event.target.value)}
                type="number"
                value={selectedYear}
              />
              <button aria-label="Increase year" disabled={!hasValidYear || numericYear >= MAX_YEAR} onClick={() => setSelectedYear(String(numericYear + 1))} type="button">+</button>
            </div>
            {selectedCategory && hasValidYear ? (
              <Link className="category-explore-button" to={exploreTarget}>
                Meet the Laureates <span aria-hidden="true">→</span>
              </Link>
            ) : (
              <span aria-disabled="true" className="category-explore-button category-explore-button-disabled">
                Meet the Laureates <span aria-hidden="true">→</span>
              </span>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

export default CategoryExplorer;
