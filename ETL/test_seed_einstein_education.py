from backend.database.connection import SessionLocal
from backend.repositories import (
    connection_repository,
    contribution_repository,
    explanation_repository,
    quiz_question_repository,
)
from ETL.seed_einstein_education import seed_einstein_education


def test_einstein_seed_is_idempotent_and_complete():
    db = SessionLocal()
    try:
        first = seed_einstein_education(db)
        second = seed_einstein_education(db)

        assert first["photoelectric_id"] == second["photoelectric_id"]
        assert first["relativity_id"] == second["relativity_id"]
        assert first["related_2017_prize_id"] == second["related_2017_prize_id"]

        contributions = contribution_repository.get_by_laureate(
            db, first["einstein_id"]
        )
        assert len(contributions) == 2

        photoelectric = contribution_repository.get_by_id(
            db, first["photoelectric_id"]
        )
        relativity = contribution_repository.get_by_id(
            db, first["relativity_id"]
        )
        assert photoelectric.contribution_type == "NOBEL_LINKED"
        assert photoelectric.laureate_prize_id == first["einstein_laureate_prize_id"]
        assert relativity.contribution_type == "BEYOND_NOBEL"
        assert relativity.laureate_prize_id is None

        assert len(
            explanation_repository.get_by_contribution(
                db, photoelectric.contribution_id
            )
        ) == 4
        simple = next(
            explanation
            for explanation in explanation_repository.get_by_contribution(
                db, photoelectric.contribution_id
            )
            if explanation.level == "Simple"
        )
        assert simple.explanation_text == (
            "Light is made of tiny bundles of energy called photons.\n\n"
            "When light shines on some metals, a photon can hit an electron. "
            "If the photon has enough energy, it can knock the electron out "
            "of the metal.\n\n"
            "Think of it like a tiny ball hitting another ball and knocking it away."
        )
        assert simple.key_concepts == (
            "Light has tiny energy bundles called photons\n"
            "Metals contain tiny particles called electrons\n"
            "Light can knock electrons out of some metals"
        )
        explanations_by_level = {
            explanation.level: explanation
            for explanation in explanation_repository.get_by_contribution(
                db, photoelectric.contribution_id
            )
        }
        assert explanations_by_level["Explore"].key_concepts == (
            "Different frequencies of light carry different amounts of energy\n"
            "A photon needs enough energy to release an electron\n"
            "Brighter low-frequency light cannot replace missing photon energy"
        )
        assert explanations_by_level["Advanced"].key_concepts == (
            "Photon energy follows E = hν\n"
            "The work function φ is the minimum energy needed to free an electron\n"
            "Above the threshold, extra photon energy becomes electron kinetic energy"
        )
        assert explanations_by_level["Expert"].key_concepts == (
            "Stopping potential measures the maximum electron kinetic energy\n"
            "Photocurrent reflects how many photoelectrons are collected\n"
            "The work function determines the threshold frequency of a material"
        )
        assert "E = hν" in explanations_by_level["Advanced"].explanation_text
        assert "Kmax = hν - φ" in explanations_by_level["Advanced"].explanation_text
        assert "eVs = Kmax = hν - φ" in explanations_by_level["Expert"].explanation_text
        for explanation in explanations_by_level.values():
            assert "hf" not in explanation.explanation_text
            assert "hf" not in (explanation.key_concepts or "")
        assert len(
            explanation_repository.get_by_contribution(db, relativity.contribution_id)
        ) == 4
        relativity_explanations = {
            explanation.level: explanation
            for explanation in explanation_repository.get_by_contribution(
                db, relativity.contribution_id
            )
        }
        assert set(relativity_explanations) == {
            "Simple",
            "Explore",
            "Advanced",
            "Expert",
        }
        assert relativity_explanations["Simple"].key_concepts == (
            "Space and time together are called spacetime\n"
            "Massive objects can curve spacetime\n"
            "Objects move along paths shaped by that curvature"
        )
        assert "teaching model" in relativity_explanations["Simple"].explanation_text
        assert relativity_explanations["Explore"].key_concepts == (
            "Mass and energy affect the geometry of spacetime\n"
            "Free-falling objects follow natural paths through curved spacetime\n"
            "Gravity can bend light and affect how fast clocks run"
        )
        assert relativity_explanations["Advanced"].key_concepts == (
            "The equivalence principle connects gravity and acceleration\n"
            "Free-falling objects follow geodesics in curved spacetime\n"
            "Gravitational fields affect light paths and clock rates"
        )
        assert relativity_explanations["Expert"].key_concepts == (
            "The Einstein field equation links spacetime curvature to matter and energy\n"
            "The metric tensor describes spacetime geometry\n"
            "Geodesics describe free motion through curved spacetime"
        )
        assert (
            "Gμν + Λgμν = (8πG/c⁴)Tμν"
            in relativity_explanations["Expert"].explanation_text
        )
        assert len(
            connection_repository.get_by_contribution(
                db, photoelectric.contribution_id
            )
        ) == 3
        relativity_connections = connection_repository.get_by_contribution(
            db, relativity.contribution_id
        )
        assert len(relativity_connections) == 3
        assert {
            connection.title: connection.connection_type
            for connection in relativity_connections
        } == {
            "GPS": "APPLICATION",
            "1919 Solar Eclipse": "EXPERIMENTAL_VALIDATION",
            "Gravitational Waves": "SCIENTIFIC_LEGACY",
        }
        gravitational_waves = next(
            connection
            for connection in relativity_connections
            if connection.title == "Gravitational Waves"
        )
        assert gravitational_waves.related_prize_id == first["related_2017_prize_id"]
        photoelectric_quiz = quiz_question_repository.get_by_contribution(
            db, photoelectric.contribution_id
        )
        assert len(photoelectric_quiz) == 12
        photoelectric_quiz_by_level = {}
        for quiz_question in photoelectric_quiz:
            photoelectric_quiz_by_level.setdefault(quiz_question.level, 0)
            photoelectric_quiz_by_level[quiz_question.level] += 1
        assert photoelectric_quiz_by_level == {
            "Simple": 3,
            "Explore": 3,
            "Advanced": 3,
            "Expert": 3,
        }

        relativity_quiz = quiz_question_repository.get_by_contribution(
            db, relativity.contribution_id
        )
        assert len(relativity_quiz) == 12
        relativity_quiz_by_level = {}
        for quiz_question in relativity_quiz:
            relativity_quiz_by_level.setdefault(quiz_question.level, 0)
            relativity_quiz_by_level[quiz_question.level] += 1
        assert relativity_quiz_by_level == {
            "Simple": 3,
            "Explore": 3,
            "Advanced": 3,
            "Expert": 3,
        }
    finally:
        db.rollback()
        db.close()
