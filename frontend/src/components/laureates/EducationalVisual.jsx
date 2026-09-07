function resolveVisualAsset(visual, level) {
  if (visual.imageUrl) return visual.imageUrl;
  if (!visual.assetsByLevel) return null;
  if (level) return visual.assetsByLevel[level] ?? null;
  return null;
}

function EducationalVisual({ visual, compact = false, level = null }) {
  if (!visual) return null;

  const imageUrl = resolveVisualAsset(visual, level);
  const alt = visual.altByLevel?.[level] ?? visual.alt;

  return (
    <figure className={`educational-visual${compact ? " educational-visual--compact" : ""}`}>
      {compact && visual.thumbnail ? (
        <div className="educational-visual-thumbnail" role="img" aria-label={visual.thumbnail.alt}>
          <span>{visual.thumbnail.label}</span>
        </div>
      ) : imageUrl ? (
        <img src={imageUrl} alt={alt} loading={compact ? "lazy" : "eager"} />
      ) : !compact ? (
        <div className="educational-visual-placeholder" role="img" aria-label={alt}>
          <span>Visual asset coming soon</span>
        </div>
      ) : null}
      {!compact && visual.caption && <figcaption>{visual.caption}</figcaption>}
    </figure>
  );
}

export default EducationalVisual;
