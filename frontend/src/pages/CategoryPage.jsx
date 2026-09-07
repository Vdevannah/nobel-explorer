import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import AwardLaureateCard from "../components/laureates/AwardLaureateCard";
import PrizeCard from "../components/prizes/PrizeCard";
import PrizePageState from "../components/prizes/PrizePageState";
import {
  getCategoryById,
  getLaureates,
  getPrizeById,
  getPrizes,
} from "../services/api";

const PAGE_SIZE = 20;

function CategoryYearResults({ category, year }) {
  const [laureates, setLaureates] = useState([]);
  const [status, setStatus] = useState("loading");
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setStatus("loading");

    getPrizes({
      limit: 1,
      category: category.name,
      year,
      signal: controller.signal,
    })
      .then(async (prizeList) => {
        const prizeSummary = prizeList.items[0];
        if (!prizeSummary) {
          setLaureates([]);
          setStatus("success");
          return;
        }

        // Compose two existing endpoints: prize detail gives the
        // award-specific share/motivation/affiliations scoped to this
        // exact LaureatePrize row, while the laureate list gives
        // portrait/birth country. Neither endpoint alone has both.
        const [prizeDetail, laureateList] = await Promise.all([
          getPrizeById(prizeSummary.prize_id, { signal: controller.signal }),
          getLaureates({
            limit: 100,
            category: category.name,
            year,
            signal: controller.signal,
          }),
        ]);

        const profileById = new Map(
          laureateList.items.map((item) => [item.laureate_id, item])
        );

        const merged = prizeDetail.laureates.map((awardLaureate) => {
          const profile = profileById.get(awardLaureate.laureate_id);
          return {
            ...awardLaureate,
            birth_country: profile?.birth_country ?? null,
            image_url: profile?.image_url ?? null,
          };
        });

        setLaureates(merged);
        setStatus("success");
      })
      .catch((error) => {
        if (error.name === "AbortError") return;
        console.error("Unable to load category/year laureates", error);
        setStatus("error");
      });

    return () => controller.abort();
  }, [category.category_id, category.name, retryKey, year]);

  return (
    <div className="category-page category-year-page">
      <header className="category-year-hero">
        <div className="container">
          <Link className="back-link" to="/">← Back to Home</Link>
          <p className="eyebrow">{category.name}</p>
          <h1>{category.name} — {year}</h1>
          <p>Meet the laureates awarded the Nobel Prize in {category.name} in {year}.</p>
        </div>
      </header>

      <section className="laureates-content container" aria-labelledby="category-year-results-title">
        <div className="results-heading">
          <h2 id="category-year-results-title">Laureates</h2>
          {status === "success" && (
            <p aria-live="polite">
              {laureates.length} {laureates.length === 1 ? "result" : "results"}
            </p>
          )}
        </div>

        {status === "loading" && (
          <div className="laureate-grid" role="status" aria-hidden="true">
            {Array.from({ length: 3 }, (_, index) => (
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
        )}

        {status === "error" && (
          <div className="laureate-message" role="alert">
            <h2>We couldn’t load these laureates.</h2>
            <p>Please check the connection and try again.</p>
            <button className="button button-primary" type="button" onClick={() => setRetryKey((key) => key + 1)}>
              Retry
            </button>
          </div>
        )}

        {status === "success" && laureates.length === 0 && (
          <div className="laureate-message">
            <h2>No Nobel Prize in {category.name} was awarded in {year}.</h2>
            <p>Try a different year or explore another category from the home page.</p>
            <Link className="button button-primary" to="/">Back to Home</Link>
          </div>
        )}

        {status === "success" && laureates.length > 0 && (
          <div className="laureate-grid">
            {laureates.map((laureate) => (
              <AwardLaureateCard laureate={laureate} key={laureate.laureate_id} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function CategoryPrizeBrowser({ category }) {
  const [prizes, setPrizes] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("loading");
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setStatus("loading");
    getPrizes({
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
      category: category.name,
      signal: controller.signal,
    })
      .then((data) => {
        setPrizes(data.items);
        setTotal(data.total);
        setStatus("success");
      })
      .catch((error) => {
        if (error.name === "AbortError") return;
        console.error("Unable to load category prizes", error);
        setStatus("error");
      });
    return () => controller.abort();
  }, [category.category_id, category.name, page, retryKey]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="category-page">
      <header className="category-hero">
        <div className="container category-hero-layout">
          <div>
            <Link className="back-link" to="/prizes">← Back to All Prizes</Link>
            <p className="eyebrow">Nobel Prize category</p>
            <h1>{category.name}</h1>
            {category.description && <p>{category.description}</p>}
          </div>
          <div className="category-motif" aria-hidden="true"><span>✦</span></div>
        </div>
      </header>

      <section className="prizes-content container" aria-labelledby="category-prizes-title">
        <div className="results-heading">
          <h2 id="category-prizes-title">Prizes in {category.name}</h2>
          {status === "success" && <p>{total.toLocaleString()} results</p>}
        </div>
        {status === "error" && (
          <div className="prize-inline-state" role="alert">
            <h2>We couldn’t load these prizes.</h2>
            <button className="button button-primary" type="button" onClick={() => setRetryKey((key) => key + 1)}>Retry</button>
          </div>
        )}
        {status === "success" && prizes.length > 0 && (
          <>
            <div className="prize-grid">{prizes.map((prize) => <PrizeCard prize={prize} key={prize.prize_id} />)}</div>
            <nav className="pagination" aria-label={`${category.name} prize pages`}>
              <button type="button" disabled={page === 1} onClick={() => setPage((value) => value - 1)}>Previous</button>
              <span>Page {page} of {totalPages}</span>
              <button type="button" disabled={page >= totalPages} onClick={() => setPage((value) => value + 1)}>Next</button>
            </nav>
          </>
        )}
        {status === "success" && prizes.length === 0 && (
          <div className="prize-inline-state"><h2>No prizes are available for this category.</h2></div>
        )}
      </section>
    </div>
  );
}

function CategoryPage() {
  const { categoryId } = useParams();
  const [searchParams] = useSearchParams();
  const year = searchParams.get("year");

  const [category, setCategory] = useState(null);
  const [status, setStatus] = useState("loading");
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setStatus("loading");
    getCategoryById(categoryId, { signal: controller.signal })
      .then((categoryData) => {
        setCategory(categoryData);
        setStatus("success");
      })
      .catch((error) => {
        if (error.name === "AbortError") return;
        console.error("Unable to load Nobel Prize category", error);
        setStatus(error.status === 404 ? "not-found" : "error");
      });
    return () => controller.abort();
  }, [categoryId, retryKey]);

  if (status === "loading") {
    return (
      <div className="prize-route-loading container" role="status">
        <span className="visually-hidden">Loading category</span>
        <div className="route-loading-hero" />
        <div className="prize-grid">{Array.from({ length: 6 }, (_, index) => <div className="prize-skeleton" key={index} />)}</div>
      </div>
    );
  }

  if (status === "not-found") {
    return <div className="container"><PrizePageState title="Category not found">We couldn’t find that Nobel Prize category.</PrizePageState></div>;
  }

  if (status === "error") {
    return <div className="container"><PrizePageState title="We couldn’t load this category" retry={() => setRetryKey((key) => key + 1)}>Please check the connection and try again.</PrizePageState></div>;
  }

  if (year) {
    return <CategoryYearResults category={category} year={year} />;
  }

  return <CategoryPrizeBrowser category={category} />;
}

export default CategoryPage;
