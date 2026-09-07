import { Link } from "react-router-dom";

const CATEGORY_ICONS = {
  Physics: "⚛",
  Chemistry: "⚗",
  "Physiology or Medicine": "♥",
  Literature: "▤",
  Peace: "❧",
  "Economic Sciences": "▥",
};

function PrizeCard({ prize }) {
  const icon = CATEGORY_ICONS[prize.category.name] || "✦";

  return (
    <article className="prize-card">
      <div className="prize-card-top">
        <span className="prize-card-icon" aria-hidden="true">{icon}</span>
        <p className="prize-card-category">{prize.category.name}</p>
      </div>
      <h2>{prize.year}</h2>
      <Link className="prize-card-link" to={`/prizes/${prize.prize_id}`}>
        Explore Prize <span aria-hidden="true">→</span>
      </Link>
    </article>
  );
}

export default PrizeCard;
