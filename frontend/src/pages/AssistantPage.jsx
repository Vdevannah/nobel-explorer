import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import AssistantComposer from "../components/assistant/AssistantComposer";
import AssistantExchange from "../components/assistant/AssistantExchange";
import SuggestedQuestions from "../components/assistant/SuggestedQuestions";
import WelcomeIllustration from "../components/assistant/WelcomeIllustration";
import { ASSISTANT_MAX_QUESTION_CHARS, askResearchAssistant } from "../services/api";
import { EXTENDED_WAIT_MESSAGE, EXTENDED_WAIT_SECONDS } from "../utils/assistantEvidence";

const SUGGESTED_QUESTIONS = [
  "Who won the 2023 Medicine prize and what did they discover?",
  "Explain click chemistry in simple terms.",
  "Which three birth countries have the most Nobel laureates?",
  "Why did Albert Einstein receive the Nobel Prize?",
];

// A request "failed" when there is nothing useful to keep: the visitor's
// question is put back into an empty input so they can edit or retry.
function isFailure(result) {
  if (result.kind !== "response") return true;
  return result.response.status === "unavailable" || result.response.status === "error";
}

function announcementFor(result) {
  if (result.kind !== "response") return "The question could not be answered.";
  const { status } = result.response;
  if (status === "completed") return "Answer received.";
  if (status === "budget_exhausted" || status === "timeout") return "The assistant stopped before finishing.";
  return "The question could not be answered.";
}

function AssistantPage() {
  // Tool activity is for debugging and evaluation only: /assistant?debug shows it.
  const [searchParams] = useSearchParams();
  const debug = searchParams.has("debug");
  const [question, setQuestion] = useState("");
  const [exchanges, setExchanges] = useState([]);
  const [pendingId, setPendingId] = useState(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [announcement, setAnnouncement] = useState("");

  // Synchronous guards: React state updates are async, refs are not.
  const submittingRef = useRef(false);
  const activeRequestRef = useRef(null); // { exchangeId, controller, question }
  const nextIdRef = useRef(0);
  const mountedRef = useRef(false);
  const textareaRef = useRef(null);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      // Leaving the page stops waiting; the server may still finish the request.
      mountedRef.current = false;
      activeRequestRef.current?.controller.abort();
      activeRequestRef.current = null;
      submittingRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (!pendingId) return undefined;
    // elapsedSeconds is reset together with pendingId (see submitQuestion), so the
    // first render of a new request never shows the previous request's time.
    const timer = window.setInterval(() => setElapsedSeconds((seconds) => seconds + 1), 1000);
    return () => window.clearInterval(timer);
  }, [pendingId]);

  // Announce the extended-wait message exactly once per request (the visible
  // timer itself is hidden from assistive technology).
  useEffect(() => {
    if (pendingId && elapsedSeconds === EXTENDED_WAIT_SECONDS) setAnnouncement(EXTENDED_WAIT_MESSAGE);
  }, [pendingId, elapsedSeconds]);

  const restoreQuestion = useCallback((text) => {
    setQuestion((current) => (current.trim() ? current : text));
  }, []);

  const submitQuestion = useCallback(async () => {
    if (submittingRef.current) return;
    const trimmed = question.trim();
    if (!trimmed || trimmed.length > ASSISTANT_MAX_QUESTION_CHARS) return;

    submittingRef.current = true;
    nextIdRef.current += 1;
    const exchangeId = `assistant-exchange-${nextIdRef.current}`;
    const controller = new AbortController();
    activeRequestRef.current = { exchangeId, controller, question: trimmed };

    setExchanges((previous) => [...previous, { id: exchangeId, question: trimmed, phase: "pending", result: null }]);
    setQuestion("");
    // Reset in the same render as the new pending id. Resetting later (in an
    // effect) let one render inherit a previous long request's time, which
    // briefly showed and announced the extended-wait message (Phase 4D.2 bug).
    setElapsedSeconds(0);
    setPendingId(exchangeId);
    setAnnouncement("Searching Nobel Explorer records…");

    const result = await askResearchAssistant(trimmed, { signal: controller.signal });

    // Ignore anything that is no longer the active request: cancelled,
    // cleared, superseded or arriving after the page was left.
    if (!mountedRef.current || activeRequestRef.current?.exchangeId !== exchangeId) return;

    activeRequestRef.current = null;
    submittingRef.current = false;
    setPendingId(null);
    setElapsedSeconds(0);
    setExchanges((previous) =>
      previous.map((exchange) => (exchange.id === exchangeId ? { ...exchange, phase: "done", result } : exchange)),
    );
    setAnnouncement(announcementFor(result));
    if (isFailure(result)) restoreQuestion(trimmed);
  }, [question, restoreQuestion]);

  const cancelRequest = useCallback(() => {
    const active = activeRequestRef.current;
    if (!active) return;
    activeRequestRef.current = null;
    submittingRef.current = false;
    active.controller.abort();
    setPendingId(null);
    setElapsedSeconds(0);
    setExchanges((previous) =>
      previous.map((exchange) => (exchange.id === active.exchangeId ? { ...exchange, phase: "cancelled" } : exchange)),
    );
    setAnnouncement("Stopped waiting; the server may still finish this request.");
    restoreQuestion(active.question);
  }, [restoreQuestion]);

  const clearConversation = useCallback(() => {
    activeRequestRef.current?.controller.abort();
    activeRequestRef.current = null;
    submittingRef.current = false;
    setPendingId(null);
    setElapsedSeconds(0);
    setExchanges([]);
    setQuestion("");
    setAnnouncement("Conversation cleared.");
    textareaRef.current?.focus();
  }, []);

  const selectSuggestion = useCallback((text) => {
    setQuestion(text);
    textareaRef.current?.focus();
  }, []);

  const pending = pendingId !== null;

  const hasConversation = exchanges.length > 0;

  return (
    <section
      className={`assistant-page container${hasConversation ? " assistant-page--active" : ""}`}
      aria-labelledby="assistant-heading"
    >
      <div className="assistant-shell">
        <header className="assistant-header">
          {/* Always shown; assistant.css scales it to 65% during a conversation. */}
          <WelcomeIllustration />
          <h1 id="assistant-heading">Nobel Intelligence</h1>
          <p className="assistant-subtitle">Discover the people, ideas and science that changed our world.</p>
        </header>

        {hasConversation ? (
          // A labelled region, not role="log": one polite announcer below reports
          // progress, so the timer and new answers are not read twice.
          <section className="assistant-conversation" aria-labelledby="assistant-conversation-heading">
            <h2 className="visually-hidden" id="assistant-conversation-heading">Questions and answers in this session</h2>
            {exchanges.map((exchange) => (
              <AssistantExchange
                key={exchange.id}
                exchange={exchange}
                elapsedSeconds={exchange.id === pendingId ? elapsedSeconds : 0}
                debug={debug}
              />
            ))}
          </section>
        ) : (
          <SuggestedQuestions questions={SUGGESTED_QUESTIONS} onSelect={selectSuggestion} />
        )}

        <AssistantComposer
          value={question}
          onChange={setQuestion}
          onSubmit={submitQuestion}
          onCancel={cancelRequest}
          onClear={clearConversation}
          pending={pending}
          canClear={pending || hasConversation}
          maxChars={ASSISTANT_MAX_QUESTION_CHARS}
          textareaRef={textareaRef}
        />
      </div>

      <p className="visually-hidden" aria-live="polite" aria-atomic="true">{announcement}</p>
    </section>
  );
}

export default AssistantPage;
