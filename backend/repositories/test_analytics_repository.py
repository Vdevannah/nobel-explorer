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
    count_distinct_birth_countries,
    get_laureate_counts_by_category,
    get_laureate_counts_by_country_and_category,
    get_us_birth_state_counts_by_category,
    get_institution_counts_by_category,
    get_gender_counts_by_category,
    get_laureate_counts_by_decade,
    get_average_age_at_award_by_category,
    get_overall_gender_counts,
    get_top_birth_countries,
    get_prize_counts_by_decade,
    get_age_distribution,
    get_gender_counts_by_era,
)


def test_analytics_repository():
    db = SessionLocal()

    try:
        baseline_laureates = count_total_laureates(db)
        baseline_prizes = count_total_prizes(db)
        baseline_decade_counts = dict(
            get_laureate_counts_by_decade(db)
        )

        # =========================================================
        # 1. CATEGORIES
        # =========================================================

        chemistry = Category(
            name="Test Analytics Chemistry",
            description="Temporary test category"
        )

        medicine = Category(
            name="Test Analytics Medicine",
            description="Temporary test category"
        )

        # =========================================================
        # 2. PRIZES
        # =========================================================

        chemistry_prize = Prize(
            year=2024,
            category=chemistry
        )

        medicine_prize = Prize(
            year=2024,
            category=medicine
        )

        # Extra prizes for decade analytics

        prize_1984 = Prize(
            year=1984,
            category=chemistry
        )

        prize_1995 = Prize(
            year=1995,
            category=chemistry
        )

        prize_2006 = Prize(
            year=2006,
            category=chemistry
        )

        # =========================================================
        # 3. LAUREATES
        # =========================================================

        laureate_one = Laureate(
            nobel_laureate_id="TEST-003",
            full_name="Test Laureate One",
            laureate_type="Person",
            birth_country="USA",
            birth_state="California",
            gender="Female",
            featured=False
        )

        laureate_two = Laureate(
            nobel_laureate_id="TEST-004",
            full_name="Test Laureate Two",
            laureate_type="Person",
            birth_country="Germany",
            gender="Male",
            featured=False
        )

        # Medicine laureates have birth dates for Step 7 testing

        laureate_three = Laureate(
            nobel_laureate_id="TEST-005",
            full_name="Test Laureate Three",
            laureate_type="Person",
            birth_date=date(1964, 1, 1),
            birth_country="USA",
            birth_state="New York",
            gender="Female",
            featured=False
        )

        laureate_four = Laureate(
            nobel_laureate_id="TEST-006",
            full_name="Test Laureate Four",
            laureate_type="Person",
            birth_date=date(1974, 1, 1),
            birth_country="USA",
            birth_state="California",
            gender="Male",
            featured=False
        )

        laureate_five = Laureate(
            nobel_laureate_id="TEST-007",
            full_name="Test Laureate Five",
            laureate_type="Person",
            birth_date=date(1984, 1, 1),
            birth_country="Japan",
            gender="Female",
            featured=False
        )

        laureate_six = Laureate(
            nobel_laureate_id="TEST-008",
            full_name="Test Laureate Six",
            laureate_type="Person",
            birth_date=date(1994, 1, 1),
            birth_country="USA",
            birth_state="Delaware",
            gender="Male",
            featured=False
        )

        # Extra laureates for decade analytics

        laureate_seven = Laureate(
            nobel_laureate_id="TEST-009",
            full_name="Test Laureate Seven",
            laureate_type="Person",
            featured=False
        )

        laureate_eight = Laureate(
            nobel_laureate_id="TEST-010",
            full_name="Test Laureate Eight",
            laureate_type="Person",
            featured=False
        )

        laureate_nine = Laureate(
            nobel_laureate_id="TEST-011",
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
            country="USA"
        )

        institution_two = Institution(
            name="Test University B",
            city="New York",
            state="New York",
            country="USA"
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

        assert total_laureates == baseline_laureates + 9
        assert total_prizes == baseline_prizes + 5

        category_dict = dict(category_counts)

        assert category_dict["Test Analytics Chemistry"] == 5
        assert category_dict["Test Analytics Medicine"] == 4

        print("\nAnalytics repository Step 1 test passed.")

        # =========================================================
        # STEP 2 - COUNTRY + CATEGORY
        # =========================================================

        medicine_country_counts = (
            get_laureate_counts_by_country_and_category(
                db,
                "Test Analytics Medicine"
            )
        )

        print("\nMedicine laureates by birth country:")

        for country, count in medicine_country_counts:
            print(country, count)

        medicine_country_dict = dict(medicine_country_counts)

        assert medicine_country_dict["USA"] == 3
        assert medicine_country_dict["Japan"] == 1

        assert medicine_country_counts[0][0] == "USA"
        assert medicine_country_counts[0][1] == 3

        print("\nAnalytics repository Step 2 test passed.")

        # =========================================================
        # STEP 3 - U.S. BIRTH STATE + CATEGORY
        # =========================================================

        medicine_state_counts = (
            get_us_birth_state_counts_by_category(
                db,
                "Test Analytics Medicine"
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
                "Test Analytics Medicine",
                "USA"
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
            "Test Analytics Medicine"
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

        assert decade_dict[1980] == baseline_decade_counts.get(1980, 0) + 1
        assert decade_dict[1990] == baseline_decade_counts.get(1990, 0) + 1
        assert decade_dict[2000] == baseline_decade_counts.get(2000, 0) + 1
        assert decade_dict[2020] == baseline_decade_counts.get(2020, 0) + 6

        print("\nAnalytics repository Step 6 test passed.")

        # =========================================================
        # STEP 7 - AVERAGE AGE AT AWARD
        # =========================================================

        average_age = get_average_age_at_award_by_category(
            db,
            "Test Analytics Medicine"
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


def test_analytics_repository_dashboard_metrics():
    db = SessionLocal()

    try:
        baseline_countries = count_distinct_birth_countries(db)
        baseline_gender = dict(get_overall_gender_counts(db))
        baseline_decades = dict(get_prize_counts_by_decade(db))
        baseline_ages = dict(get_age_distribution(db))
        baseline_top_countries = dict(
            get_top_birth_countries(db, limit=1000)
        )
        baseline_laureates_1930 = count_total_laureates(
            db, start_year=1930, end_year=1930
        )
        baseline_prizes_1930 = count_total_prizes(
            db, start_year=1930, end_year=1930
        )

        extra_category = Category(
            name="Test Analytics Extra",
            description="Temporary test category"
        )

        prize_a = Prize(year=1930, category=extra_category)
        prize_b = Prize(year=1930, category=extra_category)

        laureate_a = Laureate(
            nobel_laureate_id="TEST-020",
            full_name="Test Laureate Ten",
            laureate_type="Person",
            birth_date=date(1900, 1, 1),
            birth_country="Testlandia",
            gender="female",
            featured=False
        )

        laureate_b = Laureate(
            nobel_laureate_id="TEST-021",
            full_name="Test Laureate Eleven",
            laureate_type="Person",
            birth_country="Testlandia",
            gender="male",
            featured=False
        )

        award_a = LaureatePrize(
            laureate=laureate_a,
            prize=prize_a,
            prize_share="1/1"
        )

        award_b = LaureatePrize(
            laureate=laureate_b,
            prize=prize_b,
            prize_share="1/1"
        )

        db.add_all([
            extra_category,
            prize_a,
            prize_b,
            laureate_a,
            laureate_b,
            award_a,
            award_b,
        ])
        db.flush()

        # Distinct birth countries increases by exactly one new country.

        assert count_distinct_birth_countries(db) == baseline_countries + 1

        # Overall gender counts include the new laureates.

        gender_counts = dict(get_overall_gender_counts(db))
        assert gender_counts["female"] == baseline_gender.get("female", 0) + 1
        assert gender_counts["male"] == baseline_gender.get("male", 0) + 1

        # Prize counts by decade include both new 1930s prizes.

        decade_counts = dict(get_prize_counts_by_decade(db))
        assert decade_counts[1930] == baseline_decades.get(1930, 0) + 2

        # Age at award (1930 - 1900 = 30) lands in the 30-39 bucket.

        age_counts = dict(get_age_distribution(db))
        assert age_counts["30-39"] == baseline_ages.get("30-39", 0) + 1

        # Testlandia now has two laureates and appears in top countries.

        top_countries = dict(get_top_birth_countries(db, limit=1000))
        assert top_countries["Testlandia"] == (
            baseline_top_countries.get("Testlandia", 0) + 2
        )

        # 1901-1950 era gender split reflects the new laureates.

        era_counts = get_gender_counts_by_era(db)
        era_1901_1950 = {
            gender: count
            for era, gender, count in era_counts
            if era == "1901-1950"
        }
        assert era_1901_1950["female"] >= 1
        assert era_1901_1950["male"] >= 1

        # Phase 10G: the same category/start_year/end_year filters that
        # narrow the other dashboard queries also narrow the four summary
        # totals -- category alone, year alone, and combined.

        assert count_total_laureates(db, category="Test Analytics Extra") == 2
        assert count_total_prizes(db, category="Test Analytics Extra") == 2
        assert count_distinct_birth_countries(
            db, category="Test Analytics Extra"
        ) == 1
        gender_by_category = dict(
            get_overall_gender_counts(db, category="Test Analytics Extra")
        )
        assert gender_by_category == {"female": 1, "male": 1}

        assert count_total_laureates(
            db, start_year=1930, end_year=1930
        ) == baseline_laureates_1930 + 2
        assert count_total_prizes(
            db, start_year=1930, end_year=1930
        ) == baseline_prizes_1930 + 2

        assert count_total_laureates(
            db,
            category="Test Analytics Extra",
            start_year=1930,
            end_year=1930
        ) == 2
        assert count_total_laureates(
            db,
            category="Test Analytics Extra",
            start_year=1931,
            end_year=1940
        ) == 0

        print("\nAnalytics repository dashboard metrics test passed.")

    finally:
        db.rollback()
        db.close()


def test_analytics_repository_hardened_demographic_and_age_methodology():
    """Phase 10C/10F: age-at-award OBSERVATIONS (one per award with a
    known birth date, not one per distinct laureate) for age-distribution
    and average-age; organizations and unknown-gender records must never
    enter gender/age denominators; a repeat winner may legitimately
    contribute to two different eras and two different age buckets.
    """
    db = SessionLocal()

    try:
        baseline_ages = dict(get_age_distribution(db))

        category = Category(
            name="Test Hardened Methodology",
            description="Temporary test category"
        )

        # Two prizes, far enough apart that the same person's age-at-award
        # falls in two different buckets (<30 vs 40-49), and far enough
        # apart in year that they land in two different eras.
        early_prize = Prize(year=1935, category=category)  # -> era 1901-1950
        late_prize = Prize(year=1995, category=category)   # -> era 1991-2010

        # Born 1910: age at 1935 award = 25 (<30 bucket);
        #            age at 1995 award = 85 (80+ bucket).
        repeat_winner = Laureate(
            nobel_laureate_id="TEST-030",
            full_name="Test Repeat Winner",
            laureate_type="Person",
            birth_date=date(1910, 1, 1),
            birth_country="Sweden",
            gender="female",
            featured=False
        )

        # An organization sharing the same category and a real prize --
        # must never appear in age or gender counts (no birth date, no
        # gender to speak of, and explicitly typed "Organization").
        organization_laureate = Laureate(
            nobel_laureate_id="TEST-031",
            full_name="Test Analytics Organization",
            laureate_type="Organization",
            birth_country=None,
            gender=None,
            featured=False
        )

        # A person with no recorded gender -- must be excluded from the
        # gender-by-era denominator, never silently treated as a gender.
        unknown_gender_laureate = Laureate(
            nobel_laureate_id="TEST-032",
            full_name="Test Unknown Gender",
            laureate_type="Person",
            birth_date=date(1930, 1, 1),
            birth_country="Sweden",
            gender=None,
            featured=False
        )

        early_award_repeat = LaureatePrize(
            laureate=repeat_winner,
            prize=early_prize,
            prize_share="1/1"
        )
        late_award_repeat = LaureatePrize(
            laureate=repeat_winner,
            prize=late_prize,
            prize_share="1/1"
        )
        org_award = LaureatePrize(
            laureate=organization_laureate,
            prize=early_prize,
            prize_share="1/1"
        )
        unknown_gender_award = LaureatePrize(
            laureate=unknown_gender_laureate,
            prize=early_prize,
            prize_share="1/1"
        )

        db.add_all([
            category,
            early_prize,
            late_prize,
            repeat_winner,
            organization_laureate,
            unknown_gender_laureate,
            early_award_repeat,
            late_award_repeat,
            org_award,
            unknown_gender_award,
        ])
        db.flush()

        # ---- Age distribution: two OBSERVATIONS for the repeat winner
        # ---- alone (not one collapsed laureate), the organization
        # ---- contributes zero (no birth date), and the unknown-gender
        # ---- laureate (age 5 at the 1935 award -- gender is irrelevant
        # ---- to this endpoint) also lands in "<30" alongside her.

        age_counts = dict(get_age_distribution(db))
        assert age_counts["<30"] == baseline_ages.get("<30", 0) + 2
        assert age_counts["80+"] == baseline_ages.get("80+", 0) + 1

        # ---- Average age at award: averages every person observation in
        # ---- this category (25 and 85 for the repeat winner, 5 for the
        # ---- unknown-gender laureate -- gender is irrelevant here, only
        # ---- laureate_type and birth_date matter) rather than collapsing
        # ---- the repeat winner to a single age. The organization's
        # ---- award contributes nothing (no birth date).

        average_age = get_average_age_at_award_by_category(
            db,
            "Test Hardened Methodology"
        )
        assert average_age is not None
        assert round(average_age, 1) == round((25 + 85 + 5) / 3, 1)

        # ---- Gender by era: the same repeat winner is counted once in
        # ---- EACH of the two eras her awards fall into (distinct per
        # ---- era, not collapsed across eras); the organization and the
        # ---- unknown-gender laureate never appear in either era's
        # ---- gender breakdown at all.

        era_counts = get_gender_counts_by_era(db)
        era_lookup = {
            (era, gender): count for era, gender, count in era_counts
        }
        assert era_lookup.get(("1901-1950", "female"), 0) >= 1
        assert era_lookup.get(("1991-2010", "female"), 0) >= 1

        genders_seen_in_1901_1950 = {
            gender for era, gender, _ in era_counts if era == "1901-1950"
        }
        assert None not in genders_seen_in_1901_1950

        # ---- Gender by category: the organization and the
        # ---- unknown-gender laureate are excluded from the category's
        # ---- gender denominator entirely.

        category_gender_counts = dict(
            get_gender_counts_by_category(db, "Test Hardened Methodology")
        )
        assert category_gender_counts.get("female") == 1
        assert sum(category_gender_counts.values()) == 1

        # ---- Category counts: the organization IS still counted in
        # ---- plain laureate-by-category totals (that metric is not
        # ---- gender- or age-restricted) -- 3 distinct laureates total.

        category_counts = dict(get_laureate_counts_by_category(db))
        assert category_counts["Test Hardened Methodology"] == 3

        print(
            "\nAnalytics repository hardened methodology test passed."
        )

    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    test_analytics_repository()
    test_analytics_repository_dashboard_metrics()
    test_analytics_repository_hardened_demographic_and_age_methodology()
