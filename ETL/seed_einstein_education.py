from sqlalchemy.orm import Session

from backend.database.connection import SessionLocal
from backend.repositories import (
    category_repository,
    connection_repository,
    contribution_repository,
    explanation_repository,
    laureate_prize_repository,
    laureate_repository,
    prize_repository,
    quiz_question_repository,
)
from backend.schemas.connection import ConnectionCreate, ConnectionUpdate
from backend.schemas.contribution import ContributionCreate, ContributionUpdate
from backend.schemas.explanation import ExplanationCreate, ExplanationUpdate
from backend.schemas.quiz_question import QuizQuestionCreate, QuizQuestionUpdate
from backend.services import (
    connection_service,
    contribution_service,
    explanation_service,
    quiz_question_service,
)


EINSTEIN_NOBEL_ID = "26"

NOBEL_1921_URL = "https://www.nobelprize.org/prizes/physics/1921/summary/"
GENERAL_RELATIVITY_URL = (
    "https://science.nasa.gov/astrophysics/programs/physics-of-the-cosmos/"
    "general-relativity-and-the-nature-of-spacetime/"
)
DOE_SOLAR_URL = "https://www.energy.gov/cmei/systems/solar-photovoltaic-cell-basics"
NIST_LIGHT_SENSOR_URL = (
    "https://www.nist.gov/news-events/news/2021/04/"
    "light-fantastic-counting-single-photons-unprecedented-rates"
)
NIST_XPS_URL = (
    "https://www.nist.gov/laboratories/tools-instruments/"
    "x-ray-photoelectron-spectroscopy"
)
NIST_GPS_URL = (
    "https://www.nist.gov/atomic-clocks/a-powerful-tool-for-science/"
    "putting-einstein-test"
)
ROYAL_SOCIETY_ECLIPSE_URL = (
    "https://www.royalsociety.org/blog/2024/08/observing-relativity/"
)
NOBEL_2017_URL = "https://www.nobelprize.org/prizes/physics/2017/press-release/"


SOURCE_AUDIT = {
    "Photoelectric Effect": (
        "NobelPrize.org documents the 1921 motivation and Einstein's law of "
        "the photoelectric effect.",
        NOBEL_1921_URL,
    ),
    "Solar Panels / Photovoltaic Technology": (
        "The U.S. Department of Energy explains photon absorption, charge-carrier "
        "generation, and current extraction in semiconductor photovoltaic cells.",
        DOE_SOLAR_URL,
    ),
    "Light Sensors / Photodetectors": (
        "NIST explains photon detection through electron release and carrier "
        "amplification in semiconductor detectors.",
        NIST_LIGHT_SENSOR_URL,
    ),
    "Photoelectron Spectroscopy": (
        "NIST documents X-ray photoelectron spectroscopy for surface chemical "
        "analysis, spectroscopy, imaging, and depth profiling.",
        NIST_XPS_URL,
    ),
    "General Relativity": (
        "NASA describes general relativity as a theory of spacetime with predictions "
        "including gravitational redshift and gravitational waves.",
        GENERAL_RELATIVITY_URL,
    ),
    "GPS": (
        "NIST gives the special- and general-relativistic GPS clock effects and "
        "their approximate net correction.",
        NIST_GPS_URL,
    ),
    "1919 Solar Eclipse": (
        "The Royal Society documents the 29 May 1919 expeditions and their early "
        "observational support for predicted light deflection.",
        ROYAL_SOCIETY_ECLIPSE_URL,
    ),
    "Gravitational Waves": (
        "NobelPrize.org documents Einstein's prediction, LIGO's 2015 observation, "
        "and the 2017 Physics Prize to Weiss, Barish, and Thorne.",
        NOBEL_2017_URL,
    ),
}


PHOTOELECTRIC_EXPLANATIONS = [
    {
        "level": "Simple",
        "explanation_text": (
            "Light is made of tiny bundles of energy called photons.\n\n"
            "When light shines on some metals, a photon can hit an electron. "
            "If the photon has enough energy, it can knock the electron out "
            "of the metal.\n\n"
            "Think of it like a tiny ball hitting another ball and knocking it away."
        ),
        "key_concepts": (
            "Light has tiny energy bundles called photons\n"
            "Metals contain tiny particles called electrons\n"
            "Light can knock electrons out of some metals"
        ),
    },
    {
        "level": "Explore",
        "explanation_text": (
            "Light travels in energy packets called photons. The frequency of light, "
            "which we often notice as its color, determines how much energy each "
            "photon carries. Higher-frequency light has more energy per photon.\n\n"
            "A metal releases an electron only when one photon carries enough energy. "
            "The minimum frequency needed is called the threshold frequency. If the "
            "frequency is too low, the electron stays in the metal.\n\n"
            "Brighter light sends more photons, so it can release more electrons only "
            "when each photon already has enough energy. Making low-frequency light "
            "brighter does not increase the energy of each photon."
        ),
        "key_concepts": (
            "Different frequencies of light carry different amounts of energy\n"
            "A photon needs enough energy to release an electron\n"
            "Brighter low-frequency light cannot replace missing photon energy"
        ),
    },
    {
        "level": "Advanced",
        "explanation_text": (
            "The energy of one photon is E = hν. Here, E is photon energy, h is "
            "Planck's constant, and ν is the frequency of the incident light. Because "
            "h is constant, photon energy increases as frequency increases.\n\n"
            "A metal requires a minimum energy, called its work function φ, to free an "
            "electron. Below the threshold frequency, hν is smaller than φ and no "
            "electrons are emitted. Above the threshold, the energy left after the "
            "electron escapes becomes kinetic energy: Kmax = hν - φ, where Kmax is the "
            "maximum kinetic energy of the emitted electrons.\n\n"
            "Increasing light intensity sends more photons and can emit more electrons, "
            "but at an unchanged frequency it does not increase the energy carried by "
            "each photon."
        ),
        "key_concepts": (
            "Photon energy follows E = hν\n"
            "The work function φ is the minimum energy needed to free an electron\n"
            "Above the threshold, extra photon energy becomes electron kinetic energy"
        ),
    },
    {
        "level": "Expert",
        "explanation_text": (
            "For incident light of frequency ν, each photon carries energy E = hν. "
            "Photoemission begins when this energy reaches the metal's work function φ. "
            "Above that threshold, energy conservation gives Kmax = hν - φ for the "
            "fastest emitted electrons.\n\n"
            "In an experiment, a reverse voltage opposes the photoelectrons. The "
            "stopping potential Vs is the voltage that reduces the photocurrent to zero, "
            "so eVs = Kmax = hν - φ, where e is the elementary charge. Measuring Vs "
            "against ν therefore reveals Kmax and allows the work function to be found.\n\n"
            "Above threshold, increasing frequency raises the stopping potential and "
            "maximum electron kinetic energy. Increasing intensity at fixed frequency "
            "mainly raises the photocurrent because more photoelectrons are collected; "
            "it does not raise the energy of each photon."
        ),
        "key_concepts": (
            "Stopping potential measures the maximum electron kinetic energy\n"
            "Photocurrent reflects how many photoelectrons are collected\n"
            "The work function determines the threshold frequency of a material"
        ),
    },
]


RELATIVITY_EXPLANATIONS = [
    {
        "level": "Simple",
        "explanation_text": (
            "Gravity is more than a pulling force.\n\n"
            "Einstein described space and time as part of one thing called spacetime. "
            "Massive objects, such as stars and planets, can bend spacetime around "
            "them.\n\n"
            "Other objects move through that curved spacetime, which is why their "
            "paths can bend.\n\n"
            "Imagine placing a heavy ball on a stretched sheet. The sheet bends, and "
            "smaller balls moving nearby follow curved paths. This picture is only a "
            "teaching model—real spacetime has more dimensions than a sheet."
        ),
        "key_concepts": (
            "Space and time together are called spacetime\n"
            "Massive objects can curve spacetime\n"
            "Objects move along paths shaped by that curvature"
        ),
    },
    {
        "level": "Explore",
        "explanation_text": (
            "Mass and energy influence the geometry of spacetime, changing the paths "
            "available to objects moving through it.\n\n"
            "Objects in free fall follow the natural paths allowed by curved "
            "spacetime. Light follows those paths too, so a massive star or galaxy can "
            "bend the route light takes.\n\n"
            "Gravity also affects time. Clocks can run at different rates in different "
            "gravitational conditions, such as near a planet compared with farther "
            "away. General relativity was an achievement beyond the work recognized "
            "by Einstein's Nobel Prize."
        ),
        "key_concepts": (
            "Mass and energy affect the geometry of spacetime\n"
            "Free-falling objects follow natural paths through curved spacetime\n"
            "Gravity can bend light and affect how fast clocks run"
        ),
    },
    {
        "level": "Advanced",
        "explanation_text": (
            "The equivalence principle connects free fall with locally inertial "
            "motion: within a small freely falling laboratory, gravity can locally "
            "resemble weightlessness.\n\n"
            "General relativity does not treat gravity simply as a force. Mass-energy "
            "curves spacetime, and freely moving objects follow geodesics—the "
            "straightest possible paths through that curved geometry.\n\n"
            "The curvature deflects light and produces gravitational time dilation. "
            "Clocks deeper in a stronger gravitational field run more slowly relative "
            "to clocks farther away. This theory was not Einstein's Nobel-awarded "
            "contribution."
        ),
        "key_concepts": (
            "The equivalence principle connects gravity and acceleration\n"
            "Free-falling objects follow geodesics in curved spacetime\n"
            "Gravitational fields affect light paths and clock rates"
        ),
    },
    {
        "level": "Expert",
        "explanation_text": (
            "General relativity describes spacetime geometry with the metric tensor "
            "gμν, which defines spacetime intervals and the geodesics followed by "
            "freely moving bodies and light. Curvature is encoded by the Einstein "
            "tensor Gμν.\n\n"
            "The field equation Gμν + Λgμν = (8πG/c⁴)Tμν links geometry to physical "
            "content. Its left side describes spacetime curvature, including the "
            "cosmological constant Λ; its right side contains the stress-energy tensor "
            "Tμν, representing matter, energy, momentum, and pressure.\n\n"
            "The theory predicts gravitational redshift, lensing, orbital corrections, "
            "black holes, and gravitational waves. These predictions provide tests of "
            "the metric and its curvature. General relativity remains distinct from "
            "the photoelectric work cited by the Nobel committee."
        ),
        "key_concepts": (
            "The Einstein field equation links spacetime curvature to matter and energy\n"
            "The metric tensor describes spacetime geometry\n"
            "Geodesics describe free motion through curved spacetime"
        ),
    },
]


PHOTOELECTRIC_CONNECTIONS = [
    {
        "connection_type": "APPLICATION",
        "title": "Solar Panels / Photovoltaic Technology",
        "description": (
            "Modern photovoltaic cells absorb photons in semiconductors to generate "
            "electron-hole charge carriers, then separate and collect those carriers "
            "as electrical current. This is related light-to-electrical-energy physics; "
            "Einstein did not invent solar panels."
        ),
        "source_name": "U.S. Department of Energy",
        "source_url": DOE_SOLAR_URL,
    },
    {
        "connection_type": "APPLICATION",
        "title": "Light Sensors / Photodetectors",
        "description": (
            "Photodetectors convert absorbed photon energy into mobile charge or an "
            "electrical signal. Devices such as photodiodes and avalanche detectors "
            "use this interaction to measure even very faint light."
        ),
        "source_name": "National Institute of Standards and Technology",
        "source_url": NIST_LIGHT_SENSOR_URL,
    },
    {
        "connection_type": "APPLICATION",
        "title": "Photoelectron Spectroscopy",
        "description": (
            "Photoelectron spectroscopy illuminates a sample and measures emitted "
            "electrons. Their kinetic energies reveal electron binding energies, "
            "supporting surface, elemental, and chemical-state analysis."
        ),
        "source_name": "National Institute of Standards and Technology",
        "source_url": NIST_XPS_URL,
    },
]


RELATIVITY_CONNECTIONS = [
    {
        "connection_type": "APPLICATION",
        "title": "GPS",
        "description": (
            "GPS timing accounts for both special and general relativity. Satellite "
            "motion makes onboard clocks run about 7 microseconds per day slower, "
            "while weaker gravity makes them run about 45 microseconds per day faster, "
            "for a net rate about 38 microseconds per day faster before correction."
        ),
        "source_name": "National Institute of Standards and Technology",
        "source_url": NIST_GPS_URL,
    },
    {
        "connection_type": "EXPERIMENTAL_VALIDATION",
        "title": "1919 Solar Eclipse",
        "description": (
            "General relativity predicts that gravity deflects light near a massive "
            "body. During the 29 May 1919 eclipse, expeditions observed stars near the "
            "Sun and measured apparent position shifts. The results provided important "
            "early observational support for Einstein's predicted light deflection."
        ),
        "source_name": "The Royal Society",
        "source_url": ROYAL_SOCIETY_ECLIPSE_URL,
    },
    {
        "connection_type": "SCIENTIFIC_LEGACY",
        "title": "Gravitational Waves",
        "description": (
            "Gravitational waves arise from general relativity and were predicted by "
            "Einstein. LIGO made the first direct observation in 2015. The 2017 Physics "
            "Prize recognized Rainer Weiss, Barry C. Barish, and Kip S. Thorne for "
            "decisive contributions to the LIGO detector and the observation."
        ),
        "source_name": "NobelPrize.org",
        "source_url": NOBEL_2017_URL,
    },
]


# Answer-choice positions below are deliberately varied (not always "A") to
# avoid a guessable pattern, while the underlying scientifically correct
# answer text is unchanged. Distribution across these 12 questions: A x3,
# B x3, C x3, D x3.
PHOTOELECTRIC_QUIZ = [
    {
        "level": "Simple",
        "question": "What can happen when a light-energy packet gives an electron enough energy?",
        "choice_a": "The electron can escape from the material",
        "choice_b": "The electron becomes a proton",
        "choice_c": "The material loses all its atoms",
        "choice_d": "Gravity stops acting",
        "correct_answer": "A",
        "answer_explanation": (
            "A sufficiently energetic photon can transfer enough energy for an "
            "electron to escape the material."
        ),
    },
    {
        "level": "Explore",
        "question": (
            "Above the threshold frequency, what mainly raises the maximum energy "
            "of emitted electrons?"
        ),
        "choice_a": "Increasing the light intensity only",
        "choice_b": "Increasing the light frequency",
        "choice_c": "Making the sample larger",
        "choice_d": "Waiting longer before illumination",
        "correct_answer": "B",
        "answer_explanation": (
            "Photon energy increases with frequency; intensity mainly changes how "
            "many photons arrive."
        ),
    },
    {
        "level": "Advanced",
        "question": "Which equation gives the maximum photoelectron kinetic energy?",
        "choice_a": "Kmax = hν + φ",
        "choice_b": "Kmax = φ - hν for every frequency",
        "choice_c": "Kmax = hν - φ",
        "choice_d": "Kmax = intensity multiplied by time",
        "correct_answer": "C",
        "answer_explanation": (
            "The photon supplies energy hν, and the work function φ is required to "
            "release the electron."
        ),
    },
    {
        "level": "Expert",
        "question": "What does the stopping potential determine in a photoelectric experiment?",
        "choice_a": "The number of atoms in the sample",
        "choice_b": "The speed of light in vacuum",
        "choice_c": "The photon's electric charge",
        "choice_d": "Maximum photoelectron kinetic energy through eVs = Kmax",
        "correct_answer": "D",
        "answer_explanation": (
            "The retarding stopping potential suppresses the fastest photoelectrons, "
            "so eV_s equals their maximum kinetic energy."
        ),
    },
    {
        "level": "Simple",
        "question": "What are the tiny bundles of light energy called?",
        "choice_a": "Photons",
        "choice_b": "Protons",
        "choice_c": "Electrons",
        "choice_d": "Neutrons",
        "correct_answer": "A",
        "answer_explanation": (
            "Light is made of tiny energy bundles called photons."
        ),
    },
    {
        "level": "Simple",
        "question": "In the photoelectric effect, what does light knock out of a metal?",
        "choice_a": "A proton",
        "choice_b": "An electron",
        "choice_c": "The whole atom",
        "choice_d": "A magnet",
        "correct_answer": "B",
        "answer_explanation": (
            "A photon can hit an electron and knock it out of the metal."
        ),
    },
    {
        "level": "Explore",
        "question": (
            "What is the minimum light frequency needed to release an electron "
            "from a metal called?"
        ),
        "choice_a": "Boiling point",
        "choice_b": "Escape velocity",
        "choice_c": "Threshold frequency",
        "choice_d": "Wavelength limit",
        "correct_answer": "C",
        "answer_explanation": (
            "The threshold frequency is the minimum frequency a photon needs to "
            "release an electron."
        ),
    },
    {
        "level": "Explore",
        "question": (
            "If light frequency is below the threshold, what happens no matter "
            "how bright the light is?"
        ),
        "choice_a": "Electrons are released faster",
        "choice_b": "The metal melts",
        "choice_c": "Electrons gain extra mass",
        "choice_d": "No electrons are released",
        "correct_answer": "D",
        "answer_explanation": (
            "Brighter low-frequency light sends more photons, but none of them "
            "carry enough energy to release an electron."
        ),
    },
    {
        "level": "Advanced",
        "question": "In the equation E = hν, what does h represent?",
        "choice_a": "Planck's constant",
        "choice_b": "The speed of light",
        "choice_c": "The electron's charge",
        "choice_d": "The work function",
        "correct_answer": "A",
        "answer_explanation": (
            "h is Planck's constant, which relates a photon's frequency to its "
            "energy."
        ),
    },
    {
        "level": "Advanced",
        "question": (
            "What is the term for the minimum energy needed to free an electron "
            "from a specific metal?"
        ),
        "choice_a": "Kinetic energy",
        "choice_b": "Work function",
        "choice_c": "Threshold voltage",
        "choice_d": "Photon frequency",
        "correct_answer": "B",
        "answer_explanation": (
            "The work function φ is the minimum energy a metal requires to free "
            "an electron."
        ),
    },
    {
        "level": "Expert",
        "question": (
            "In the stopping-potential experiment, what does the elementary "
            "charge e represent in eVs = Kmax?"
        ),
        "choice_a": "The charge of the photon",
        "choice_b": "The charge of the nucleus",
        "choice_c": "The charge of the electron",
        "choice_d": "A unit of frequency",
        "correct_answer": "C",
        "answer_explanation": (
            "e is the elementary charge carried by the electron, linking the "
            "measured stopping voltage to its kinetic energy."
        ),
    },
    {
        "level": "Expert",
        "question": (
            "At a fixed frequency above threshold, increasing light intensity "
            "primarily increases which quantity?"
        ),
        "choice_a": "The maximum kinetic energy per electron",
        "choice_b": "The work function of the metal",
        "choice_c": "The stopping potential",
        "choice_d": "The photocurrent (number of photoelectrons)",
        "correct_answer": "D",
        "answer_explanation": (
            "More intense light delivers more photons per second, raising the "
            "photocurrent, but each photon's energy is unchanged at fixed "
            "frequency."
        ),
    },
]


# Answer-choice positions below are deliberately varied (not always "A") to
# avoid a guessable pattern, while the underlying scientifically correct
# answer text is unchanged. Distribution across these 12 questions: A x3,
# B x3, C x3, D x3.
RELATIVITY_QUIZ = [
    {
        "level": "Simple",
        "question": "What did Einstein say space and time together form?",
        "choice_a": "Spacetime",
        "choice_b": "A rainbow",
        "choice_c": "A magnetic field",
        "choice_d": "A rocket ship",
        "correct_answer": "A",
        "answer_explanation": (
            "Einstein described space and time as one combined thing called "
            "spacetime."
        ),
    },
    {
        "level": "Simple",
        "question": (
            "In the stretched-sheet picture, what happens when you place a heavy "
            "ball on the sheet?"
        ),
        "choice_a": "The sheet turns to ice",
        "choice_b": "The sheet bends",
        "choice_c": "The ball disappears",
        "choice_d": "The sheet flies away",
        "correct_answer": "B",
        "answer_explanation": (
            "The heavy ball bends the sheet, similar to how a massive object "
            "curves spacetime around it."
        ),
    },
    {
        "level": "Simple",
        "question": "What can massive objects like stars do to spacetime?",
        "choice_a": "Erase it",
        "choice_b": "Freeze it",
        "choice_c": "Curve it",
        "choice_d": "Multiply it",
        "correct_answer": "C",
        "answer_explanation": (
            "Massive objects such as stars and planets can bend, or curve, "
            "spacetime around them."
        ),
    },
    {
        "level": "Explore",
        "question": (
            "According to general relativity, what can a massive star or galaxy "
            "do to light passing near it?"
        ),
        "choice_a": "Turn it a different color permanently",
        "choice_b": "Stop it completely",
        "choice_c": "Make it invisible",
        "choice_d": "Bend its path",
        "correct_answer": "D",
        "answer_explanation": (
            "Light follows the curved paths available in spacetime, so massive "
            "objects can bend the route light takes."
        ),
    },
    {
        "level": "Explore",
        "question": "Was general relativity the work for which Einstein received his Nobel Prize?",
        "choice_a": "No, his Nobel Prize was for the photoelectric effect",
        "choice_b": "Yes, it was his Nobel-winning work",
        "choice_c": "He won two separate Nobel Prizes for it",
        "choice_d": "He never explained general relativity",
        "correct_answer": "A",
        "answer_explanation": (
            "Einstein's 1921 Nobel Prize was awarded for the photoelectric "
            "effect, not for general relativity."
        ),
    },
    {
        "level": "Explore",
        "question": "What does general relativity say about clocks in different gravitational conditions?",
        "choice_a": "They all stop working",
        "choice_b": "They can run at different rates",
        "choice_c": "They only work in space",
        "choice_d": "They run backward",
        "correct_answer": "B",
        "answer_explanation": (
            "Gravity affects time, so clocks can run at different rates in "
            "different gravitational conditions."
        ),
    },
    {
        "level": "Advanced",
        "question": "What does the equivalence principle connect?",
        "choice_a": "Light and sound",
        "choice_b": "Electrons and protons",
        "choice_c": "Free fall and locally inertial motion",
        "choice_d": "Voltage and current",
        "correct_answer": "C",
        "answer_explanation": (
            "The equivalence principle connects free fall with locally inertial "
            "motion, since gravity can locally resemble weightlessness."
        ),
    },
    {
        "level": "Advanced",
        "question": (
            "In general relativity, what path do freely moving objects follow "
            "through curved spacetime?"
        ),
        "choice_a": "Straight lines only",
        "choice_b": "Circular orbits only",
        "choice_c": "Random paths",
        "choice_d": "Geodesics",
        "correct_answer": "D",
        "answer_explanation": (
            "Freely moving objects follow geodesics, the straightest possible "
            "paths through curved spacetime."
        ),
    },
    {
        "level": "Advanced",
        "question": (
            "What happens to clocks deeper in a stronger gravitational field, "
            "relative to clocks farther away?"
        ),
        "choice_a": "They run more slowly",
        "choice_b": "They run faster",
        "choice_c": "They stop entirely",
        "choice_d": "They run at the same rate",
        "correct_answer": "A",
        "answer_explanation": (
            "Gravitational time dilation makes clocks deeper in a stronger "
            "gravitational field run more slowly relative to clocks farther "
            "away."
        ),
    },
    {
        "level": "Expert",
        "question": "What does the Einstein field equation relate?",
        "choice_a": "Voltage to current",
        "choice_b": "Spacetime curvature to matter and energy",
        "choice_c": "Frequency to wavelength",
        "choice_d": "Mass to charge",
        "correct_answer": "B",
        "answer_explanation": (
            "The Einstein field equation links spacetime curvature (via the "
            "Einstein tensor) to matter and energy (via the stress-energy "
            "tensor)."
        ),
    },
    {
        "level": "Expert",
        "question": "What mathematical object describes spacetime geometry in general relativity?",
        "choice_a": "The wave function",
        "choice_b": "The Hamiltonian",
        "choice_c": "The metric tensor",
        "choice_d": "The partition function",
        "correct_answer": "C",
        "answer_explanation": (
            "The metric tensor gμν defines spacetime intervals and the "
            "geodesics followed by freely moving bodies and light."
        ),
    },
    {
        "level": "Expert",
        "question": "Which of the following is a prediction of general relativity?",
        "choice_a": "The photoelectric effect",
        "choice_b": "Nuclear fission",
        "choice_c": "Quantum entanglement",
        "choice_d": "Gravitational waves",
        "correct_answer": "D",
        "answer_explanation": (
            "General relativity predicts gravitational waves, later confirmed "
            "by LIGO in 2015."
        ),
    },
]


def _require_existing_nobel_data(db: Session):
    einstein = laureate_repository.get_by_nobel_id(db, EINSTEIN_NOBEL_ID)
    if einstein is None or einstein.full_name != "Albert Einstein":
        raise RuntimeError("Albert Einstein Nobel ID 26 was not found as expected")

    physics = category_repository.get_by_name(db, "Physics")
    if physics is None:
        raise RuntimeError("Physics category was not found")

    prize_1921 = prize_repository.get_by_year_and_category(
        db, 1921, physics.category_id
    )
    prize_2017 = prize_repository.get_by_year_and_category(
        db, 2017, physics.category_id
    )
    if prize_1921 is None or prize_2017 is None:
        raise RuntimeError("The 1921 and 2017 Physics prizes must already exist")

    einstein_prize = laureate_prize_repository.get_by_laureate_and_prize(
        db, einstein.laureate_id, prize_1921.prize_id
    )
    if einstein_prize is None:
        raise RuntimeError("Einstein's 1921 Physics LaureatePrize was not found")
    motivation = (einstein_prize.motivation or "").lower()
    if "photoelectric effect" not in motivation:
        raise RuntimeError("Einstein's stored Nobel motivation was not photoelectric")

    return einstein, einstein_prize, prize_2017


def _upsert_contribution(db: Session, data: ContributionCreate):
    contribution = contribution_repository.get_by_laureate_type_and_title(
        db, data.credited_laureates[0].laureate_id, data.contribution_type, data.title
    )
    if contribution is None:
        return contribution_service.create_contribution(db, data)
    return contribution_service.update_contribution(
        db,
        contribution.contribution_id,
        ContributionUpdate(**data.model_dump()),
    )


def _upsert_explanations(db: Session, contribution_id: int, rows: list[dict]):
    results = []
    for row in rows:
        data = ExplanationCreate(contribution_id=contribution_id, **row)
        explanation = explanation_repository.get_by_contribution_and_level(
            db, contribution_id, data.level
        )
        if explanation is None:
            explanation = explanation_service.create_explanation(db, data)
        else:
            explanation = explanation_service.update_explanation(
                db,
                explanation.explanation_id,
                ExplanationUpdate(**data.model_dump()),
            )
        results.append(explanation)
    return results


def _upsert_connections(
    db: Session,
    contribution_id: int,
    rows: list[dict],
    related_prize_id: int | None = None,
):
    results = []
    for row in rows:
        row_related_prize_id = (
            related_prize_id
            if row["connection_type"] == "SCIENTIFIC_LEGACY"
            else None
        )
        data = ConnectionCreate(
            contribution_id=contribution_id,
            related_prize_id=row_related_prize_id,
            **row,
        )
        connection = connection_repository.get_by_contribution_type_and_title(
            db, contribution_id, data.connection_type, data.title
        )
        if connection is None:
            connection = connection_service.create_connection(db, data)
        else:
            connection = connection_service.update_connection(
                db,
                connection.connection_id,
                ConnectionUpdate(**data.model_dump()),
            )
        results.append(connection)
    return results


def _upsert_quiz(db: Session, contribution_id: int, rows: list[dict]):
    results = []
    for row in rows:
        data = QuizQuestionCreate(contribution_id=contribution_id, **row)
        question = quiz_question_repository.get_by_contribution_and_question(
            db, contribution_id, data.question
        )
        if question is None:
            question = quiz_question_service.create_quiz_question(db, data)
        else:
            question = quiz_question_service.update_quiz_question(
                db,
                question.question_id,
                QuizQuestionUpdate(**data.model_dump()),
            )
        results.append(question)
    return results


def seed_einstein_education(db: Session) -> dict:
    einstein, einstein_prize, prize_2017 = _require_existing_nobel_data(db)

    photoelectric = _upsert_contribution(
        db,
        ContributionCreate(
            credited_laureates=[{
                "laureate_id": einstein.laureate_id,
                "laureate_prize_id": einstein_prize.laureate_prize_id,
            }],
            contribution_type="NOBEL_LINKED",
            title="Photoelectric Effect",
            summary=(
                "Einstein explained the photoelectric effect by treating light energy "
                "as discrete quanta whose energy depends on frequency."
            ),
            significance=(
                "This work helped establish quantum physics and was the work especially "
                "identified in the motivation for Einstein's 1921 Physics Prize—not "
                "general relativity."
            ),
            source_url=NOBEL_1921_URL,
        ),
    )
    relativity = _upsert_contribution(
        db,
        ContributionCreate(
            credited_laureates=[{"laureate_id": einstein.laureate_id}],
            contribution_type="BEYOND_NOBEL",
            title="General Relativity",
            summary=(
                "General relativity describes gravity through the geometry of curved "
                "spacetime shaped by matter and energy."
            ),
            significance=(
                "The theory transformed modern gravitation and underpins predictions "
                "from gravitational time dilation to gravitational waves. It was not "
                "the work for which Einstein received the Nobel Prize."
            ),
            source_url=GENERAL_RELATIVITY_URL,
        ),
    )

    photo_explanations = _upsert_explanations(
        db, photoelectric.contribution_id, PHOTOELECTRIC_EXPLANATIONS
    )
    relativity_explanations = _upsert_explanations(
        db, relativity.contribution_id, RELATIVITY_EXPLANATIONS
    )
    photo_connections = _upsert_connections(
        db, photoelectric.contribution_id, PHOTOELECTRIC_CONNECTIONS
    )
    relativity_connections = _upsert_connections(
        db,
        relativity.contribution_id,
        RELATIVITY_CONNECTIONS,
        related_prize_id=prize_2017.prize_id,
    )
    photo_quiz = _upsert_quiz(db, photoelectric.contribution_id, PHOTOELECTRIC_QUIZ)
    relativity_quiz = _upsert_quiz(db, relativity.contribution_id, RELATIVITY_QUIZ)

    return {
        "einstein_id": einstein.laureate_id,
        "einstein_laureate_prize_id": einstein_prize.laureate_prize_id,
        "photoelectric_id": photoelectric.contribution_id,
        "relativity_id": relativity.contribution_id,
        "related_2017_prize_id": prize_2017.prize_id,
        "photoelectric_explanations": len(photo_explanations),
        "relativity_explanations": len(relativity_explanations),
        "photoelectric_connections": len(photo_connections),
        "relativity_connections": len(relativity_connections),
        "photoelectric_quiz_questions": len(photo_quiz),
        "relativity_quiz_questions": len(relativity_quiz),
    }


def print_source_audit() -> None:
    print("Authoritative source audit:")
    for title, (support, url) in SOURCE_AUDIT.items():
        print(f"- {title}: {support}")
        print(f"  {url}")


def main() -> None:
    print_source_audit()
    db = SessionLocal()
    try:
        result = seed_einstein_education(db)
        db.commit()
        print("Einstein educational seed complete:", result)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
