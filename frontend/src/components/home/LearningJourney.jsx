import { Link } from "react-router-dom";

import simpleCharacter from "../../assets/learning-levels/simple.png";
import exploreCharacter from "../../assets/learning-levels/explore.png";
import advancedCharacter from "../../assets/learning-levels/advanced.png";
import expertCharacter from "../../assets/learning-levels/expert.png";

const learningLevels = [
  {
    name: "Simple",
    audience: "Grades 4–6",
    description: "Everyday language, minimal math",
    className: "level-simple",
    image: simpleCharacter,
  },
  {
    name: "Explore",
    audience: "Grades 7–9",
    description: "Build vocabulary and understanding",
    className: "level-explore",
    image: exploreCharacter,
  },
  {
    name: "Advanced",
    audience: "Grades 10–12",
    description: "Use equations and deeper reasoning",
    className: "level-advanced",
    image: advancedCharacter,
  },
  {
    name: "Expert",
    audience: "College+",
    description: "Technical details and full scientific context",
    className: "level-expert",
    image: expertCharacter,
  },
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
                <img
                  className="level-card-image"
                  src={level.image}
                  alt={`${level.name} learning level`}
                />
                <strong>{level.name}</strong>
                <small>{level.audience}</small>
                <p className="level-card-description">{level.description}</p>
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
