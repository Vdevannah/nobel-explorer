import CategoryExplorer from "../components/home/CategoryExplorer";
import FeaturedLaureate from "../components/home/FeaturedLaureate";
import HeroSection from "../components/home/HeroSection";
import LearningJourney from "../components/home/LearningJourney";
import einsteinFeatured from "../assets/einstein-featured.png";

function HomePage() {
  return (
    <>
      <HeroSection />
      <div className="container home-top-grid">
        <CategoryExplorer />
        <FeaturedLaureate
          name="Albert Einstein"
          category="Physics"
          year={1921}
          description="Discover Einstein's Nobel-winning work and explore the science behind the photoelectric effect."
          imageUrl={einsteinFeatured}
          laureateId={249}
        />
      </div>
      <LearningJourney />
    </>
  );
}

export default HomePage;
