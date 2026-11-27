import {
  describeGrounding,
  GENERAL_KNOWLEDGE_NOTE,
  MIXED_KNOWLEDGE_NOTE,
  RESTATES_NO_MATCH,
} from "../../utils/assistantEvidence";

// Backend limitations that only restate the grounding warning shown above them
// (friendly wording from friendlyLimitation). Hidden when that warning is shown.
const RESTATES_WARNING = {
  no_evidence: "No supporting evidence was retrieved, so this answer is not based on Nobel Explorer data.",
  uncited: "The answer does not reference any of the evidence that was retrieved.",
};

// Quiet notes under an answer, shown only when they matter: a grounding
// warning (some references invalid, none provided, no evidence retrieved) and
// the backend's limitations in plain language. A fully cited answer with no
// limitations shows nothing here. Labels describe citations, never "verified".
function AnswerNotes({ id, grounding, limitations, knowledge = null }) {
  const general = knowledge === "general";
  const info = describeGrounding(grounding);
  // For a general-knowledge answer the subtle note replaces the "no evidence" warning.
  const warning = !general && info && info.tone !== "info" ? info : null;
  const redundant = warning && Object.hasOwn(RESTATES_WARNING, grounding) ? RESTATES_WARNING[grounding] : null;
  const items = limitations.filter((item) => item !== redundant && !(general && RESTATES_NO_MATCH.has(item)));
  const note = general ? GENERAL_KNOWLEDGE_NOTE : knowledge === "mixed" ? MIXED_KNOWLEDGE_NOTE : null;
  if (!note && !warning && items.length === 0) return null;

  return (
    <section className="assistant-notes" aria-labelledby={`${id}-limitations`}>
      <h4 className="visually-hidden" id={`${id}-limitations`}>Limitations</h4>
      {note && (
        <p className="assistant-knowledge-note">
          <span aria-hidden="true">ⓘ </span>
          {note}
        </p>
      )}
      {(warning || items.length > 0) && (
        <ul>
          {warning && (
            <li className={`assistant-note assistant-note--${warning.tone}`}>
              <span className="assistant-note-label">{warning.label}.</span> {warning.detail}
            </li>
          )}
          {items.map((item) => (
            <li key={item} className="assistant-note">{item}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default AnswerNotes;
