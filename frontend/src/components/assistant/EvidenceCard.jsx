import { Link } from "react-router-dom";

import { displayHost } from "../../utils/safeUrl";

// One normalised citation (see normalizeCitations). Only a direct source URL
// that passed safeExternalUrl becomes an external link; related sources are
// context text only and never linked.
function EvidenceCard({ card, domId }) {
  const { id, title, provenance, sourceName, source, relatedSourceName, laureateId } = card;
  const ids = card.ids?.length ? card.ids : [id];

  return (
    <li className={`assistant-evidence-card assistant-evidence-card--${provenance.key}`} id={domId} tabIndex={-1}>
      <div className="assistant-evidence-card-header">
        <span className="assistant-evidence-id">{ids.join(", ")}</span>
        <span className="assistant-evidence-title">{title}</span>
      </div>

      {ids.length > 1 && (
        <p className="assistant-evidence-grouped">
          Cited as {ids.slice(0, -1).join(", ")} and {ids.at(-1)}: the same record was returned more than once.
        </p>
      )}

      <p className="assistant-provenance">{provenance.label}</p>

      {provenance.key === "structured_record" && sourceName && (
        <p className="assistant-evidence-meta">Source: {sourceName}</p>
      )}

      {provenance.key === "source_linked" && source && (
        <p className="assistant-evidence-meta">
          Source:{" "}
          {source.url ? (
            <a
              className="assistant-source-link"
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
            >
              {source.name || displayHost(source.url)}{" "}
              <span className="visually-hidden">(opens in a new tab)</span>
            </a>
          ) : (
            <span>{source.name}</span>
          )}
        </p>
      )}

      {provenance.key === "unverified_educational" && (
        <>
          <p className="assistant-evidence-warning">Not independently verified</p>
          {relatedSourceName && (
            <p className="assistant-related-context">Related context: {relatedSourceName}</p>
          )}
        </>
      )}

      {provenance.key === "unknown" && (
        <p className="assistant-evidence-warning">Provenance was not provided for this evidence.</p>
      )}

      {laureateId !== null && (
        <p className="assistant-evidence-meta">
          {/* New tab: following the link must not unmount this page and lose
              the session-only conversation. */}
          <Link
            className="assistant-internal-link"
            to={`/laureates/${laureateId}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            View laureate profile<span className="visually-hidden">: {title} (opens in a new tab)</span>
          </Link>
        </p>
      )}
    </li>
  );
}

export default EvidenceCard;
