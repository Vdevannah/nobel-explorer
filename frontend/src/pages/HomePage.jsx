import CategoryExplorer from "../components/home/CategoryExplorer";
import FeaturedLaureate from "../components/home/FeaturedLaureate";
import HeroSection from "../components/home/HeroSection";
import LearningJourney from "../components/home/LearningJourney";

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
          description="Explore the story and Nobel-recognized work of Albert Einstein."
        />
      </div>
      <LearningJourney />
    </>
  );
}

export default HomePage;
