import { useEffect, useState } from "react";

import LaureateCard from "../components/laureates/LaureateCard";
import { getCategories, getLaureates } from "../services/api";

const PAGE_SIZE = 20;
const EMPTY_FILTERS = {
  search: "",
  category: "",
  year: "",
  country: "",
  gender: "",
};

function LoadingCards() {
  return (
    <div className="laureate-grid" aria-hidden="true">
      {Array.from({ length: 6 }, (_, index) => (
        <div className="laureate-skeleton" key={index}>
          <div className="laureate-skeleton-top">
            <div className="skeleton-portrait" />
            <div className="laureate-skeleton-lines">
              <div className="skeleton-line skeleton-line-medium" />
              <div className="skeleton-line skeleton-line-short" />
              <div className="skeleton-line skeleton-line-short" />
            </div>
          </div>
          <div className="skeleton-line skeleton-line-cta" />
        </div>
      ))}
    </div>
  );
}

function LaureatesPage() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [categories, setCategories] = useState([]);
  const [laureates, setLaureates] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    getCategories({ signal: controller.signal })
      .then(setCategories)
      .catch((requestError) => {
        if (requestError.name !== "AbortError") {
          console.error("Unable to load Nobel Prize categories", requestError);
        }
      });

    return () => controller.abort();
  }, []);

  useEffect(() => {
    const debounceTimer = window.setTimeout(() => {
      setDebouncedSearch(filters.search.trim());
      setPage(1);
    }, 400);

    return () => window.clearTimeout(debounceTimer);
  }, [filters.search]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(false);

    getLaureates({
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
      search: debouncedSearch,
      category: filters.category,
      year: filters.year,
      country: filters.country,
      gender: filters.gender,
      signal: controller.signal,
    })
      .then((data) => {
        setLaureates(data.items);
        setTotal(data.total);
      })
      .catch((requestError) => {
        if (requestError.name !== "AbortError") {
          console.error("Unable to load Nobel Laureates", requestError);
          setError(true);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [debouncedSearch, filters.category, filters.country, filters.gender, filters.year, page, retryKey]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const filtersActive = Object.values(filters).some((value) => value !== "");

  function updateFilter(name, value) {
    setFilters((current) => ({ ...current, [name]: value }));
    if (name !== "search") {
      setPage(1);
    }
  }

  function clearFilters() {
    setFilters(EMPTY_FILTERS);
    setDebouncedSearch("");
    setPage(1);
  }

  return (
    <div className="laureates-page">
      <header className="laureates-header">
        <div className="container">
          <p className="eyebrow">People and organizations</p>
          <h1>Explore Nobel Laureates</h1>
          <p>Discover the people and organizations behind Nobel-winning work.</p>
        </div>
      </header>

      <section className="laureates-content container" aria-labelledby="laureate-results-title">
        <form className="laureate-filters" onSubmit={(event) => event.preventDefault()}>
          <div className="filter-field filter-search">
            <label htmlFor="laureate-search">Search by name</label>
            <input
              id="laureate-search"
              type="search"
              value={filters.search}
              placeholder="Try Marie Curie"
              onChange={(event) => updateFilter("search", event.target.value)}
            />
          </div>

          <div className="filter-field">
            <label htmlFor="category-filter">Category</label>
            <select
              id="category-filter"
              value={filters.category}
              onChange={(event) => updateFilter("category", event.target.value)}
            >
              <option value="">All categories</option>
              {categories.map((category) => (
                <option value={category.name} key={category.category_id}>
                  {category.name}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-field">
            <label htmlFor="year-filter">Award year</label>
            <input
              id="year-filter"
              type="number"
              min="1901"
              max="2025"
              value={filters.year}
              placeholder="Any year"
              onChange={(event) => updateFilter("year", event.target.value)}
            />
          </div>

          <div className="filter-field">
            <label htmlFor="country-filter">Birth country</label>
            <input
              id="country-filter"
              type="text"
              value={filters.country}
              placeholder="Try USA"
              onChange={(event) => updateFilter("country", event.target.value)}
            />
          </div>

          <div className="filter-field">
            <label htmlFor="gender-filter">Gender</label>
            <select
              id="gender-filter"
              value={filters.gender}
              onChange={(event) => updateFilter("gender", event.target.value)}
            >
              <option value="">All genders</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
            </select>
          </div>

          <button
            className="clear-filters"
            type="button"
            disabled={!filtersActive}
            onClick={clearFilters}
          >
            Clear Filters
          </button>
        </form>

        <div className="results-heading">
          <h2 id="laureate-results-title">Laureates</h2>
          {!loading && !error && (
            <p aria-live="polite">{total.toLocaleString()} results</p>
          )}
        </div>

        {loading && (
          <div role="status" aria-live="polite">
            <span className="visually-hidden">Loading laureates</span>
            <LoadingCards />
          </div>
        )}

        {!loading && error && (
          <div className="laureate-message" role="alert">
            <h2>We couldn’t load the laureates.</h2>
            <p>Please check the connection and try again.</p>
            <button className="button button-primary" type="button" onClick={() => setRetryKey((key) => key + 1)}>
              Retry
            </button>
          </div>
        )}

        {!loading && !error && laureates.length === 0 && (
          <div className="laureate-message">
            <h2>No laureates matched your search.</h2>
            <p>Try changing your search or clearing the filters.</p>
            <button className="button button-primary" type="button" onClick={clearFilters}>
              Clear Filters
            </button>
          </div>
        )}

        {!loading && !error && laureates.length > 0 && (
          <>
            <div className="laureate-grid">
              {laureates.map((laureate) => (
                <LaureateCard laureate={laureate} key={laureate.laureate_id} />
              ))}
            </div>

            <nav className="pagination" aria-label="Laureate result pages">
              <button type="button" disabled={page === 1} onClick={() => setPage((current) => current - 1)}>
                Previous
              </button>
              <span aria-live="polite">Page {page} of {totalPages}</span>
              <button type="button" disabled={page >= totalPages} onClick={() => setPage((current) => current + 1)}>
                Next
              </button>
            </nav>
          </>
        )}
      </section>
    </div>
  );
}

export default LaureatesPage;
