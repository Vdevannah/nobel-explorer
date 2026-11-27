import { useMemo, useState } from "react";

import {
  EDUCATIONAL_PROVENANCE_NOTICE,
  EXTENDED_WAIT_MESSAGE,
  EXTENDED_WAIT_SECONDS,
  friendlyLimitations,
  groupEvidence,
  knowledgeKind,
  normalizeCitations,
  normalizeToolCalls,
} from "../../utils/assistantEvidence";
import { claimsByEvidence } from "../../utils/assistantText";
import AnswerNotes from "./AnswerNotes";
import AnswerText from "./AnswerText";
import EvidenceList from "./EvidenceList";
import ResponseActions from "./ResponseActions";
import ResponseStatusNotice from "./ResponseStatusNotice";
import ToolActivity from "./ToolActivity";

// Decorative disclosure chevron; rotation follows aria-expanded in CSS.
function Chevron() {
  return (
    <svg className="assistant-chip-icon" viewBox="0 0 12 12" width="12" height="12" aria-hidden="true" focusable="false">
      <path d="M3 4.5 6 7.5 9 4.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// One question and its outcome, presented for learners: the answer text has no
// evidence ids; a collapsed "Sources" panel lists each source with the statements
// it supports. All citations, grouping and provenance come from the response
// unchanged. Tool activity is kept for debugging only (`debug`), not shown publicly.
// Every DOM id is namespaced by the exchange id.
function AssistantExchange({ exchange, elapsedSeconds, debug = false }) {
  const response = exchange.result?.kind === "response" ? exchange.result.response : null;
  const cards = useMemo(() => normalizeCitations(response?.citations), [response]);
  // Identical records cited under several ids share one card.
  const groups = useMemo(() => groupEvidence(cards), [cards]);
  const limitations = useMemo(() => friendlyLimitations(response?.evidence_limitations), [response]);
  const toolCalls = useMemo(() => (debug ? normalizeToolCalls(response?.tool_calls) : []), [debug, response]);

  const [sourcesExpanded, setSourcesExpanded] = useState(false);
  const [toolsExpanded, setToolsExpanded] = useState(false);

  const answer = typeof response?.answer === "string" && response.answer.trim() ? response.answer : null;
  // Statements each source supports (claim-to-source association without inline ids).
  const claims = useMemo(() => claimsByEvidence(answer ?? ""), [answer]);
  const cardDomId = (id) => `${exchange.id}-evidence-${id}`;

  const listId = `${exchange.id}-evidence-list`;
  const toolsPanelId = `${exchange.id}-tools-panel`;
  // The educational-provenance notice belongs with the sources; it stays under the
  // answer only if there is no Sources panel to hold it.
  const sourceNotices = groups.length > 0 ? limitations.filter((item) => item === EDUCATIONAL_PROVENANCE_NOTICE) : [];
  const answerNotes = limitations.filter((item) => !sourceNotices.includes(item));
  const hasActions = Boolean(answer) || groups.length > 0 || toolCalls.length > 0;

  return (
    <article className="assistant-exchange" aria-labelledby={`${exchange.id}-question`}>
      <h3 className="assistant-question" id={`${exchange.id}-question`}>
        <span className="visually-hidden">You asked: </span>
        {exchange.question}
      </h3>

      <div className="assistant-response">
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

            {answer && <AnswerText text={answer} />}

            {response && (
              <AnswerNotes
                id={exchange.id}
                grounding={answer ? response.grounding : null}
                limitations={answerNotes}
                knowledge={answer ? knowledgeKind(answer, response.grounding) : null}
              />
            )}

            {hasActions && (
              <div className="assistant-answer-actions">
                {answer && <ResponseActions answer={answer} />}
                {groups.length > 0 && (
                  <button
                    type="button"
                    className="assistant-chip"
                    aria-expanded={sourcesExpanded}
                    aria-controls={listId}
                    onClick={() => setSourcesExpanded((value) => !value)}
                  >
                    Sources ({groups.length})
                    <Chevron />
                  </button>
                )}
                {toolCalls.length > 0 && (
                  <button
                    type="button"
                    className="assistant-chip"
                    aria-expanded={toolsExpanded}
                    aria-controls={toolsPanelId}
                    onClick={() => setToolsExpanded((value) => !value)}
                  >
                    How this answer was found
                    <Chevron />
                  </button>
                )}
              </div>
            )}

            <EvidenceList
              cards={groups}
              claims={claims}
              domIdFor={cardDomId}
              listId={listId}
              expanded={sourcesExpanded}
              notices={sourceNotices}
            />
            {debug && <ToolActivity calls={toolCalls} panelId={toolsPanelId} expanded={toolsExpanded} />}
          </>
        )}
      </div>
    </article>
  );
}

export default AssistantExchange;
