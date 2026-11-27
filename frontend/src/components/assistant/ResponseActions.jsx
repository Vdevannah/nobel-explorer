import { useEffect, useRef, useState } from "react";

import { plainAnswerText } from "../../utils/assistantText";

const FEEDBACK_MS = 2500;

// Copies the answer as shown to learners (no evidence ids or ** markers, no metadata).
// Success is reported only after the Clipboard API resolves.
function ResponseActions({ answer }) {
  const [feedback, setFeedback] = useState(null); // null | "copied" | "failed"
  const timerRef = useRef(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      window.clearTimeout(timerRef.current);
    };
  }, []);

  function showFeedback(value) {
    if (!mountedRef.current) return;
    setFeedback(value);
    window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => {
      if (mountedRef.current) setFeedback(null);
    }, FEEDBACK_MS);
  }

  async function copyAnswer() {
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(plainAnswerText(answer));
      showFeedback("copied");
    } catch {
      showFeedback("failed");
    }
  }

  return (
    <>
      <button
        type="button"
        className="assistant-icon-button"
        onClick={copyAnswer}
        aria-label="Copy answer"
        title="Copy answer"
      >
        <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">
          <rect x="5.25" y="5.25" width="8" height="8.5" rx="1.75" fill="none" stroke="currentColor" strokeWidth="1.4" />
          <path d="M10.5 3.5V3.25A1.75 1.75 0 0 0 8.75 1.5h-4.5A1.75 1.75 0 0 0 2.5 3.25v5.5A1.75 1.75 0 0 0 4.25 10.5h.5"
            fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
        </svg>
      </button>
      <span className={`assistant-copy-feedback assistant-copy-feedback--${feedback ?? "idle"}`} role="status">
        {feedback === "copied" && "Copied"}
        {feedback === "failed" && "Could not copy. Select the answer text to copy it manually."}
      </span>
    </>
  );
}

export default ResponseActions;
