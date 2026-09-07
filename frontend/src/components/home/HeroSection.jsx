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
        </div>

        <figure className="home-hero-artwork">
          <img
            alt="Nobel science illustration featuring the Alfred Nobel medal, laboratory glassware, books, an atom, and a microscope."
            src={nobelScienceHero}
          />
        </figure>
      </div>
    </section>
  );
}

export default HeroSection;
