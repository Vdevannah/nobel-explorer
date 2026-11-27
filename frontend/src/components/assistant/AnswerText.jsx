import { splitEmphasis, tokenizeAnswer } from "../../utils/assistantText";

const MARKER_LABELS = {
  unverified: {
    text: "[unverified]",
    description: "A citation here was removed because it did not match retrieved evidence.",
  },
  link_removed: {
    text: "[link removed]",
    description: "A link here was removed because no tool returned it.",
  },
};

// Renders model output as plain React text (never HTML). Well-formed **bold**
// becomes <strong>; citation ids are buttons only when they match a citation
// returned for THIS exchange.
function AnswerText({ text, citationsById, evidenceDomId, onCitationSelect }) {
  function renderTokens(tokens, keyPrefix) {
    return tokens.map((token, index) => {
      const key = `${keyPrefix}-${index}`;
      if (token.type === "text") {
        return <span key={key}>{token.value}</span>;
      }

      if (token.type === "marker") {
        const marker = MARKER_LABELS[token.marker];
        return (
          <span
            key={key}
            className={`assistant-marker assistant-marker--${token.marker}`}
            title={marker.description}
          >
            {marker.text}
            <span className="visually-hidden"> {marker.description}</span>
          </span>
        );
      }

      return (
        <span key={key} className="assistant-citation-group">
          {token.ids.map((id) => {
            const citation = citationsById[id];
            if (!citation) {
              return (
                <span key={id} className="assistant-citation-unmatched">
                  [{id}]
                </span>
              );
            }
            return (
              <button
                key={id}
                type="button"
                className="assistant-citation"
                aria-label={`Evidence ${id}: ${citation.title}`}
                aria-controls={evidenceDomId(id)}
                onClick={() => onCitationSelect(id)}
              >
                {id}
              </button>
            );
          })}
        </span>
      );
    });
  }

  return (
    <div className="assistant-answer-text">
      {splitEmphasis(text).map((segment, index) =>
        segment.strong ? (
          <strong key={`s${index}`}>{renderTokens(tokenizeAnswer(segment.text), `s${index}`)}</strong>
        ) : (
          renderTokens(tokenizeAnswer(segment.text), `p${index}`)
        ),
      )}
    </div>
  );
}

export default AnswerText;
