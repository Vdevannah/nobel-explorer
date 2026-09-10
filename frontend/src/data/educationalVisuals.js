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
import mrnaAdvancedImage from "../assets/education/mrna-advanced.png";
import mrnaExpertImage from "../assets/education/mrna-expert.png";
import mrnaExploreImage from "../assets/education/mrna-explore.png";
import mrnaSimpleImage from "../assets/education/mrna-simple.png";
import mrnaVaccinesApplicationImage from "../assets/education/mrna-vaccines-application.png";
import mrnaFutureMedicinesApplicationImage from "../assets/education/mrna-future-medicines-application.png";
import mrnaRnaSensingApplicationImage from "../assets/education/mrna-rna-sensing-application.png";
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
  "Nucleoside Base Modifications and mRNA Vaccines": {
    thumbnail: {
      label: "U → Ψ",
      alt: "Uridine transforming into pseudouridine",
    },
    assetsByLevel: {
      Simple: mrnaSimpleImage,
      Explore: mrnaExploreImage,
      Advanced: mrnaAdvancedImage,
      Expert: mrnaExpertImage,
    },
    alt: "Diagram of nucleoside-modified mRNA reducing innate immune activation",
    caption: null,
    altByLevel: {
      Simple:
        "An mRNA message flowing into a cell to make a protein, with unmodified and modified versions compared",
      Explore:
        "DNA to mRNA to protein flow, comparing unmodified and modified mRNA immune responses, and uridine becoming pseudouridine",
      Advanced:
        "Synthetic mRNA delivered to a dendritic cell, comparing unmodified RNA triggering inflammatory signaling against modified nucleosides producing an antigen and adaptive immune response",
      Expert:
        "In-vitro-transcribed mRNA sensed by endosomal and cytosolic RNA receptors compared with nucleoside-modified mRNA, distinguishing pseudouridine from N1-methylpseudouridine and separating the Nobel-recognized discovery from later vaccine engineering",
    },
    levelCues: {
      Simple: ["mRNA message", "cell reads it", "protein"],
      Explore: ["uridine → pseudouridine", "innate immune reaction", "protein production"],
      Advanced: ["dendritic cell", "Toll-like receptors", "adaptive immune response"],
      Expert: ["TLR3/7/8", "RIG-I/MDA5", "Ψ vs m1Ψ"],
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
  "mRNA Vaccines": {
    kind: "mrna-vaccines",
    imageUrl: mrnaVaccinesApplicationImage,
    alt: "A COVID-19 mRNA vaccine vial, lipid nanoparticle, and cell producing spike protein that trains antibodies",
  },
  "Therapeutic mRNA / Future Medicines": {
    kind: "mrna-future-medicines",
    imageUrl: mrnaFutureMedicinesApplicationImage,
    alt: "Therapeutic mRNA entering a cell to make a therapeutic protein, with cancer, antibody, and protein-replacement applications",
  },
  "Understanding Innate Immune Recognition of RNA": {
    kind: "mrna-rna-sensing",
    imageUrl: mrnaRnaSensingApplicationImage,
    alt: "Foreign RNA recognized by innate immune sensors such as TLR7/8 and RIG-I, triggering immune signaling and response",
  },
};

export function getContributionVisual(title) {
  return contributionVisuals[title] ?? null;
}

export function getConnectionVisual(title) {
  return connectionVisuals[title] ?? null;
}
