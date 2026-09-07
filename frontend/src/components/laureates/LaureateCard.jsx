import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { isScientificVisual } from "../../data/scientificVisualLaureates";
import { getCountryFlag } from "../../utils/countryFlags";

function getInitials(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function LaureatePortrait({ imageUrl, mediaType, name }) {
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => {
    setImageFailed(false);
  }, [imageUrl]);

  if (imageUrl && !imageFailed) {
    const altText =
      mediaType === "organization"
        ? `${name} logo`
        : mediaType === "scientific"
          ? `Scientific visual related to ${name}'s Nobel-recognized work`
          : `Portrait of ${name}`;

    return (
      <img
        className={`laureate-card-portrait laureate-card-media--${mediaType}`}
        src={imageUrl}
        alt={altText}
        loading="lazy"
        onError={() => setImageFailed(true)}
      />
    );
  }

  return (
    <div
      className="laureate-card-placeholder"
      role="img"
      aria-label={`Portrait placeholder for ${name}`}
    >
      <span aria-hidden="true">{getInitials(name)}</span>
    </div>
  );
}

function LaureateCard({ laureate }) {
  const mediaType =
    laureate.laureate_type === "Organization"
      ? "organization"
      : isScientificVisual(laureate)
        ? "scientific"
        : "portrait";
  const genderLabel = laureate.gender
    ? laureate.gender.charAt(0).toUpperCase() + laureate.gender.slice(1)
    : null;
  const flag = laureate.birth_country && getCountryFlag(laureate.birth_country);
  const typeLine = [laureate.laureate_type, genderLabel].filter(Boolean).join(" · ");

  return (
    <article className="laureate-card">
      <div className="laureate-card-top">
        <LaureatePortrait imageUrl={laureate.image_url} mediaType={mediaType} name={laureate.full_name} />
        <div className="laureate-card-info">
          <h2>{laureate.full_name}</h2>
          {laureate.birth_country && (
            <p className="laureate-card-country">
              {flag && <span aria-hidden="true">{flag} </span>}
              {laureate.birth_country}
            </p>
          )}
          {typeLine && <p className="laureate-card-type">{typeLine}</p>}
        </div>
      </div>
      <Link className="laureate-cta" to={`/laureates/${laureate.laureate_id}`}>
        Explore Laureate <span aria-hidden="true">→</span>
      </Link>
    </article>
  );
}

export default LaureateCard;
