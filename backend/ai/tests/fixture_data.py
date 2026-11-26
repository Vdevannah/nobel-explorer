"""Shared fixture text for AI tests (kept out of conftest so tests can import it)."""

EXPERT_SENTENCES = [
    "Einstein proposed that light energy arrives in discrete quanta whose energy is proportional to frequency.",
    "An electron absorbs a whole photon, and if the photon energy exceeds the work function the electron escapes the metal.",
    "The maximum kinetic energy of the emitted electrons rises linearly with frequency, not with intensity.",
    "Intensity changes only the number of photons per second, so it changes the photocurrent but not the electron energy.",
    "Millikan's careful measurements confirmed the linear relation and gave an accurate value of Planck's constant.",
    "Below the threshold frequency no electrons are emitted at all, however bright the light becomes.",
    "This behaviour could not be explained by classical wave theory, which predicted a delay and an intensity dependence.",
    "The photon picture therefore became one of the foundations of quantum theory in the early twentieth century.",
    "Modern photoelectron spectroscopy uses the same principle to measure electronic binding energies in materials.",
    "Solar cells and photodetectors rely on related photon absorption processes in semiconductors.",
    "The work function differs between metals, which explains why the threshold frequency depends on the surface.",
    "Einstein's 1921 Nobel Prize motivation cites the law of the photoelectric effect rather than relativity.",
]
EXPERT_TEXT = " ".join(EXPERT_SENTENCES)
