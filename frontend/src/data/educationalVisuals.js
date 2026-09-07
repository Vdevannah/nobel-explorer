import eclipseImage from "../assets/education/solar-eclipse.jpg";
import gpsImage from "../assets/education/gps-satellite.jpg";
import wavesImage from "../assets/education/gravitational-waves.jpg";
import sensorImage from "../assets/education/light-sensor.jpg";
import spectroscopyImage from "../assets/education/photoelectron-spectroscopy.jpg";
import photoelectricAdvancedImage from "../assets/education/photoelectric-advanced.png";
import photoelectricExpertImage from "../assets/education/photoelectric-expert.png";
import photoelectricExploreImage from "../assets/education/photoelectric-explore.png";
import photoelectricSimpleImage from "../assets/education/photoelectric-simple.png";
import relativityAdvancedImage from "../assets/education/relativity-advanced.png";
import relativityExpertImage from "../assets/education/relativity-expert.png";
import relativityExploreImage from "../assets/education/relativity-explore.png";
import relativitySimpleImage from "../assets/education/relativity-simple.png";
import solarImage from "../assets/education/solar-panels.jpg";

export const contributionVisuals = {
  "Photoelectric Effect": {
    thumbnail: {
      label: "hν → e⁻",
      alt: "Photon releasing an electron",
    },
    assetsByLevel: {
      Simple: photoelectricSimpleImage,
      Explore: photoelectricExploreImage,
      Advanced: photoelectricAdvancedImage,
      Expert: photoelectricExpertImage,
    },
    alt: "Photons traveling toward a metal surface and releasing electrons",
    caption: null,
    levelCues: {
      Simple: ["photons", "metal surface", "released electrons"],
      Explore: ["frequency threshold", "energy transfer", "cause → effect"],
      Advanced: ["E = hν", "Kmax = hν − φ", "threshold frequency"],
      Expert: ["eVs = Kmax = hν − φ", "photocurrent", "work function φ"],
    },
  },
  "General Relativity": {
    thumbnail: {
      label: "Gμν",
      alt: "Spacetime curvature symbol",
    },
    assetsByLevel: {
      Simple: relativitySimpleImage,
      Explore: relativityExploreImage,
      Advanced: relativityAdvancedImage,
      Expert: relativityExpertImage,
    },
    alt: "Light following a curved path near a massive star in curved spacetime",
    caption: "Mass and energy curve spacetime, changing the paths of matter and light.",
    levelCues: {
      Simple: ["matter and energy", "curved spacetime", "changed paths"],
      Explore: ["mass-energy", "light bending", "free fall"],
      Advanced: ["equivalence principle", "geodesics", "time dilation"],
      Expert: ["metric gμν", "curvature Gμν", "stress-energy Tμν"],
    },
  },
};

export const connectionVisuals = {
  "Solar Panels / Photovoltaic Technology": {
    kind: "solar",
    imageUrl: solarImage,
    alt: "Sunlight reaching a tilted solar panel",
  },
  "Light Sensors / Photodetectors": {
    kind: "sensor",
    imageUrl: sensorImage,
    alt: "Light entering a camera-style photodetector",
  },
  "Photoelectron Spectroscopy": {
    kind: "spectroscopy",
    imageUrl: spectroscopyImage,
    alt: "A light beam striking a sample while an instrument measures emitted electrons",
  },
  GPS: {
    kind: "gps",
    imageUrl: gpsImage,
    alt: "A navigation satellite sending timing signals toward Earth",
  },
  "1919 Solar Eclipse": {
    kind: "eclipse",
    imageUrl: eclipseImage,
    alt: "The Moon covering the Sun while starlight bends near it",
  },
  "Gravitational Waves": {
    kind: "waves",
    imageUrl: wavesImage,
    alt: "Two orbiting compact objects sending ripples through spacetime",
  },
};

export function getContributionVisual(title) {
  return contributionVisuals[title] ?? null;
}

export function getConnectionVisual(title) {
  return connectionVisuals[title] ?? null;
}
