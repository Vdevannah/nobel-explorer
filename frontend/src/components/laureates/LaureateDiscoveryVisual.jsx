// Occupies the hero's right-hand slot in place of LaureateContextPanel when
// curated Discovery content exists for a laureate. Kept separable so
// Phase 8.6 can extend it with a short discovery introduction alongside
// the image.
function LaureateDiscoveryVisual({ imageUrl, alt }) {
  return (
    <div className="detail-discovery-visual" aria-label="Discovery visual">
      <img src={imageUrl} alt={alt} />
    </div>
  );
}

export default LaureateDiscoveryVisual;
