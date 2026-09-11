from backend.database.connection import SessionLocal
from backend.repositories import (
    connection_repository,
    contribution_repository,
    explanation_repository,
    quiz_question_repository,
)
from ETL.seed_click_chemistry_education import seed_click_chemistry_education


def test_click_chemistry_seed_is_idempotent_and_shared_between_all_three_laureates():
    db = SessionLocal()
    try:
        first = seed_click_chemistry_education(db)
        second = seed_click_chemistry_education(db)

        # Idempotent: re-running resolves to the exact same contribution.
        assert (
            first["click_chemistry_contribution_id"]
            == second["click_chemistry_contribution_id"]
        )
        assert first["prize_id"] == 261
        assert first["bertozzi_id"] == 356
        assert first["meldal_id"] == 886
        assert first["sharpless_id"] == 766
        assert first["bertozzi_laureate_prize_id"] == 333
        assert first["meldal_laureate_prize_id"] == 870
        assert first["sharpless_laureate_prize_id"] == 748

        contribution_id = first["click_chemistry_contribution_id"]
        contribution = contribution_repository.get_by_id(db, contribution_id)
        assert contribution.contribution_type == "NOBEL_LINKED"
        assert contribution.title == "Click Chemistry and Bioorthogonal Chemistry"

        # Shared attribution: exactly one contribution, credited to all
        # three laureates, each keeping their own award link -- not three
        # separate per-laureate contributions.
        credits = {
            credit.laureate_id: credit for credit in contribution.credited_laureates
        }
        assert set(credits) == {356, 886, 766}
        assert credits[356].laureate_prize_id == 333
        assert credits[886].laureate_prize_id == 870
        assert credits[766].laureate_prize_id == 748

        # Discoverable from all three laureates, as the SAME contribution_id,
        # and re-running the seed a second time must not duplicate it.
        bertozzi_contributions = contribution_repository.get_by_laureate(db, 356)
        meldal_contributions = contribution_repository.get_by_laureate(db, 886)
        sharpless_contributions = contribution_repository.get_by_laureate(db, 766)
        assert [c.contribution_id for c in bertozzi_contributions].count(
            contribution_id
        ) == 1
        assert [c.contribution_id for c in meldal_contributions].count(
            contribution_id
        ) == 1
        assert [c.contribution_id for c in sharpless_contributions].count(
            contribution_id
        ) == 1

        # Exactly 4 explanations, one per learning level.
        explanations = explanation_repository.get_by_contribution(
            db, contribution_id
        )
        assert len(explanations) == 4
        assert {explanation.level for explanation in explanations} == {
            "Simple",
            "Explore",
            "Advanced",
            "Expert",
        }
        explanations_by_level = {
            explanation.level: explanation for explanation in explanations
        }
        assert "cyclooctyne" in explanations_by_level["Advanced"].explanation_text.lower()
        assert "SPAAC" in explanations_by_level["Expert"].explanation_text
        assert (
            "metabolic labeling"
            in explanations_by_level["Expert"].explanation_text.lower()
        )

        # Exactly 3 connections, all APPLICATION.
        connections = connection_repository.get_by_contribution(
            db, contribution_id
        )
        assert len(connections) == 3
        assert {connection.title: connection.connection_type for connection in connections} == {
            "Visualizing Biomolecules in Living Systems": "APPLICATION",
            "Building Better Medicines": "APPLICATION",
            "Targeted Cancer Research": "APPLICATION",
        }
        for connection in connections:
            assert connection.source_url is not None
            assert connection.source_url.startswith("https://www.nobelprize.org/")

        # Exactly 12 quiz questions, 3 per level, answers hidden from the
        # public schema (checked at the route layer, not here).
        quiz_questions = quiz_question_repository.get_by_contribution(
            db, contribution_id
        )
        assert len(quiz_questions) == 12
        quiz_by_level = {}
        for question in quiz_questions:
            quiz_by_level.setdefault(question.level, 0)
            quiz_by_level[question.level] += 1
        assert quiz_by_level == {
            "Simple": 3,
            "Explore": 3,
            "Advanced": 3,
            "Expert": 3,
        }

        # Required correct-answer distribution: A x3, B x3, C x3, D x3.
        answer_counts = {}
        for question in quiz_questions:
            answer_counts.setdefault(question.correct_answer, 0)
            answer_counts[question.correct_answer] += 1
        assert answer_counts == {"A": 3, "B": 3, "C": 3, "D": 3}

        # Catalog exposes the contribution exactly once, crediting all
        # three laureates by name.
        catalog = contribution_repository.list_catalog(db)
        matches = [item for item in catalog if item.contribution_id == contribution_id]
        assert len(matches) == 1
    finally:
        db.rollback()
        db.close()
