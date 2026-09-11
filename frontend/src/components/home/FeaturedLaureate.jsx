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

function FeaturedLaureate({
  name,
  category,
  year,
  contributionTitle = null,
  description,
  imageUrl = null,
  laureateId = null,
  ctaLabel = "Explore Laureate",
}) {
  return (
    <section className="home-section featured-section" aria-labelledby="featured-title">
      <div className="container">
        <div className="featured-card">
          <p className="eyebrow featured-eyebrow">Featured Story</p>
          <div className="featured-card-row">
            <Portrait imageUrl={imageUrl} name={name} />
            <div className="featured-copy">
              <h2 id="featured-title">{name}</h2>
              <p className="featured-award">{category} <span>•</span> {year}</p>
              {contributionTitle && <p className="featured-contribution">{contributionTitle}</p>}
              <p>{description}</p>
              {laureateId ? (
                <Link className="button button-primary featured-cta" to={`/laureates/${laureateId}`}>
                  {ctaLabel} <span aria-hidden="true">→</span>
                </Link>
              ) : (
                <button className="button button-primary featured-cta" type="button" aria-disabled="true">
                  {ctaLabel} <span aria-hidden="true">→</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default FeaturedLaureate;
