import { Link } from "react-router-dom";

import nobelScienceHero from "../../assets/nobel-science-hero.png";

function HeroSection() {
  return (
    <section className="home-hero" aria-labelledby="home-hero-title">
      <div className="cosmic-glow cosmic-glow-left" aria-hidden="true" />
      <div className="cosmic-glow cosmic-glow-right" aria-hidden="true" />

      <div className="container home-hero-layout">
        <div className="home-hero-copy">
          <p className="eyebrow">
            Explore <span>•</span> Learn <span>•</span> Be Inspired
          </p>
          <h1 id="home-hero-title">
            Discover the greatest minds.
            <span>Understand their ideas.</span>
            <span>Change your world.</span>
          </h1>
          <p className="home-hero-description">
            Nobel Explorer helps students understand Nobel-winning discoveries,
            why they matter, and how their impact reaches into everyday life.
          </p>
          <div className="home-hero-actions">
            <Link className="button button-primary" to="/prizes">
              Explore Nobel Prizes <span aria-hidden="true">→</span>
            </Link>
            <Link className="button button-secondary" to="/learn">
              Start Learning <span aria-hidden="true">→</span>
            </Link>
          </div>
        </div>

        <div className="home-hero-visual">
          <figure className="home-hero-artwork">
            <img
              alt="Nobel science illustration featuring the Alfred Nobel medal, laboratory glassware, books, an atom, and a microscope."
              src={nobelScienceHero}
            />
          </figure>
          <blockquote className="home-hero-quote">
            <p>The important thing is not to stop questioning.</p>
            <cite>— Albert Einstein</cite>
          </blockquote>
        </div>
      </div>
    </section>
  );
}

export default HeroSection;
