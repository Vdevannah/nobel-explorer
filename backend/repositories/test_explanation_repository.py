from sqlalchemy.exc import IntegrityError

from backend.database.connection import SessionLocal

from backend.models.category import Category
from backend.models.prize import Prize
from backend.models.laureate import Laureate
from backend.models.laureate_prize import LaureatePrize
from backend.models.contribution import Contribution
from backend.models.explanation import Explanation

from backend.repositories.explanation_repository import (
    create,
    get_by_id,
    get_by_contribution,
    get_by_contribution_and_level,
    update,
    delete,
)


def test_explanation_repository():
    db = SessionLocal()

    try:
        # Build temporary parent records
        category = Category(
            name="Repository Test Explanation Category",
            description="Temporary category"
        )

        prize = Prize(
            year=2024,
            category=category
        )

        laureate = Laureate(
            nobel_laureate_id="TEST-014",
            full_name="Test Explanation Laureate",
            laureate_type="Person",
            featured=True
        )

        laureate_prize = LaureatePrize(
            laureate=laureate,
            prize=prize,
            prize_share="1/1",
            motivation="Temporary Nobel prize"
        )

        contribution = Contribution(
            laureate=laureate,
            laureate_prize=laureate_prize,
            contribution_type="NOBEL_LINKED",
            title="Test Contribution",
            summary="Temporary contribution",
            significance="Temporary significance"
        )

        db.add(category)
        db.flush()

        # CREATE four learning levels
        levels = [
            ("Simple", "Simple explanation", "basic concept"),
            ("Explore", "Explore explanation", "intermediate concept"),
            ("Advanced", "Advanced explanation", "advanced concept"),
            ("Expert", "Expert explanation", "expert concept"),
        ]

        created_explanations = []

        for level, text, concepts in levels:
            explanation = Explanation(
                contribution=contribution,
                level=level,
                explanation_text=text,
                key_concepts=concepts
            )

            created_explanation = create(
                db,
                explanation
            )

            created_explanations.append(
                created_explanation
            )

        print(
            "Explanations created:",
            len(created_explanations)
        )

        # READ BY ID
        simple_explanation = get_by_id(
            db,
            created_explanations[0].explanation_id
        )

        print(
            "Found by ID:",
            simple_explanation.level
        )

        # READ ALL EXPLANATIONS FOR APPLICATION
        contribution_explanations = get_by_contribution(
            db,
            contribution.contribution_id
        )

        print(
            "Explanations found for application:",
            len(contribution_explanations)
        )

        # READ SPECIFIC LEVEL
        advanced_explanation = get_by_contribution_and_level(
            db,
            contribution.contribution_id,
            "Advanced"
        )

        print(
            "Advanced Explanation:",
            advanced_explanation.explanation_text
        )

        # UPDATE
        updated_explanation = update(
            db,
            advanced_explanation,
            level="Advanced",
            explanation_text="Updated advanced explanation",
            key_concepts="updated advanced concepts"
        )

        print(
            "Updated Explanation:",
            updated_explanation.explanation_text
        )

        # UNIQUE CONSTRAINT: an application cannot have two explanations
        # at the same learning level. A savepoint keeps the outer test
        # transaction usable after MySQL rejects the duplicate.
        duplicate_level_prevented = False

        try:
            with db.begin_nested():
                duplicate_explanation = Explanation(
                    contribution=contribution,
                    level="Simple",
                    explanation_text="Duplicate simple explanation",
                    key_concepts="duplicate concept"
                )
                create(db, duplicate_explanation)
        except IntegrityError:
            duplicate_level_prevented = True

        assert duplicate_level_prevented

        print(
            "Duplicate contribution/level prevented:",
            duplicate_level_prevented
        )

        # DELETE
        delete(
            db,
            updated_explanation
        )

        deleted_explanation = get_by_id(
            db,
            updated_explanation.explanation_id
        )

        print(
            "Explanation after delete:",
            deleted_explanation
        )

        print(
            "\nExplanation repository CRUD test passed."
        )

    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    test_explanation_repository()
    
