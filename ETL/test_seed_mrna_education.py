from backend.database.connection import SessionLocal
from backend.repositories import (
    connection_repository,
    contribution_repository,
    explanation_repository,
    quiz_question_repository,
)
from ETL.seed_mrna_education import seed_mrna_education


def test_mrna_seed_is_idempotent_and_shared_between_both_laureates():
    db = SessionLocal()
    try:
        first = seed_mrna_education(db)
        second = seed_mrna_education(db)

        # Idempotent: re-running resolves to the exact same contribution.
        assert first["mrna_contribution_id"] == second["mrna_contribution_id"]
        assert first["prize_id"] == 318
        assert first["kariko_id"] == 774
        assert first["weissman_id"] == 428
        assert first["kariko_laureate_prize_id"] == 756
        assert first["weissman_laureate_prize_id"] == 405

        contribution_id = first["mrna_contribution_id"]
        contribution = contribution_repository.get_by_id(db, contribution_id)
        assert contribution.contribution_type == "NOBEL_LINKED"
        assert contribution.title == (
            "Nucleoside Base Modifications and mRNA Vaccines"
        )

        # Shared attribution: exactly one contribution, credited to both
        # laureates, each keeping their own award link -- not two separate
        # per-laureate contributions.
        credits = {
            credit.laureate_id: credit for credit in contribution.credited_laureates
        }
        assert set(credits) == {774, 428}
        assert credits[774].laureate_prize_id == 756
        assert credits[428].laureate_prize_id == 405

        # Discoverable from both laureates, as the SAME contribution_id, and
        # re-running the seed a second time must not duplicate it.
        kariko_contributions = contribution_repository.get_by_laureate(db, 774)
        weissman_contributions = contribution_repository.get_by_laureate(db, 428)
        assert [c.contribution_id for c in kariko_contributions].count(
            contribution_id
        ) == 1
        assert [c.contribution_id for c in weissman_contributions].count(
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
        assert "pseudouridine" in explanations_by_level["Advanced"].explanation_text
        assert "Toll-like receptors" in explanations_by_level["Expert"].explanation_text
        assert (
            "lipid nanoparticle"
            in explanations_by_level["Expert"].explanation_text
        )

        # Exactly 3 connections, using only existing enum values.
        connections = connection_repository.get_by_contribution(
            db, contribution_id
        )
        assert len(connections) == 3
        assert {connection.title: connection.connection_type for connection in connections} == {
            "mRNA Vaccines": "APPLICATION",
            "Therapeutic mRNA / Future Medicines": "APPLICATION",
            "Understanding Innate Immune Recognition of RNA": "SCIENTIFIC_LEGACY",
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

        # Catalog exposes the contribution exactly once, crediting both
        # laureates by name.
        catalog = contribution_repository.list_catalog(db)
        matches = [item for item in catalog if item.contribution_id == contribution_id]
        assert len(matches) == 1
    finally:
        db.rollback()
        db.close()
