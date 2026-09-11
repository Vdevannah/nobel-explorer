import { Link } from "react-router-dom";

const learningLevels = [
  { name: "Simple", audience: "Grades 4–6", className: "level-simple" },
  { name: "Explore", audience: "Grades 7–9", className: "level-explore" },
  { name: "Advanced", audience: "Grades 10–12", className: "level-advanced" },
  { name: "Expert", audience: "College+", className: "level-expert" },
];

function LearningJourney() {
  return (
    <section className="home-section level-section" aria-labelledby="levels-title">
      <div className="container">
        <div className="level-preview">
          <div className="section-heading section-heading-centered">
            <p className="eyebrow">Learn your way</p>
            <h2 id="levels-title">Learn at Your Level</h2>
            <p>The same Nobel-winning science, explained for every learner.</p>
          </div>
          <div className="level-grid">
            {learningLevels.map((level) => (
              <article className={`level-card ${level.className}`} key={level.name}>
                <span className="level-dot" aria-hidden="true" />
                <strong>{level.name}</strong>
                <small>{level.audience}</small>
              </article>
            ))}
          </div>
          <div className="level-preview-cta">
            <Link className="button button-primary" to="/learn">
              Start Learning <span aria-hidden="true">→</span>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

export default LearningJourney;
