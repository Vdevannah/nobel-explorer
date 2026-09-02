from backend.database.connection import SessionLocal

from backend.models.category import Category
from backend.models.prize import Prize
from backend.models.laureate import Laureate
from backend.models.laureate_prize import LaureatePrize
from backend.models.institution import Institution
from backend.models.award_affiliation import AwardAffiliation

from backend.repositories.award_affiliation_repository import (
    create,
    get_by_id,
    get_by_laureate_prize,
    get_by_institution,
)


def test_award_affiliation_repository():
    db = SessionLocal()

    try:
        category = Category(
            name="Repository Test Medicine",
            description="Temporary category"
        )

        prize = Prize(
            year=2024,
            motivation="Temporary Nobel prize",
            category=category
        )

        laureate = Laureate(
            full_name="Test Affiliation Laureate",
            laureate_type="Person",
            featured=False
        )

        laureate_prize = LaureatePrize(
            laureate=laureate,
            prize=prize,
            prize_share="1/1"
        )

        institution = Institution(
            name="Repository Test Institute",
            city="Test City",
            state="Massachusetts",
            country="USA"
        )

        db.add_all([category, institution])
        db.flush()

        affiliation = AwardAffiliation(
            laureate_prize=laureate_prize,
            institution=institution
        )

        created_affiliation = create(db, affiliation)

        assert created_affiliation.award_affiliation_id is not None

        found_affiliation = get_by_id(
            db,
            affiliation.award_affiliation_id
        )

        assert found_affiliation is not None

        print(
            "Affiliation ID:",
            found_affiliation.award_affiliation_id
        )

        print(
            "Laureate:",
            found_affiliation.laureate_prize.laureate.full_name
        )

        print(
            "Institution:",
            found_affiliation.institution.name
        )

        award_institutions = get_by_laureate_prize(
            db,
            laureate_prize.laureate_prize_id
        )

        print(
            "Institutions found for award:",
            len(award_institutions)
        )

        institution_awards = get_by_institution(
            db,
            institution.institution_id
        )

        print(
            "Awards found for institution:",
            len(institution_awards)
        )

        print("\nAwardAffiliation repository test passed.")

    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    test_award_affiliation_repository()
