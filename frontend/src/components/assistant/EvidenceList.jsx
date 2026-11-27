import EvidenceCard from "./EvidenceCard";

// Disclosure section of evidence cards. Expanded by default; citation buttons
// re-expand it before focusing a card. Collapsed cards stay in the DOM (hidden)
// so aria-controls on citation buttons always points at an existing element.
function EvidenceList({ cards, domIdFor, sectionId, expanded, onToggle }) {
  if (cards.length === 0) return null;
  const listId = `${sectionId}-list`;

  return (
    <section className="assistant-evidence" aria-labelledby={`${sectionId}-heading`}>
      <h4 className="assistant-subheading assistant-disclosure-heading" id={`${sectionId}-heading`}>
        <button
          type="button"
          className="assistant-disclosure"
          aria-expanded={expanded}
          aria-controls={listId}
          onClick={onToggle}
        >
          <span className="assistant-disclosure-icon" aria-hidden="true">{expanded ? "▾" : "▸"}</span>
          Cited evidence ({cards.length})
        </button>
      </h4>
      <ol className="assistant-evidence-list" id={listId} hidden={!expanded}>
        {cards.map((card) => <EvidenceCard key={card.id} card={card} domId={domIdFor(card.ids?.[0] ?? card.id)} />)}
      </ol>
    </section>
  );
}

export default EvidenceList;
