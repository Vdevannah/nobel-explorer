// Occupies the hero's right-hand slot. Phase 8.6 will replace this with a
// curated Discovery visual/introduction — keep it swappable in isolation
// from LaureateHero's portrait/identity structure.
function LaureateContextPanel({ awards }) {
  if (!awards.length) {
    return null;
  }

  return (
    <div className="detail-nobel-context" aria-label="Nobel prize summary">
      <p className="detail-nobel-context-heading">{awards.length === 1 ? "Nobel Prize" : "Nobel Prizes"}</p>
      <ul className="detail-nobel-context-list">
        {awards.map((award) => (
          <li key={award.laureate_prize_id}>
            <p className="detail-nobel-context-award">
              {award.prize.category.name} — {award.prize.year}
            </p>
            {award.prize_share && <p className="detail-nobel-context-share">Share {award.prize_share}</p>}
            {award.affiliations.length > 0 && (
              <p className="detail-nobel-context-affiliation">
                {award.affiliations.map((affiliation) => affiliation.name).join("; ")}
              </p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default LaureateContextPanel;
