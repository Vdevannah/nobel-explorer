import { ACCURACY_DISCLAIMER, CITATION_DISCLAIMER } from "../../utils/assistantEvidence";
import EvidenceCard from "./EvidenceCard";

// Sources panel for one answer. Collapsed by default (the toggle lives in the
// answer's action row); citation buttons expand it before focusing a card.
// Collapsed cards stay in the DOM (hidden) so aria-controls on citation
// buttons always points at an existing element.
function EvidenceList({ cards, claims = {}, domIdFor, listId, expanded, notices = [] }) {
  if (cards.length === 0) return null;

  return (
    <section className="assistant-sources" id={listId} aria-label="Sources" hidden={!expanded}>
      <p className="assistant-disclaimer">{ACCURACY_DISCLAIMER} {CITATION_DISCLAIMER}</p>
      {notices.map((notice) => <p key={notice} className="assistant-disclaimer">{notice}</p>)}
      <ol className="assistant-evidence-list">
        {cards.map((card) => {
          // Statements supported by any of this card's (grouped) evidence ids.
          const supports = [...new Set((card.ids ?? [card.id]).flatMap((id) => claims[id] ?? []))];
          return <EvidenceCard key={card.id} card={card} supports={supports} domId={domIdFor(card.ids?.[0] ?? card.id)} />;
        })}
      </ol>
    </section>
  );
}

export default EvidenceList;
