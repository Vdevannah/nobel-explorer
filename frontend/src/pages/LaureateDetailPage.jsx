import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import AwardCard from "../components/laureates/AwardCard";
import EducationalContent from "../components/laureates/EducationalContent";
import EducationalEmptyState from "../components/laureates/EducationalEmptyState";
import LaureateHero from "../components/laureates/LaureateHero";
import LaureateQuickFacts from "../components/laureates/LaureateQuickFacts";
import { getLaureateById, getLaureateContributions } from "../services/api";

function DetailSkeleton() {
  return (
    <div className="detail-skeleton" aria-hidden="true">
      <div className="detail-skeleton-portrait" />
      <div className="detail-skeleton-copy">
        <span />
        <span />
        <span />
      </div>
    </div>
  );
}

function DetailMessage({ title, children, retry }) {
  return (
    <section className="detail-message" role={retry ? "alert" : undefined}>
      <p className="eyebrow">Nobel Explorer</p>
      <h1>{title}</h1>
      <p>{children}</p>
      <div className="detail-message-actions">
        {retry && (
          <button className="button button-primary" type="button" onClick={retry}>
            Retry
          </button>
        )}
        <Link className="button button-secondary" to="/laureates">
          Back to Laureates
        </Link>
      </div>
    </section>
  );
}

function LaureateDetailPage() {
  const { laureateId } = useParams();
  const [laureate, setLaureate] = useState(null);
  const [status, setStatus] = useState("loading");
  const [retryKey, setRetryKey] = useState(0);
  const [contributions, setContributions] = useState([]);
  const [educationStatus, setEducationStatus] = useState("loading");

  useEffect(() => {
    const controller = new AbortController();
    setStatus("loading");
    setEducationStatus("loading");

    getLaureateById(laureateId, { signal: controller.signal })
      .then((data) => {
        setLaureate(data);
        setStatus("success");
      })
      .catch((requestError) => {
        if (requestError.name === "AbortError") {
          return;
        }
        console.error("Unable to load Nobel Laureate detail", requestError);
        setStatus(requestError.status === 404 ? "not-found" : "error");
      });

    getLaureateContributions(laureateId, { signal: controller.signal })
      .then((data) => {
        setContributions(data);
        setEducationStatus("success");
      })
      .catch((requestError) => {
        if (requestError.name !== "AbortError") {
          console.error("Unable to load Laureate educational content", requestError);
          setEducationStatus("error");
        }
      });

    return () => controller.abort();
  }, [laureateId, retryKey]);

  if (status === "loading") {
    return (
      <div className="detail-page container" role="status" aria-live="polite">
        <span className="visually-hidden">Loading laureate details</span>
        <DetailSkeleton />
      </div>
    );
  }

  if (status === "not-found") {
    return (
      <div className="detail-page container">
        <DetailMessage title="Laureate not found">
          We couldn’t find a Nobel Laureate with that identifier.
        </DetailMessage>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="detail-page container">
        <DetailMessage title="We couldn’t load this Laureate" retry={() => setRetryKey((key) => key + 1)}>
          Please check the connection and try again.
        </DetailMessage>
      </div>
    );
  }

  return (
    <div className="detail-page">
      <div className="container">
        <Link className="back-link" to="/laureates">← Back to Laureates</Link>

        <div id="overview"><LaureateHero laureate={laureate} /></div>

        <div className={`detail-content-layout${contributions.length ? " detail-content-layout--education" : ""}`}>
          <div className="detail-main-content">
            {laureate.awards.length > 1 && (
              <section className="awards-section" aria-labelledby="awards-title">
                <div className="detail-section-heading">
                  <p className="eyebrow">Nobel recognition</p>
                  <h2 id="awards-title">Nobel Awards</h2>
                </div>
                <div className="award-list">
                  {laureate.awards.map((award, index) => (
                    <AwardCard award={award} number={index + 1} key={award.laureate_prize_id} />
                  ))}
                </div>
              </section>
            )}

            {educationStatus === "loading" && (
              <p className="education-status" role="status">Loading educational content…</p>
            )}
            {educationStatus === "error" && (
              <EducationalEmptyState title="Educational content unavailable">
                The educational material could not be loaded, but the Laureate details remain available.
              </EducationalEmptyState>
            )}
            {educationStatus === "success" && contributions.length === 0 && (
              <EducationalEmptyState title="Educational content coming soon">
                Curated contributions and learning material have not been added for this Laureate yet.
              </EducationalEmptyState>
            )}
            {educationStatus === "success" && contributions.length > 0 && (
              <EducationalContent contributions={contributions} laureateName={laureate.full_name} />
            )}
          </div>

          <div className="detail-sidebar">
            <LaureateQuickFacts laureate={laureate} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default LaureateDetailPage;
