import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import AwardLaureateCard from "../components/laureates/AwardLaureateCard";
import PrizePageState from "../components/prizes/PrizePageState";
import { getLaureates, getPrizeById } from "../services/api";

function PrizeDetailPage() {
  const { prizeId } = useParams();
  const [prize, setPrize] = useState(null);
  const [laureates, setLaureates] = useState([]);
  const [status, setStatus] = useState("loading");
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setStatus("loading");

    getPrizeById(prizeId, { signal: controller.signal })
      .then(async (prizeDetail) => {
        // Prize detail scopes share/motivation/affiliations to this exact
        // award, but not portrait/birth country — merge in the laureate
        // list the same way CategoryYearResults does, in one extra request.
        const laureateList = await getLaureates({
          limit: 100,
          category: prizeDetail.category.name,
          year: prizeDetail.year,
          signal: controller.signal,
        });

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

        setPrize(prizeDetail);
        setLaureates(merged);
        setStatus("success");
      })
      .catch((error) => {
        if (error.name === "AbortError") return;
        console.error("Unable to load Nobel Prize detail", error);
        setStatus(error.status === 404 ? "not-found" : "error");
      });

    return () => controller.abort();
  }, [prizeId, retryKey]);

  if (status === "loading") {
    return (
      <div className="prize-detail-page">
        <div className="container">
          <span className="visually-hidden" role="status">Loading prize details</span>
          <div className="prize-detail-header-skeleton" aria-hidden="true">
            <div className="skeleton-line skeleton-line-short" />
            <div className="skeleton-line skeleton-line-medium" />
          </div>
          <div className="laureate-grid" aria-hidden="true">
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
        </div>
      </div>
    );
  }

  if (status === "not-found") {
    return <div className="container"><PrizePageState title="Prize not found">We couldn’t find a Nobel Prize with that identifier.</PrizePageState></div>;
  }

  if (status === "error") {
    return <div className="container"><PrizePageState title="We couldn’t load this prize" retry={() => setRetryKey((key) => key + 1)}>Please check the connection and try again.</PrizePageState></div>;
  }

  return (
    <div className="prize-detail-page">
      <header className="category-year-hero">
        <div className="container">
          <Link className="back-link" to="/prizes">← Back to Prizes</Link>
          <p className="eyebrow">Nobel Prize</p>
          <h1>{prize.category.name} — {prize.year}</h1>
          <p>Explore each laureate’s award share, motivation, and affiliations.</p>
        </div>
      </header>

      <section className="laureates-content container" aria-labelledby="prize-laureates-title">
        <div className="results-heading">
          <h2 id="prize-laureates-title">Laureates</h2>
          <p aria-live="polite">
            {laureates.length} {laureates.length === 1 ? "result" : "results"}
          </p>
        </div>
        <div className="laureate-grid">
          {laureates.map((laureate) => (
            <AwardLaureateCard laureate={laureate} key={laureate.laureate_id} />
          ))}
        </div>
      </section>
    </div>
  );
}

export default PrizeDetailPage;
