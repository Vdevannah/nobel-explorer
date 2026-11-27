import { useCallback, useEffect, useMemo, useState } from "react";

import {
  EXTENDED_WAIT_MESSAGE,
  EXTENDED_WAIT_SECONDS,
  friendlyLimitations,
  groupEvidence,
  normalizeCitations,
} from "../../utils/assistantEvidence";
import AnswerText from "./AnswerText";
import EvidenceList from "./EvidenceList";
import GroundingBadge from "./GroundingBadge";
import ResponseActions from "./ResponseActions";
import ResponseStatusNotice from "./ResponseStatusNotice";
import ToolActivity from "./ToolActivity";

function prefersReducedMotion() {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

// One question and its outcome. Evidence ids resolve only against this
// exchange's own citations, and every DOM id is namespaced by the exchange id,
// so two answers that both cite E1 never share a target.
function AssistantExchange({ exchange, elapsedSeconds }) {
  const response = exchange.result?.kind === "response" ? exchange.result.response : null;
  const cards = useMemo(() => normalizeCitations(response?.citations), [response]);
  const citationsById = useMemo(() => Object.fromEntries(cards.map((card) => [card.id, card])), [cards]);
  // Identical records cited under several ids share one card; every id maps to it.
  const groups = useMemo(() => groupEvidence(cards), [cards]);
  const groupIdFor = useMemo(
    () => Object.fromEntries(groups.flatMap((group) => group.ids.map((id) => [id, group.ids[0]]))),
    [groups],
  );
  const limitations = useMemo(() => friendlyLimitations(response?.evidence_limitations), [response]);

  const [evidenceExpanded, setEvidenceExpanded] = useState(true);
  const [focusRequest, setFocusRequest] = useState(null); // { id } – new object per click

  const cardDomId = useCallback((id) => `${exchange.id}-evidence-${id}`, [exchange.id]);
  const evidenceDomId = useCallback((id) => cardDomId(groupIdFor[id] ?? id), [cardDomId, groupIdFor]);

  // Focus after React has rendered the expanded list (it may have been hidden).
  useEffect(() => {
    if (!focusRequest || !evidenceExpanded) return;
    const target = document.getElementById(evidenceDomId(focusRequest.id));
    if (!target) return;
    target.scrollIntoView({ block: "nearest", behavior: prefersReducedMotion() ? "auto" : "smooth" });
    target.focus({ preventScroll: true });
  }, [focusRequest, evidenceExpanded, evidenceDomId]);

  const focusEvidence = useCallback((id) => {
    setEvidenceExpanded(true);
    setFocusRequest({ id });
  }, []);

  const answer = typeof response?.answer === "string" && response.answer.trim() ? response.answer : null;

  return (
    <article className="assistant-exchange" aria-labelledby={`${exchange.id}-question`}>
      <div className="assistant-question">
        <p className="assistant-label" aria-hidden="true">You asked</p>
        <h3 className="assistant-question-text" id={`${exchange.id}-question`}>
          <span className="visually-hidden">You asked: </span>
          {exchange.question}
        </h3>
      </div>

      <div className="assistant-response">
        <p className="assistant-label">Assistant</p>

        {exchange.phase === "pending" ? (
          // Not a live region: the page announcer reports the start and the
          // extended-wait message once each; a live region here would read the
          // ticking timer every second.
          <div className="assistant-pending-block">
            <p className="assistant-pending">
              <span className="assistant-pending-dot" aria-hidden="true" />
              Searching Nobel Explorer records…
              <span className="assistant-elapsed" aria-hidden="true"> {elapsedSeconds}s</span>
            </p>
            {elapsedSeconds >= EXTENDED_WAIT_SECONDS && (
              <p className="assistant-extended-wait">{EXTENDED_WAIT_MESSAGE}</p>
            )}
          </div>
        ) : (
          <>
            <ResponseStatusNotice exchange={exchange} />

            {answer && (
              <>
                <AnswerText
                  text={answer}
                  citationsById={citationsById}
                  evidenceDomId={evidenceDomId}
                  onCitationSelect={focusEvidence}
                />
                <ResponseActions answer={answer} />
                <GroundingBadge grounding={response.grounding} />
              </>
            )}

            {limitations.length > 0 && (
              <section className="assistant-limitations" aria-labelledby={`${exchange.id}-limitations`}>
                <h4 className="assistant-subheading" id={`${exchange.id}-limitations`}>Limitations</h4>
                <ul>
                  {limitations.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </section>
            )}

            <EvidenceList
              cards={groups}
              domIdFor={cardDomId}
              sectionId={`${exchange.id}-evidence`}
              expanded={evidenceExpanded}
              onToggle={() => setEvidenceExpanded((value) => !value)}
            />

            {response && <ToolActivity toolCalls={response.tool_calls} sectionId={`${exchange.id}-tools`} />}
          </>
        )}
      </div>
    </article>
  );
}

export default AssistantExchange;
