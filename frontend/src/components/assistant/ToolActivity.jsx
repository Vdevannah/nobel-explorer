// Observed tool activity only: which tools ran, with allow-listed arguments.
// It is not the model's reasoning. The list is unordered because the response
// does not say which calls ran in parallel. Collapsed by default; the toggle
// lives in the answer's action row.
function ToolActivity({ calls, panelId, expanded }) {
  if (calls.length === 0) return null;

  return (
    <section className="assistant-tools-panel" id={panelId} aria-label="How this answer was found" hidden={!expanded}>
      <p className="assistant-tools-intro">
        Nobel Explorer tools used for this question. This shows observed tool activity, not the model&apos;s
        reasoning.
      </p>
      <ul className="assistant-tool-list">
        {calls.map((call) => (
          <li key={call.key} className="assistant-tool">
            <div className="assistant-tool-header">
              <span className="assistant-tool-name">{call.label}</span>
              <span className={`assistant-tool-status assistant-tool-status--${call.ok ? "ok" : "failed"}`}>
                {call.statusText}
              </span>
            </div>
            {call.arguments.length > 0 && (
              <dl className="assistant-tool-args">
                {call.arguments.map((argument) => (
                  <div key={argument.key}>
                    <dt>{argument.label}</dt>
                    <dd>{argument.value}</dd>
                  </div>
                ))}
              </dl>
            )}
            {call.evidenceCount !== null && (
              <p className="assistant-tool-evidence">
                {call.evidenceCount === 1 ? "1 evidence reference returned" : `${call.evidenceCount} evidence references returned`}
              </p>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

export default ToolActivity;
