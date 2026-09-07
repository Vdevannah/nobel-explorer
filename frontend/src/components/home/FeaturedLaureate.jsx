function Portrait({ imageUrl, name }) {
  if (imageUrl) {
    return <img className="featured-portrait" src={imageUrl} alt={name} />;
  }

  return (
    <div className="portrait-placeholder" role="img" aria-label={`Portrait placeholder for ${name}`}>
      <span aria-hidden="true">AE</span>
      <small>Portrait coming soon</small>
    </div>
  );
}

function FeaturedLaureate({ name, category, year, description, imageUrl = null }) {
  return (
    <section className="home-section featured-section" aria-labelledby="featured-title">
      <div className="container">
        <div className="featured-card">
          <Portrait imageUrl={imageUrl} name={name} />
          <div className="featured-copy">
            <p className="eyebrow">Featured Laureate</p>
            <h2 id="featured-title">{name}</h2>
            <p className="featured-award">{category} <span>•</span> {year}</p>
            <p>{description}</p>
            <button className="text-link" type="button" aria-disabled="true">
              Explore Laureate <span aria-hidden="true">→</span>
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

export default FeaturedLaureate;
