import pytest

from backend.database.connection import SessionLocal
from backend.models.category import Category
from backend.models.laureate import Laureate
from backend.models.laureate_prize import LaureatePrize
from backend.models.prize import Prize
from backend.schemas.connection import ConnectionCreate
from backend.schemas.contribution import ContributionCreate
from backend.schemas.explanation import ExplanationCreate
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
        laureate_id=laureate_id,
        laureate_prize_id=laureate_prize_id,
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
