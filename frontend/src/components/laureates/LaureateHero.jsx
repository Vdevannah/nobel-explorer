import { useEffect, useState } from "react";

import { getCountryFlag } from "../../utils/countryFlags";
import { isScientificVisual } from "../../data/scientificVisualLaureates";

function initialsFor(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function DetailPortrait({ imageUrl, name, mediaType }) {
  const [imageFailed, setImageFailed] = useState(false);

  useEffect(() => setImageFailed(false), [imageUrl]);

  if (imageUrl && !imageFailed) {
    if (mediaType === "portrait") {
      return (
        <img
          className="detail-portrait"
          src={imageUrl}
          alt={`Portrait of ${name}`}
          onError={() => setImageFailed(true)}
        />
      );
    }

    const altText =
      mediaType === "scientific"
        ? `Scientific visual related to ${name}'s Nobel-recognized work`
        : `${name} logo`;

    return (
      <div className={`detail-media detail-media--${mediaType}`}>
        <img
          className="detail-media-image"
          src={imageUrl}
          alt={altText}
          onError={() => setImageFailed(true)}
        />
      </div>
    );
  }

  return (
    <div className="detail-portrait-placeholder" role="img" aria-label={`Portrait placeholder for ${name}`}>
      <span aria-hidden="true">{initialsFor(name)}</span>
      <small>Portrait coming soon</small>
    </div>
  );
}

function LaureateHero({ laureate }) {
  const mediaType =
    laureate.laureate_type === "Organization"
      ? "organization"
      : isScientificVisual(laureate)
        ? "scientific"
        : "portrait";

  const countryFlag = laureate.birth_country ? getCountryFlag(laureate.birth_country) : "";

  return (
    <section className="detail-hero" aria-labelledby="laureate-name">
      <DetailPortrait imageUrl={laureate.image_url} name={laureate.full_name} mediaType={mediaType} />
      <div className="detail-identity">
        <p className="eyebrow">Nobel Laureate</p>
        <h1 id="laureate-name">{laureate.full_name}</h1>
        <div className="detail-hero-awards" aria-label="Nobel awards">
          {laureate.awards.map((award) => (
            <div className="detail-hero-award" key={award.laureate_prize_id}>
              <span className="detail-award-tag">
                {award.prize.category.name} — {award.prize.year}
              </span>
              {award.motivation && <p className="detail-hero-motivation">“{award.motivation}”</p>}
              <div className="detail-hero-metadata">
                {award.prize_share && <p className="detail-hero-share">Share {award.prize_share}</p>}
                {award.affiliations.length > 0 && (
                  <p className="detail-hero-affiliation">
                    {award.affiliations.map((affiliation) => affiliation.name).join("; ")}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
        {laureate.birth_country && (
          <div className="detail-country-pill">
            {countryFlag && <span className="detail-country-flag" aria-hidden="true">{countryFlag}</span>}
            <span>{laureate.birth_country}</span>
          </div>
        )}
      </div>
    </section>
  );
}

export default LaureateHero;
