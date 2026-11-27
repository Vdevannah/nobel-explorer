import { Link } from "react-router-dom";

import { displayHost } from "../../utils/safeUrl";

// One normalised citation (see normalizeCitations). Only a direct source URL
// that passed safeExternalUrl becomes an external link; related sources are
// context text only and never linked.
function EvidenceCard({ card, domId, supports = [] }) {
  const { title, provenance, sourceName, source, relatedSourceName, laureateId } = card;

  return (
    <li className={`assistant-evidence-card assistant-evidence-card--${provenance.key}`} id={domId} tabIndex={-1}>
      <p className="assistant-evidence-title">{title}</p>

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
          <p className="assistant-evidence-meta">Nobel Explorer teaching content; no stored external citation</p>
          {relatedSourceName && (
            <p className="assistant-related-context">Related context: {relatedSourceName}</p>
          )}
        </>
      )}

      {provenance.key === "unknown" && (
        <p className="assistant-evidence-warning">Provenance was not provided for this evidence.</p>
      )}

      {supports.length > 0 && (
        <div className="assistant-supports">
          <p className="assistant-supports-label">Supports</p>
          <ul>
            {supports.map((claim) => <li key={claim}>{claim}</li>)}
          </ul>
        </div>
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
