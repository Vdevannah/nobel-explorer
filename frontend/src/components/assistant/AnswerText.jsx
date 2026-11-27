import { splitEmphasis, stripCitations, tokenizeAnswer } from "../../utils/assistantText";

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

// Renders model output as plain React text (never HTML) for learners: evidence
// ids such as [E1] are hidden (the Sources panel shows which statements each
// source supports), well-formed **bold** becomes <strong>, and validation
// markers ([unverified], [link removed]) stay visible as genuine warnings.
function AnswerText({ text }) {
  function renderTokens(tokens, keyPrefix) {
    return tokens.map((token, index) => {
      const key = `${keyPrefix}-${index}`;
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
      // Citations were stripped; anything else is plain text.
      return <span key={key}>{token.type === "text" ? token.value : ""}</span>;
    });
  }

  return (
    <div className="assistant-answer-text">
      {splitEmphasis(stripCitations(text)).map((segment, index) =>
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
