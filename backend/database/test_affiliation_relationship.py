from backend.database.connection import SessionLocal
from backend.models import (
    Category,
    Prize,
    Laureate,
    LaureatePrize,
    Institution,
    AwardAffiliation,
)


def test_affiliation_relationship():
    db = SessionLocal()

    try:
        category = Category(
            name="Test Physics",
            description="Temporary test category"
        )

        prize = Prize(
            year=2025,
            motivation="Temporary test prize",
            category=category
        )

        laureate = Laureate(
            full_name="Test Laureate",
            laureate_type="Person",
            birth_city="Test City",
            birth_state="California",
            birth_country="USA",
            featured=False
        )

        laureate_prize = LaureatePrize(
            laureate=laureate,
            prize=prize,
            prize_share="1/2"
        )

        institution = Institution(
            name="Test University",
            city="Test City",
            state="California",
            country="USA"
        )

        affiliation = AwardAffiliation(
            laureate_prize=laureate_prize,
            institution=institution
        )

        db.add(category)

        # Send SQL to MySQL, but DO NOT permanently save it.
        db.flush()

        print("Laureate:", laureate.full_name)
        print("Birth State:", laureate.birth_state)
        print("Prize:", laureate_prize.prize.year)
        print("Institution:", laureate_prize.award_affiliations[0].institution.name)
        print("Institution State:", institution.state)

        print("\nAffiliation relationship test passed.")

    finally:
        # Because we never commit, this removes the temporary records.
        db.rollback()
        db.close()


if __name__ == "__main__":
    test_affiliation_relationship()