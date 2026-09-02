from datetime import date

from backend.database.connection import SessionLocal

from backend.models.category import Category
from backend.models.prize import Prize
from backend.models.laureate import Laureate
from backend.models.laureate_prize import LaureatePrize
from backend.models.institution import Institution
from backend.models.award_affiliation import AwardAffiliation

from backend.repositories.analytics_repository import (
    count_total_laureates,
    count_total_prizes,
    get_laureate_counts_by_category,
    get_laureate_counts_by_country_and_category,
    get_us_birth_state_counts_by_category,
    get_institution_counts_by_category,
    get_gender_counts_by_category,
    get_laureate_counts_by_decade,
    get_average_age_at_award_by_category,
)


def test_analytics_repository():
    db = SessionLocal()

    try:
        # =========================================================
        # 1. CATEGORIES
        # =========================================================

        chemistry = Category(
            name="Chemistry",
            description="Temporary test category"
        )

        medicine = Category(
            name="Medicine",
            description="Temporary test category"
        )

        # =========================================================
        # 2. PRIZES
        # =========================================================

        chemistry_prize = Prize(
            year=2024,
            motivation="Temporary chemistry prize",
            category=chemistry
        )

        medicine_prize = Prize(
            year=2024,
            motivation="Temporary medicine prize",
            category=medicine
        )

        # Extra prizes for decade analytics

        prize_1984 = Prize(
            year=1984,
            motivation="Temporary 1980s prize",
            category=chemistry
        )

        prize_1995 = Prize(
            year=1995,
            motivation="Temporary 1990s prize",
            category=chemistry
        )

        prize_2006 = Prize(
            year=2006,
            motivation="Temporary 2000s prize",
            category=chemistry
        )

        # =========================================================
        # 3. LAUREATES
        # =========================================================

        laureate_one = Laureate(
            full_name="Test Laureate One",
            laureate_type="Person",
            birth_country="United States",
            birth_state="California",
            gender="Female",
            featured=False
        )

        laureate_two = Laureate(
            full_name="Test Laureate Two",
            laureate_type="Person",
            birth_country="Germany",
            gender="Male",
            featured=False
        )

        # Medicine laureates have birth dates for Step 7 testing

        laureate_three = Laureate(
            full_name="Test Laureate Three",
            laureate_type="Person",
            birth_date=date(1964, 1, 1),
            birth_country="United States",
            birth_state="New York",
            gender="Female",
            featured=False
        )

        laureate_four = Laureate(
            full_name="Test Laureate Four",
            laureate_type="Person",
            birth_date=date(1974, 1, 1),
            birth_country="United States",
            birth_state="California",
            gender="Male",
            featured=False
        )

        laureate_five = Laureate(
            full_name="Test Laureate Five",
            laureate_type="Person",
            birth_date=date(1984, 1, 1),
            birth_country="Japan",
            gender="Female",
            featured=False
        )

        laureate_six = Laureate(
            full_name="Test Laureate Six",
            laureate_type="Person",
            birth_date=date(1994, 1, 1),
            birth_country="United States",
            birth_state="Delaware",
            gender="Male",
            featured=False
        )

        # Extra laureates for decade analytics

        laureate_seven = Laureate(
            full_name="Test Laureate Seven",
            laureate_type="Person",
            featured=False
        )

        laureate_eight = Laureate(
            full_name="Test Laureate Eight",
            laureate_type="Person",
            featured=False
        )

        laureate_nine = Laureate(
            full_name="Test Laureate Nine",
            laureate_type="Person",
            featured=False
        )

        # =========================================================
        # 4. LAUREATE-PRIZE AWARDS
        # =========================================================

        chemistry_award_one = LaureatePrize(
            laureate=laureate_one,
            prize=chemistry_prize,
            prize_share="1/2"
        )

        chemistry_award_two = LaureatePrize(
            laureate=laureate_two,
            prize=chemistry_prize,
            prize_share="1/2"
        )

        medicine_award = LaureatePrize(
            laureate=laureate_three,
            prize=medicine_prize,
            prize_share="1/1"
        )

        medicine_award_two = LaureatePrize(
            laureate=laureate_four,
            prize=medicine_prize,
            prize_share="1/3"
        )

        medicine_award_three = LaureatePrize(
            laureate=laureate_five,
            prize=medicine_prize,
            prize_share="1/3"
        )

        medicine_award_four = LaureatePrize(
            laureate=laureate_six,
            prize=medicine_prize,
            prize_share="1/3"
        )

        # Awards from different decades

        award_1984 = LaureatePrize(
            laureate=laureate_seven,
            prize=prize_1984,
            prize_share="1/1"
        )

        award_1995 = LaureatePrize(
            laureate=laureate_eight,
            prize=prize_1995,
            prize_share="1/1"
        )

        award_2006 = LaureatePrize(
            laureate=laureate_nine,
            prize=prize_2006,
            prize_share="1/1"
        )

        # =========================================================
        # 5. INSTITUTIONS
        # =========================================================

        institution_one = Institution(
            name="Test University A",
            city="Boston",
            state="Massachusetts",
            country="United States"
        )

        institution_two = Institution(
            name="Test University B",
            city="New York",
            state="New York",
            country="United States"
        )

        institution_three = Institution(
            name="Test University C",
            city="London",
            state=None,
            country="United Kingdom"
        )

        # =========================================================
        # 6. AWARD AFFILIATIONS
        # =========================================================

        affiliation_one = AwardAffiliation(
            laureate_prize=medicine_award,
            institution=institution_one
        )

        affiliation_two = AwardAffiliation(
            laureate_prize=medicine_award_two,
            institution=institution_one
        )

        affiliation_three = AwardAffiliation(
            laureate_prize=medicine_award_three,
            institution=institution_two
        )

        affiliation_four = AwardAffiliation(
            laureate_prize=medicine_award_four,
            institution=institution_three
        )

        # =========================================================
        # 7. ADD TEMPORARY TEST DATA
        # =========================================================

        db.add_all([
            chemistry,
            medicine,

            chemistry_prize,
            medicine_prize,
            prize_1984,
            prize_1995,
            prize_2006,

            laureate_one,
            laureate_two,
            laureate_three,
            laureate_four,
            laureate_five,
            laureate_six,
            laureate_seven,
            laureate_eight,
            laureate_nine,

            chemistry_award_one,
            chemistry_award_two,

            medicine_award,
            medicine_award_two,
            medicine_award_three,
            medicine_award_four,

            award_1984,
            award_1995,
            award_2006,

            institution_one,
            institution_two,
            institution_three,

            affiliation_one,
            affiliation_two,
            affiliation_three,
            affiliation_four,
        ])

        db.flush()

        # =========================================================
        # STEP 1 - CORE COUNTS
        # =========================================================

        total_laureates = count_total_laureates(db)
        total_prizes = count_total_prizes(db)
        category_counts = get_laureate_counts_by_category(db)

        print("Total laureates:", total_laureates)
        print("Total prizes:", total_prizes)

        print("\nLaureates by category:")

        for category_name, count in category_counts:
            print(category_name, count)

        assert total_laureates == 9
        assert total_prizes == 5

        category_dict = dict(category_counts)

        assert category_dict["Chemistry"] == 5
        assert category_dict["Medicine"] == 4

        print("\nAnalytics repository Step 1 test passed.")

        # =========================================================
        # STEP 2 - COUNTRY + CATEGORY
        # =========================================================

        medicine_country_counts = (
            get_laureate_counts_by_country_and_category(
                db,
                "Medicine"
            )
        )

        print("\nMedicine laureates by birth country:")

        for country, count in medicine_country_counts:
            print(country, count)

        medicine_country_dict = dict(medicine_country_counts)

        assert medicine_country_dict["United States"] == 3
        assert medicine_country_dict["Japan"] == 1

        assert medicine_country_counts[0][0] == "United States"
        assert medicine_country_counts[0][1] == 3

        print("\nAnalytics repository Step 2 test passed.")

        # =========================================================
        # STEP 3 - U.S. BIRTH STATE + CATEGORY
        # =========================================================

        medicine_state_counts = (
            get_us_birth_state_counts_by_category(
                db,
                "Medicine"
            )
        )

        print("\nU.S. Medicine laureates by birth state:")

        for state, count in medicine_state_counts:
            print(state, count)

        medicine_state_dict = dict(medicine_state_counts)

        assert medicine_state_dict["California"] == 1
        assert medicine_state_dict["New York"] == 1
        assert medicine_state_dict["Delaware"] == 1

        print("\nAnalytics repository Step 3 test passed.")

        # =========================================================
        # STEP 4 - INSTITUTION + CATEGORY
        # =========================================================

        us_medicine_institutions = (
            get_institution_counts_by_category(
                db,
                "Medicine",
                "United States"
            )
        )

        print("\nU.S. Medicine laureates by institution:")

        for institution_name, count in us_medicine_institutions:
            print(institution_name, count)

        institution_dict = dict(us_medicine_institutions)

        assert institution_dict["Test University A"] == 2
        assert institution_dict["Test University B"] == 1

        assert "Test University C" not in institution_dict

        assert us_medicine_institutions[0][0] == "Test University A"
        assert us_medicine_institutions[0][1] == 2

        print("\nAnalytics repository Step 4 test passed.")

        # =========================================================
        # STEP 5 - GENDER + CATEGORY
        # =========================================================

        medicine_gender_counts = get_gender_counts_by_category(
            db,
            "Medicine"
        )

        print("\nMedicine laureates by gender:")

        for gender, count in medicine_gender_counts:
            print(gender, count)

        gender_dict = dict(medicine_gender_counts)

        assert gender_dict["Female"] == 2
        assert gender_dict["Male"] == 2

        print("\nAnalytics repository Step 5 test passed.")

        # =========================================================
        # STEP 6 - LAUREATES BY DECADE
        # =========================================================

        decade_counts = get_laureate_counts_by_decade(db)

        print("\nLaureates by decade:")

        for decade, count in decade_counts:
            print(decade, count)

        decade_dict = dict(decade_counts)

        assert decade_dict[1980] == 1
        assert decade_dict[1990] == 1
        assert decade_dict[2000] == 1
        assert decade_dict[2020] == 6

        print("\nAnalytics repository Step 6 test passed.")

        # =========================================================
        # STEP 7 - AVERAGE AGE AT AWARD
        # =========================================================

        average_age = get_average_age_at_award_by_category(
            db,
            "Medicine"
        )

        print(
            "\nAverage age at award for Medicine:",
            average_age
        )

        assert average_age is not None
        assert round(average_age, 1) == 45.0

        print("\nAnalytics repository Step 7 test passed.")

    finally:
        # Remove all temporary test data.
        db.rollback()
        db.close()


if __name__ == "__main__":
    test_analytics_repository()