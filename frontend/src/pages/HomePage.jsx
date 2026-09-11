import CategoryExplorer from "../components/home/CategoryExplorer";
import FeaturedLaureate from "../components/home/FeaturedLaureate";
import HeroSection from "../components/home/HeroSection";
import HowItWorks from "../components/home/HowItWorks";
import LearningJourney from "../components/home/LearningJourney";
import einsteinFeatured from "../assets/einstein-featured.png";

function HomePage() {
  return (
    <>
      <HeroSection />
      <CategoryExplorer />
      <FeaturedLaureate
        name="Albert Einstein"
        category="Physics"
        year={1921}
        contributionTitle="Photoelectric Effect"
        description="Discover Einstein's Nobel-winning work and explore the science behind the photoelectric effect."
        imageUrl={einsteinFeatured}
        laureateId={249}
        ctaLabel="Explore Einstein"
      />
      <HowItWorks />
      <LearningJourney />
    </>
  );
}

export default HomePage;
