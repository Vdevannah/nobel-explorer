import { CITATION_DISCLAIMER, describeGrounding } from "../../utils/assistantEvidence";

// Describes how the answer relates to retrieved evidence, using the backend's
// grounding value as-is. Null or unknown values get no classification, only
// the standing disclaimer. No confidence scores are shown.
function GroundingBadge({ grounding }) {
  const info = describeGrounding(grounding);

  return (
    <div className="assistant-grounding">
      {info && (
        <p className={`assistant-grounding-badge assistant-grounding-badge--${info.tone}`}>
          <span className="assistant-grounding-label">{info.label}</span>
          <span className="assistant-grounding-detail">{info.detail}</span>
        </p>
      )}
      <p className="assistant-disclaimer">{CITATION_DISCLAIMER}</p>
    </div>
  );
}

export default GroundingBadge;
