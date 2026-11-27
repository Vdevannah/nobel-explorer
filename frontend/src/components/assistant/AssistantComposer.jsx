import { useLayoutEffect } from "react";

// Show the visible character counter only near the limit; screen readers can
// always reach it through aria-describedby.
const COUNTER_VISIBLE_FROM = 900;
const MAX_TEXTAREA_HEIGHT_PX = 200;

// Question input. Enter submits; Shift+Enter inserts a newline; Enter is
// ignored during IME composition. The page owns all request state.
function AssistantComposer({
  value,
  onChange,
  onSubmit,
  onCancel,
  onClear,
  pending,
  canClear,
  maxChars,
  textareaRef,
}) {
  const length = value.trim().length;
  const tooLong = length > maxChars;
  const canSubmit = !pending && length > 0 && !tooLong;
  const showCounter = tooLong || length >= COUNTER_VISIBLE_FROM;

  // Grow with the text up to a maximum height, then scroll.
  useLayoutEffect(() => {
    const textarea = textareaRef?.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_TEXTAREA_HEIGHT_PX)}px`;
  }, [value, textareaRef]);

  function handleKeyDown(event) {
    if (event.key !== "Enter" || event.shiftKey) return;
    if (event.nativeEvent.isComposing || event.keyCode === 229) return;
    event.preventDefault();
    if (canSubmit) onSubmit();
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (canSubmit) onSubmit();
  }

  return (
    <form className="assistant-composer" onSubmit={handleSubmit} aria-label="Ask a question">
      <label className="visually-hidden" htmlFor="assistant-question">Your question</label>
      <div className={tooLong ? "assistant-input assistant-input--invalid" : "assistant-input"}>
        <textarea
          id="assistant-question"
          ref={textareaRef}
          className="assistant-textarea"
          rows={1}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          aria-describedby="assistant-question-hint assistant-question-count"
          aria-invalid={tooLong || undefined}
          placeholder="Ask a question…"
        />
        <div className="assistant-input-actions">
          {pending && (
            <button className="assistant-text-button" type="button" onClick={onCancel}>
              Cancel
            </button>
          )}
          <button className="assistant-send" type="submit" disabled={!canSubmit}>
            {pending ? "Asking…" : "Ask"}
          </button>
        </div>
      </div>

      <div className="assistant-composer-footer">
        <span
          id="assistant-question-count"
          className={[
            "assistant-count",
            tooLong ? "assistant-count--over" : "",
            showCounter ? "" : "visually-hidden",
          ].filter(Boolean).join(" ")}
        >
          {length.toLocaleString()} / {maxChars.toLocaleString()} characters
          {tooLong && " — please shorten your question"}
        </span>
        {canClear && (
          <button className="assistant-text-button" type="button" onClick={onClear}>
            Clear conversation
          </button>
        )}
      </div>
      <span id="assistant-question-hint" className="visually-hidden">
        Press Enter to ask, Shift+Enter for a new line.
      </span>
    </form>
  );
}

export default AssistantComposer;
