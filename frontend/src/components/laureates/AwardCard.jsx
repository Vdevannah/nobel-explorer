import { getCountryFlag } from "../../utils/countryFlags";

function institutionLocation(institution) {
  const countryFlag = institution.country && getCountryFlag(institution.country);
  return [
    institution.city,
    institution.state,
    institution.country && (countryFlag ? `${countryFlag} ${institution.country}` : institution.country),
  ].filter(Boolean).join(", ");
}

function AwardCard({ award, number }) {
  return (
    <article className="award-card">
      <header className="award-card-header">
        <div>
          <p>Award {number}</p>
          <h3>{award.prize.category.name}</h3>
        </div>
        <span className="award-year">{award.prize.year}</span>
      </header>

      {award.prize_share && (
        <p className="award-share">Prize share: {award.prize_share}</p>
      )}

      {award.motivation && (
        <blockquote className="award-motivation">
          <p>{award.motivation}</p>
        </blockquote>
      )}

      {award.affiliations.length > 0 && (
        <section className="award-affiliations" aria-label={`Affiliations for ${award.prize.year} ${award.prize.category.name}`}>
          <h4>Affiliation at time of award</h4>
          <ul>
            {award.affiliations.map((institution) => {
              const location = institutionLocation(institution);
              return (
                <li key={institution.institution_id}>
                  <strong>{institution.name}</strong>
                  {location && <span>{location}</span>}
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </article>
  );
}

export default AwardCard;
