const journeySteps = [
  "Discover",
  "Understand",
  "Connect to Real Life",
  "Learn at Your Level",
  "Test Your Knowledge",
  "Explore Data",
];

const learningLevels = [
  { name: "Simple", audience: "Grades 4–6", className: "level-simple" },
  { name: "Explore", audience: "Grades 7–9", className: "level-explore" },
  { name: "Advanced", audience: "Grades 10–12", className: "level-advanced" },
  { name: "Expert", audience: "College+", className: "level-expert" },
];

function LearningJourney() {
  return (
    <section className="home-section journey-section" aria-labelledby="journey-title">
      <div className="container">
        <div className="section-heading section-heading-centered">
          <p className="eyebrow">Follow your curiosity</p>
          <h2 id="journey-title">Your Learning Journey</h2>
          <p>Move from a big question to a deeper understanding, one step at a time.</p>
        </div>

        <ol className="journey-path">
          {journeySteps.map((step, index) => (
            <li key={step}>
              <span className="journey-number">{index + 1}</span>
              <span>{step}</span>
            </li>
          ))}
        </ol>

        <div className="level-preview" aria-labelledby="levels-title">
          <div className="level-preview-copy">
            <p className="eyebrow">Learn your way</p>
            <h3 id="levels-title">Choose your learning level</h3>
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
        </div>
      </div>
    </section>
  );
}

export default LearningJourney;
