import { Link } from "react-router-dom";

function Portrait({ imageUrl, name }) {
  if (imageUrl) {
    return <img className="featured-story-image" src={imageUrl} alt={name} />;
  }

  return (
    <div className="portrait-placeholder" role="img" aria-label={`Portrait placeholder for ${name}`}>
      <span aria-hidden="true">AE</span>
      <small>Portrait coming soon</small>
    </div>
  );
}

function FeaturedLaureate({ name, category, year, description, imageUrl = null, laureateId = null }) {
  return (
    <section className="home-section featured-section" aria-labelledby="featured-title">
      <div className="container">
        <div className="featured-card">
          <Portrait imageUrl={imageUrl} name={name} />
          <div className="featured-copy">
            <p className="eyebrow">Featured Story</p>
            <h2 id="featured-title">{name}</h2>
            <p className="featured-award">{category} <span>•</span> {year}</p>
            <p>{description}</p>
            {laureateId ? (
              <Link className="text-link" to={`/laureates/${laureateId}`}>
                Explore Laureate <span aria-hidden="true">→</span>
              </Link>
            ) : (
              <button className="text-link" type="button" aria-disabled="true">
                Explore Laureate <span aria-hidden="true">→</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

export default FeaturedLaureate;
