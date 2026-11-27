import { useState } from "react";

import { normalizeToolCalls } from "../../utils/assistantEvidence";

// Observed tool activity only: which tools ran, with allow-listed arguments.
// It is not the model's reasoning. The list is unordered because the response
// does not say which calls ran in parallel.
function ToolActivity({ toolCalls, sectionId }) {
  const [expanded, setExpanded] = useState(false);
  const calls = normalizeToolCalls(toolCalls);
  if (calls.length === 0) return null;
  const panelId = `${sectionId}-panel`;

  return (
    <section className="assistant-tools" aria-labelledby={`${sectionId}-heading`}>
      <h4 className="assistant-subheading assistant-disclosure-heading" id={`${sectionId}-heading`}>
        <button
          type="button"
          className="assistant-disclosure"
          aria-expanded={expanded}
          aria-controls={panelId}
          onClick={() => setExpanded((value) => !value)}
        >
          <span className="assistant-disclosure-icon" aria-hidden="true">{expanded ? "▾" : "▸"}</span>
          How this answer was found
        </button>
      </h4>
      <div className="assistant-tools-panel" id={panelId} hidden={!expanded}>
        <p className="assistant-tools-intro">
          Nobel Explorer tools the assistant used for this question. This shows observed tool activity,
          not the model&apos;s reasoning, and the order does not indicate which ran first.
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
              <p className="assistant-tool-description">{call.description}</p>
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
      </div>
    </section>
  );
}

export default ToolActivity;
