from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database.connection import SessionLocal
from backend.models.award_affiliation import AwardAffiliation
from backend.models.category import Category
from backend.models.institution import Institution
from backend.models.laureate import Laureate
from backend.models.laureate_prize import LaureatePrize
from backend.models.prize import Prize
from backend.repositories import award_affiliation_repository
from backend.repositories import category_repository
from backend.repositories import institution_repository
from backend.repositories import laureate_prize_repository
from backend.repositories import laureate_repository
from backend.repositories import prize_repository
from ETL.transform import transform_affiliations
from ETL.transform import transform_laureate
from ETL.transform import transform_prizes


def get_or_create_category(db: Session, category_name: str) -> Category:
    category = category_repository.get_by_name(db, category_name)

    if category is not None:
        return category

    return category_repository.create(
        db,
        Category(name=category_name)
    )


def get_or_create_prize(
    db: Session,
    year: int,
    category: Category
) -> Prize:
    prize = prize_repository.get_by_year_and_category(
        db,
        year,
        category.category_id
    )

    if prize is not None:
        return prize

    return prize_repository.create(
        db,
        Prize(
            year=year,
            category=category
        )
    )


def get_or_create_laureate(
    db: Session,
    laureate_data: dict
) -> Laureate:
    laureate = laureate_repository.get_by_nobel_id(
        db,
        laureate_data["nobel_laureate_id"]
    )

    if laureate is not None:
        return laureate

    return laureate_repository.create(
        db,
        Laureate(
            nobel_laureate_id=laureate_data["nobel_laureate_id"],
            full_name=laureate_data["full_name"],
            laureate_type=laureate_data["laureate_type"],
            birth_date=laureate_data.get("birth_date"),
            birth_city=laureate_data.get("birth_city"),
            birth_state=laureate_data.get("birth_state"),
            birth_country=laureate_data.get("birth_country"),
            gender=laureate_data.get("gender"),
            image_url=None,
            featured=False
        )
    )


def get_or_create_laureate_prize(
    db: Session,
    laureate: Laureate,
    prize: Prize,
    prize_share: str | None,
    motivation: str | None
) -> LaureatePrize:
    laureate_prize = (
        laureate_prize_repository.get_by_laureate_and_prize(
            db,
            laureate.laureate_id,
            prize.prize_id
        )
    )

    if laureate_prize is not None:
        if laureate_prize.motivation != motivation:
            laureate_prize.motivation = motivation
            db.flush()

        return laureate_prize

    return laureate_prize_repository.create(
        db,
        LaureatePrize(
            laureate=laureate,
            prize=prize,
            prize_share=prize_share,
            motivation=motivation
        )
    )


def get_or_create_institution(
    db: Session,
    affiliation_data: dict
) -> Institution | None:
    name = affiliation_data.get("name")

    if not name:
        return None

    institution = institution_repository.get_by_name(db, name)

    if institution is not None:
        return institution

    return institution_repository.create(
        db,
        Institution(
            name=name,
            city=affiliation_data.get("city"),
            state=affiliation_data.get("state"),
            country=affiliation_data.get("country")
        )
    )


def get_or_create_award_affiliation(
    db: Session,
    laureate_prize: LaureatePrize,
    institution: Institution | None
) -> AwardAffiliation | None:
    if institution is None:
        return None

    award_affiliation = (
        award_affiliation_repository
        .get_by_laureate_prize_and_institution(
            db,
            laureate_prize.laureate_prize_id,
            institution.institution_id
        )
    )

    if award_affiliation is not None:
        return award_affiliation

    return award_affiliation_repository.create(
        db,
        AwardAffiliation(
            laureate_prize=laureate_prize,
            institution=institution
        )
    )


def load_laureate_record(
    db: Session,
    laureate_data: dict,
    raw_prizes: list[dict]
) -> Laureate:
    laureate = get_or_create_laureate(db, laureate_data)

    for raw_prize in raw_prizes:
        prize_data_list = transform_prizes({
            "nobelPrizes": [raw_prize]
        })

        if not prize_data_list:
            continue

        prize_data = prize_data_list[0]
        category = get_or_create_category(db, prize_data["category"])
        prize = get_or_create_prize(
            db,
            prize_data["year"],
            category
        )
        laureate_prize = get_or_create_laureate_prize(
            db,
            laureate,
            prize,
            prize_data.get("prize_share"),
            prize_data.get("motivation")
        )

        for affiliation_data in transform_affiliations(raw_prize):
            institution = get_or_create_institution(db, affiliation_data)
            get_or_create_award_affiliation(
                db,
                laureate_prize,
                institution
            )

    return laureate


if __name__ == "__main__":
    raw_spence = {
        "id": "745",
        "fullName": {
            "en": "A. Michael Spence"
        },
        "gender": "male",
        "birth": {
            "date": "1943-11-07",
            "place": {
                "city": {
                    "en": "Montclair, NJ"
                },
                "country": {
                    "en": "USA"
                }
            }
        },
        "nobelPrizes": [
            {
                "awardYear": "2001",
                "category": {
                    "en": "Economic Sciences"
                },
                "motivation": {
                    "en": "for analyses of markets with asymmetric information"
                },
                "portion": "1/3",
                "affiliations": [
                    {
                        "name": {
                            "en": "Stanford University"
                        },
                        "city": {
                            "en": "Stanford, CA"
                        },
                        "country": {
                            "en": "USA"
                        }
                    }
                ]
            }
        ]
    }

    db = SessionLocal()

    try:
        laureate_data = transform_laureate(raw_spence)

        first_laureate = load_laureate_record(
            db,
            laureate_data,
            raw_spence.get("nobelPrizes", [])
        )

        prize_data = transform_prizes(raw_spence)[0]
        first_category = category_repository.get_by_name(
            db,
            prize_data["category"]
        )
        first_prize = prize_repository.get_by_year_and_category(
            db,
            prize_data["year"],
            first_category.category_id
        )
        first_laureate_prize = (
            laureate_prize_repository.get_by_laureate_and_prize(
                db,
                first_laureate.laureate_id,
                first_prize.prize_id
            )
        )
        first_institution = institution_repository.get_by_name(
            db,
            "Stanford University"
        )
        first_award_affiliation = (
            award_affiliation_repository
            .get_by_laureate_prize_and_institution(
                db,
                first_laureate_prize.laureate_prize_id,
                first_institution.institution_id
            )
        )

        first_ids = {
            "laureate": first_laureate.laureate_id,
            "category": first_category.category_id,
            "prize": first_prize.prize_id,
            "laureate_prize": first_laureate_prize.laureate_prize_id,
            "institution": first_institution.institution_id,
            "award_affiliation": (
                first_award_affiliation.award_affiliation_id
            )
        }

        second_laureate = load_laureate_record(
            db,
            laureate_data,
            raw_spence.get("nobelPrizes", [])
        )

        second_category = category_repository.get_by_name(
            db,
            prize_data["category"]
        )
        second_prize = prize_repository.get_by_year_and_category(
            db,
            prize_data["year"],
            second_category.category_id
        )
        second_laureate_prize = (
            laureate_prize_repository.get_by_laureate_and_prize(
                db,
                second_laureate.laureate_id,
                second_prize.prize_id
            )
        )
        second_institution = institution_repository.get_by_name(
            db,
            "Stanford University"
        )
        second_award_affiliation = (
            award_affiliation_repository
            .get_by_laureate_prize_and_institution(
                db,
                second_laureate_prize.laureate_prize_id,
                second_institution.institution_id
            )
        )

        second_ids = {
            "laureate": second_laureate.laureate_id,
            "category": second_category.category_id,
            "prize": second_prize.prize_id,
            "laureate_prize": second_laureate_prize.laureate_prize_id,
            "institution": second_institution.institution_id,
            "award_affiliation": (
                second_award_affiliation.award_affiliation_id
            )
        }

        filtered_counts = {
            "laureate": db.scalar(
                select(func.count())
                .select_from(Laureate)
                .where(Laureate.nobel_laureate_id == "745")
            ),
            "category": db.scalar(
                select(func.count())
                .select_from(Category)
                .where(Category.name == "Economic Sciences")
            ),
            "prize": db.scalar(
                select(func.count())
                .select_from(Prize)
                .where(
                    Prize.year == 2001,
                    Prize.category_id == first_category.category_id
                )
            ),
            "laureate_prize": db.scalar(
                select(func.count())
                .select_from(LaureatePrize)
                .where(
                    LaureatePrize.laureate_id
                    == first_laureate.laureate_id,
                    LaureatePrize.prize_id == first_prize.prize_id
                )
            ),
            "institution": db.scalar(
                select(func.count())
                .select_from(Institution)
                .where(Institution.name == "Stanford University")
            ),
            "award_affiliation": db.scalar(
                select(func.count())
                .select_from(AwardAffiliation)
                .where(
                    AwardAffiliation.laureate_prize_id
                    == first_laureate_prize.laureate_prize_id,
                    AwardAffiliation.institution_id
                    == first_institution.institution_id
                )
            )
        }

        assert first_ids == second_ids
        assert all(count == 1 for count in filtered_counts.values())

        print("First load IDs:", first_ids)
        print("Second load IDs:", second_ids)
        print("Filtered row counts:", filtered_counts)
        print("Idempotence verified: all records were reused.")
    finally:
        db.rollback()
        db.close()
