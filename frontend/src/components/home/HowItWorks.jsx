const steps = [
  { icon: "🔭", title: "Explore", description: "Discover Nobel Prizes and laureates." },
  { icon: "📖", title: "Learn", description: "Understand the science at your level." },
  { icon: "💡", title: "Quiz", description: "Test your understanding with interactive questions." },
  { icon: "📊", title: "Analyze", description: "Explore Nobel trends and data." },
];

function HowItWorks() {
  return (
    <section className="home-section how-it-works-section" aria-labelledby="how-it-works-title">
      <div className="container">
        <div className="section-heading section-heading-centered">
          <p className="eyebrow">How it works</p>
          <h2 id="how-it-works-title">How Nobel Explorer Works</h2>
          <p>From Nobel discoveries to a deeper understanding — in four simple steps.</p>
        </div>

        <ol className="how-it-works-steps">
          {steps.map((step, index) => (
            <li className="how-it-works-step" key={step.title}>
              <div className="how-it-works-card">
                <span className="how-it-works-number" aria-hidden="true">{index + 1}</span>
                <span className="how-it-works-icon" aria-hidden="true">{step.icon}</span>
                <p className="how-it-works-title">{step.title}</p>
                <p className="how-it-works-description">{step.description}</p>
              </div>
              {index < steps.length - 1 && (
                <span className="how-it-works-arrow" aria-hidden="true">→</span>
              )}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

export default HowItWorks;
