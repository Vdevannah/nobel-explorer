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
      <label className="assistant-composer-label" htmlFor="assistant-question">Your question</label>
      <textarea
        id="assistant-question"
        ref={textareaRef}
        className="assistant-textarea"
        rows={3}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        aria-describedby="assistant-question-hint assistant-question-count"
        aria-invalid={tooLong || undefined}
        placeholder="For example: Who won the 2022 Chemistry prize?"
      />
      <div className="assistant-composer-meta">
        <span id="assistant-question-hint">Press Enter to ask, Shift+Enter for a new line.</span>
        <span
          id="assistant-question-count"
          className={tooLong ? "assistant-count assistant-count--over" : "assistant-count"}
        >
          {length.toLocaleString()} / {maxChars.toLocaleString()} characters
          {tooLong && " — please shorten your question"}
        </span>
      </div>
      <div className="assistant-composer-actions">
        <button className="button button-primary" type="submit" disabled={!canSubmit}>
          {pending ? "Asking…" : "Ask"}
        </button>
        {pending && (
          <button className="button button-secondary" type="button" onClick={onCancel}>
            Cancel
          </button>
        )}
        <button className="button button-secondary" type="button" onClick={onClear} disabled={!canClear}>
          Clear conversation
        </button>
      </div>
    </form>
  );
}

export default AssistantComposer;
