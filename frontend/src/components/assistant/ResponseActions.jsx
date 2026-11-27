import { useEffect, useRef, useState } from "react";

const FEEDBACK_MS = 2500;

// Copies the original answer text (citation markers included, no metadata).
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
      await navigator.clipboard.writeText(answer);
      showFeedback("copied");
    } catch {
      showFeedback("failed");
    }
  }

  return (
    <div className="assistant-actions">
      <button type="button" className="assistant-action-button" onClick={copyAnswer}>
        Copy answer
      </button>
      <span className={`assistant-copy-feedback assistant-copy-feedback--${feedback ?? "idle"}`} role="status">
        {feedback === "copied" && "Answer copied"}
        {feedback === "failed" && "Could not copy. Select the answer text to copy it manually."}
      </span>
    </div>
  );
}

export default ResponseActions;
