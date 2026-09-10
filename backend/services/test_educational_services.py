import pytest

from backend.database.connection import SessionLocal
from backend.models.category import Category
from backend.models.laureate import Laureate
from backend.models.laureate_prize import LaureatePrize
from backend.models.prize import Prize
from backend.schemas.connection import ConnectionCreate
from backend.schemas.contribution import ContributionCreate
from backend.schemas.explanation import ExplanationCreate
from backend.repositories import contribution_repository
from backend.services import (
    connection_service,
    contribution_service,
    explanation_service,
)
from backend.services.exceptions import ResourceNotFoundError, ServiceValidationError


@pytest.fixture
def educational_db():
    db = SessionLocal()
    try:
        category = Category(name="Educational Service Test Physics")
        prize = Prize(year=1921, category=category)
        related_prize = Prize(year=2017, category=category)
        laureate = Laureate(
            nobel_laureate_id="TEST-EDU-001",
            full_name="Educational Test Laureate",
            laureate_type="Person",
            featured=False,
        )
        other_laureate = Laureate(
            nobel_laureate_id="TEST-EDU-002",
            full_name="Other Educational Laureate",
            laureate_type="Person",
            featured=False,
        )
        laureate_prize = LaureatePrize(laureate=laureate, prize=prize)
        db.add_all([category, related_prize, other_laureate])
        db.flush()
        yield db, laureate, other_laureate, laureate_prize, related_prize
    finally:
        db.rollback()
        db.close()


def contribution_data(
    laureate_id: int,
    contribution_type: str,
    laureate_prize_id: int | None,
    title: str,
) -> ContributionCreate:
    return ContributionCreate(
        credited_laureates=[{"laureate_id": laureate_id, "laureate_prize_id": laureate_prize_id}],
        contribution_type=contribution_type,
        title=title,
        summary="Test summary",
    )


def test_contribution_relationship_validation(educational_db):
    db, laureate, other_laureate, laureate_prize, _ = educational_db

    nobel_linked = contribution_service.create_contribution(
        db,
        contribution_data(
            laureate.laureate_id,
            "NOBEL_LINKED",
            laureate_prize.laureate_prize_id,
            "Nobel-linked work",
        ),
    )
    assert nobel_linked.laureate_prize_id == laureate_prize.laureate_prize_id

    beyond_nobel = contribution_service.create_contribution(
        db,
        contribution_data(
            laureate.laureate_id,
            "BEYOND_NOBEL",
            None,
            "Beyond-Nobel work",
        ),
    )
    assert beyond_nobel.laureate_prize_id is None

    with pytest.raises(ServiceValidationError):
        contribution_service.create_contribution(
            db,
            contribution_data(
                laureate.laureate_id,
                "NOBEL_LINKED",
                None,
                "Missing award",
            ),
        )

    with pytest.raises(ServiceValidationError):
        contribution_service.create_contribution(
            db,
            contribution_data(
                other_laureate.laureate_id,
                "NOBEL_LINKED",
                laureate_prize.laureate_prize_id,
                "Mismatched award",
            ),
        )

    with pytest.raises(ServiceValidationError):
        contribution_service.create_contribution(
            db,
            contribution_data(
                laureate.laureate_id,
                "BEYOND_NOBEL",
                laureate_prize.laureate_prize_id,
                "Invalid beyond-Nobel award",
            ),
        )


def test_shared_contribution_with_multiple_laureates(educational_db):
    # Mirrors the Karikó/Weissman shared-Nobel-Prize architecture case with
    # synthetic laureates (no real Karikó/Weissman educational content is
    # created here, per the "do not seed yet" instruction) -- two laureates
    # explicitly credited on one contribution, each with their own award link.
    db, laureate, other_laureate, laureate_prize, related_prize = educational_db
    other_prize = LaureatePrize(laureate=other_laureate, prize=related_prize)
    db.add(other_prize)
    db.flush()

    shared = contribution_service.create_contribution(
        db,
        ContributionCreate(
            credited_laureates=[
                {"laureate_id": laureate.laureate_id, "laureate_prize_id": laureate_prize.laureate_prize_id},
                {"laureate_id": other_laureate.laureate_id, "laureate_prize_id": other_prize.laureate_prize_id},
            ],
            contribution_type="NOBEL_LINKED",
            title="Shared discovery",
            summary="Two laureates explicitly credited for one discovery.",
        ),
    )

    # Shared contribution with two laureates, each keeping their own award.
    credits = {credit.laureate_id: credit for credit in shared.credited_laureates}
    assert set(credits) == {laureate.laureate_id, other_laureate.laureate_id}
    assert credits[laureate.laureate_id].laureate_prize_id == laureate_prize.laureate_prize_id
    assert credits[other_laureate.laureate_id].laureate_prize_id == other_prize.laureate_prize_id

    # Discoverable from both laureates.
    from_first = contribution_repository.get_by_laureate(db, laureate.laureate_id)
    from_second = contribution_repository.get_by_laureate(db, other_laureate.laureate_id)
    assert shared.contribution_id in [item.contribution_id for item in from_first]
    assert shared.contribution_id in [item.contribution_id for item in from_second]

    # Catalog returns it exactly once, exposing both credited laureates.
    catalog = contribution_service.list_catalog(db)
    matches = [item for item in catalog if item.contribution_id == shared.contribution_id]
    assert len(matches) == 1
    assert {credit.laureate_id for credit in matches[0].credited_laureates} == {
        laureate.laureate_id, other_laureate.laureate_id,
    }

    # Each award must belong to its own credited laureate -- swapping them is rejected.
    with pytest.raises(ServiceValidationError):
        contribution_service.create_contribution(
            db,
            ContributionCreate(
                credited_laureates=[
                    {"laureate_id": laureate.laureate_id, "laureate_prize_id": other_prize.laureate_prize_id},
                    {"laureate_id": other_laureate.laureate_id, "laureate_prize_id": laureate_prize.laureate_prize_id},
                ],
                contribution_type="NOBEL_LINKED",
                title="Swapped awards",
            ),
        )

    # Association is explicit only -- an uninvolved laureate is never auto-credited.
    third_party = Laureate(
        nobel_laureate_id="TEST-EDU-003",
        full_name="Uncredited Laureate",
        laureate_type="Person",
        featured=False,
    )
    db.add(third_party)
    db.flush()
    assert third_party.laureate_id not in credits
    assert shared.contribution_id not in [
        item.contribution_id
        for item in contribution_repository.get_by_laureate(db, third_party.laureate_id)
    ]

    # (contribution_id, laureate_id) uniqueness is an explicit business rule.
    with pytest.raises(ServiceValidationError):
        contribution_service.create_contribution(
            db,
            ContributionCreate(
                credited_laureates=[
                    {"laureate_id": laureate.laureate_id},
                    {"laureate_id": laureate.laureate_id},
                ],
                contribution_type="BEYOND_NOBEL",
                title="Duplicate credit",
            ),
        )


def test_nested_content_and_scientific_legacy(educational_db):
    db, laureate, _, laureate_prize, related_prize = educational_db
    contribution = contribution_service.create_contribution(
        db,
        contribution_data(
            laureate.laureate_id,
            "NOBEL_LINKED",
            laureate_prize.laureate_prize_id,
            "Test contribution",
        ),
    )
    explanation_service.create_explanation(
        db,
        ExplanationCreate(
            contribution_id=contribution.contribution_id,
            level="Simple",
            explanation_text="A simple explanation",
        ),
    )
    connection_service.create_connection(
        db,
        ConnectionCreate(
            contribution_id=contribution.contribution_id,
            connection_type="SCIENTIFIC_LEGACY",
            related_prize_id=related_prize.prize_id,
            title="A later Nobel-recognized legacy",
        ),
    )

    detail = contribution_service.get_contribution(
        db, contribution.contribution_id
    )
    assert detail.explanations[0].level == "Simple"
    assert detail.connections[0].related_prize.prize_id == related_prize.prize_id
    assert detail.connections[0].related_prize.year == 2017
    assert detail.connections[0].related_prize.category == "Educational Service Test Physics"

    explanation = explanation_service.get_explanation_by_level(
        db, contribution.contribution_id, "Simple"
    )
    assert explanation.explanation_text == "A simple explanation"


def test_nonexistent_educational_resources():
    db = SessionLocal()
    try:
        with pytest.raises(ResourceNotFoundError):
            contribution_service.get_contribution(db, 999999999)
        with pytest.raises(ResourceNotFoundError):
            explanation_service.list_explanations(db, 999999999)
        with pytest.raises(ResourceNotFoundError):
            connection_service.list_connections(db, 999999999)
    finally:
        db.rollback()
        db.close()
