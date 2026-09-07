import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import PrizeCard from "../components/prizes/PrizeCard";
import { getCategories, getPrizes } from "../services/api";

const PAGE_SIZE = 20;

function PrizeSkeletons() {
  return (
    <div className="prize-grid" aria-hidden="true">
      {Array.from({ length: 6 }, (_, index) => <div className="prize-skeleton" key={index} />)}
    </div>
  );
}

function PrizesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [prizes, setPrizes] = useState([]);
  const [categories, setCategories] = useState([]);
  const [category, setCategory] = useState(() => searchParams.get("category") || "");
  const [year, setYear] = useState(() => searchParams.get("year") || "");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState("loading");
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    getCategories({ signal: controller.signal })
      .then(setCategories)
      .catch((error) => {
        if (error.name !== "AbortError") console.error("Unable to load categories", error);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setStatus("loading");
    getPrizes({
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
      category,
      year,
      signal: controller.signal,
    })
      .then((data) => {
        setPrizes(data.items);
        setTotal(data.total);
        setStatus("success");
      })
      .catch((error) => {
        if (error.name !== "AbortError") {
          console.error("Unable to load Nobel Prizes", error);
          setStatus("error");
        }
      });
    return () => controller.abort();
  }, [category, page, retryKey, year]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (year) params.set("year", year);
    setSearchParams(params, { replace: true });
  }, [category, setSearchParams, year]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  function clearFilters() {
    setCategory("");
    setYear("");
    setPage(1);
  }

  return (
    <div className="prizes-page">
      <header className="prizes-hero">
        <div className="container">
          <p className="eyebrow">A legacy of discovery</p>
          <h1>Explore Nobel Prizes</h1>
          <p>Browse Nobel awards across categories and years.</p>
        </div>
      </header>

      <section className="prizes-content container" aria-labelledby="prize-results-title">
        <form className="prize-filters" onSubmit={(event) => event.preventDefault()}>
          <div className="filter-field">
            <label htmlFor="prize-category">Category</label>
            <select id="prize-category" value={category} onChange={(event) => { setCategory(event.target.value); setPage(1); }}>
              <option value="">All categories</option>
              {categories.map((item) => <option value={item.name} key={item.category_id}>{item.name}</option>)}
            </select>
          </div>
          <div className="filter-field">
            <label htmlFor="prize-year">Award year</label>
            <input id="prize-year" type="number" min="1901" max="2025" value={year} placeholder="Any year" onChange={(event) => { setYear(event.target.value); setPage(1); }} />
          </div>
          <button className="clear-filters" type="button" disabled={!category && !year} onClick={clearFilters}>Clear Filters</button>
        </form>

        <div className="results-heading">
          <h2 id="prize-results-title">Prizes</h2>
          {status === "success" && <p aria-live="polite">{total.toLocaleString()} results</p>}
        </div>

        {status === "loading" && <div role="status"><span className="visually-hidden">Loading prizes</span><PrizeSkeletons /></div>}
        {status === "error" && (
          <div className="prize-inline-state" role="alert">
            <h2>We couldn’t load the prizes.</h2><p>Please check the connection and try again.</p>
            <button className="button button-primary" type="button" onClick={() => setRetryKey((key) => key + 1)}>Retry</button>
          </div>
        )}
        {status === "success" && prizes.length === 0 && (
          <div className="prize-inline-state"><h2>No prizes matched these filters.</h2><p>Try another category or year.</p><button className="button button-primary" type="button" onClick={clearFilters}>Clear Filters</button></div>
        )}
        {status === "success" && prizes.length > 0 && (
          <>
            <div className="prize-grid">{prizes.map((prize) => <PrizeCard prize={prize} key={prize.prize_id} />)}</div>
            <nav className="pagination" aria-label="Prize result pages">
              <button type="button" disabled={page === 1} onClick={() => setPage((value) => value - 1)}>Previous</button>
              <span aria-live="polite">Page {page} of {totalPages}</span>
              <button type="button" disabled={page >= totalPages} onClick={() => setPage((value) => value + 1)}>Next</button>
            </nav>
          </>
        )}
      </section>
    </div>
  );
}

export default PrizesPage;
