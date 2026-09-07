import { getCountryFlag } from "../../utils/countryFlags";

function formatBirthDate(value) {
  if (!value) {
    return null;
  }

  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function LaureateQuickFacts({ laureate }) {
  const countryFlag = laureate.birth_country && getCountryFlag(laureate.birth_country);
  const birthplace = [
    laureate.birth_city,
    laureate.birth_state,
    laureate.birth_country && (countryFlag ? `${countryFlag} ${laureate.birth_country}` : laureate.birth_country),
  ].filter(Boolean).join(", ");
  const facts = [
    ["Nobel API ID", laureate.nobel_laureate_id],
    ["Laureate type", laureate.laureate_type],
    ["Birth date", formatBirthDate(laureate.birth_date)],
    ["Birthplace", birthplace || null],
    ["Gender", laureate.gender],
    ["Nobel awards", String(laureate.awards.length)],
  ].filter(([, value]) => value);

  return (
    <aside className="quick-facts" aria-labelledby="quick-facts-title">
      <h2 id="quick-facts-title">Quick Facts</h2>
      <dl>
        {facts.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </aside>
  );
}

export default LaureateQuickFacts;
