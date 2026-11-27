"""Shared fixtures for AI retrieval tests.

Unit tests run against an in-memory SQLite database built from the real
SQLAlchemy models and use ``HashingEmbedder`` (a lexical stand-in, NOT a
semantic model). Real-model and live-database tests are opt-in:

    AI_RUN_REAL_MODEL_TESTS=1  -> tests marked ``real_model``
    AI_RUN_LIVE_DB_TESTS=1     -> tests marked ``live_db``
"""

from __future__ import annotations

import os
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import backend.models  # noqa: F401  (registers all mappers)
from backend.database.connection import Base
from backend.ai.tests.fixture_data import EXPERT_TEXT
from backend.models import (
    AwardAffiliation,
    Category,
    Connection,
    Contribution,
    ContributionLaureate,
    Explanation,
    Institution,
    Laureate,
    LaureatePrize,
    Prize,
)



# Generous limits so ordinary API tests are not throttled by each other; the
# guard itself is tested in test_ai_guard.py with explicit limits.
UNLIMITED_GUARD = dict(per_ip_per_minute=100_000, per_ip_per_day=100_000, global_per_day=100_000,
                       max_concurrent=1_000, daily_spend_limit_usd=1e6, monthly_spend_limit_usd=1e6)


@pytest.fixture(autouse=True)
def _fresh_ai_guard(monkeypatch):
    from backend.ai import guard

    monkeypatch.setattr(guard, "_guard", guard.AIGuard(guard.GuardConfig(**UNLIMITED_GUARD)))


def pytest_configure(config):
    config.addinivalue_line("markers", "real_model: requires the real all-MiniLM-L6-v2 model")
    config.addinivalue_line("markers", "live_db: requires the live Nobel Explorer MySQL database")
    config.addinivalue_line("markers", "paid_llm: calls a real, paid LLM provider (never run by default)")


def pytest_collection_modifyitems(config, items):
    gates = {
        "real_model": ("AI_RUN_REAL_MODEL_TESTS", "set AI_RUN_REAL_MODEL_TESTS=1 to run real-model tests"),
        "live_db": ("AI_RUN_LIVE_DB_TESTS", "set AI_RUN_LIVE_DB_TESTS=1 to run live-database tests"),
        "paid_llm": ("AI_RUN_PAID_LLM_TESTS", "PAID: set AI_RUN_PAID_LLM_TESTS=1 only after explicit approval"),
    }
    for item in items:
        for marker, (env, reason) in gates.items():
            if marker in item.keywords and os.getenv(env) != "1":
                item.add_marker(pytest.mark.skip(reason=reason))


def _seed(db: Session) -> None:
    physics = Category(category_id=1, name="Physics")
    chemistry = Category(category_id=2, name="Chemistry")
    p1921 = Prize(prize_id=10, year=1921, category=physics)
    p2022 = Prize(prize_id=20, year=2022, category=chemistry)
    p2017 = Prize(prize_id=30, year=2017, category=physics)

    einstein = Laureate(
        laureate_id=249, nobel_laureate_id="26", full_name="Albert Einstein", laureate_type="Person",
        birth_date=date(1879, 3, 14), birth_city="Ulm", birth_country="Germany", gender="male",
    )
    bertozzi = Laureate(
        laureate_id=766, nobel_laureate_id="1015", full_name="Carolyn R. Bertozzi",
        laureate_type="Person", birth_country="USA", gender="female",
    )
    sharpless = Laureate(
        laureate_id=886, nobel_laureate_id="743", full_name="K. Barry Sharpless",
        laureate_type="Person", birth_city="Philadelphia", birth_state="Pennsylvania",
        birth_country="USA", gender="male",
    )
    red_cross = Laureate(
        laureate_id=648, nobel_laureate_id="482", full_name="International Committee of the Red Cross",
        laureate_type="Organization",
    )

    lp_einstein = LaureatePrize(
        laureate_prize_id=226, laureate=einstein, prize=p1921, prize_share="1",
        motivation="for his services to Theoretical Physics, and especially for his discovery of the law of the photoelectric effect",
    )
    lp_bertozzi = LaureatePrize(
        laureate_prize_id=748, laureate=bertozzi, prize=p2022, prize_share="1/3",
        motivation="for the development of click chemistry and bioorthogonal chemistry",
    )
    lp_sharpless = LaureatePrize(
        laureate_prize_id=870, laureate=sharpless, prize=p2022, prize_share="1/3",
        motivation="for the development of click chemistry and bioorthogonal chemistry",
    )
    institution = Institution(institution_id=5, name="Stanford University", city="Stanford", state="CA", country="USA")
    affiliation = AwardAffiliation(award_affiliation_id=1, laureate_prize=lp_bertozzi, institution=institution)

    photo = Contribution(
        contribution_id=38, contribution_type="NOBEL_LINKED", title="Photoelectric Effect",
        summary="Einstein explained the photoelectric effect by treating light as discrete quanta.",
        significance="This work helped establish quantum physics.",
        source_url="https://www.nobelprize.org/prizes/physics/1921/summary/",
    )
    photo.credited_laureates.append(ContributionLaureate(laureate=einstein, laureate_prize=lp_einstein))
    click = Contribution(
        contribution_id=779, contribution_type="NOBEL_LINKED", title="Click Chemistry and Bioorthogonal Chemistry",
        summary="Click reactions join molecular building blocks quickly and selectively.",
        significance="Bioorthogonal reactions work inside living organisms without disturbing them.",
        source_url="https://www.nobelprize.org/prizes/chemistry/2022/summary/",
    )
    click.credited_laureates.extend([
        ContributionLaureate(laureate=bertozzi, laureate_prize=lp_bertozzi),
        ContributionLaureate(laureate=sharpless, laureate_prize=lp_sharpless),
    ])

    explanations = [
        Explanation(explanation_id=1, contribution=photo, level="Simple",
                    explanation_text="Light is made of tiny packets called photons that can knock electrons out of metal.",
                    key_concepts="Light has photons\nPhotons knock out electrons"),
        Explanation(explanation_id=2, contribution=photo, level="Explore",
                    explanation_text="Only light above a threshold frequency ejects electrons, regardless of brightness."),
        Explanation(explanation_id=3, contribution=photo, level="Advanced",
                    explanation_text="The maximum kinetic energy equals Planck's constant times frequency minus the work function."),
        Explanation(explanation_id=4, contribution=photo, level="Expert", explanation_text=EXPERT_TEXT),
        Explanation(explanation_id=5, contribution=click, level="Simple",
                    explanation_text="Click chemistry snaps molecules together like buckles, and bioorthogonal reactions do it inside cells."),
    ]
    connections = [
        Connection(connection_id=24, contribution=photo, connection_type="APPLICATION",
                   title="Solar Panels / Photovoltaic Technology",
                   description="Photovoltaic cells convert absorbed photons into electric current.",
                   source_name="U.S. Department of Energy",
                   source_url="https://www.energy.gov/cmei/systems/solar-photovoltaic-cell-basics"),
        Connection(connection_id=29, contribution=photo, connection_type="SCIENTIFIC_LEGACY", related_prize=p2017,
                   title="Quantum Legacy", description="Quantum theory grew from the photon concept."),
    ]
    db.add_all([physics, chemistry, p1921, p2022, p2017, einstein, bertozzi, sharpless, red_cross,
                lp_einstein, lp_bertozzi, lp_sharpless, institution, affiliation, photo, click,
                *explanations, *connections])
    db.commit()


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        _seed(session)
        yield session
    engine.dispose()


@pytest.fixture()
def documents(db_session):
    from backend.ai.documents import build_all_documents

    return build_all_documents(db_session)


@pytest.fixture()
def hashing_embedder():
    from backend.ai.embeddings import HashingEmbedder

    return HashingEmbedder()


@pytest.fixture()
def index_config(tmp_path):
    from backend.ai.config import IndexConfig

    return IndexConfig(persist_dir=tmp_path / "chroma", collection_name="test_nobel")


# --------------------------------------------------------------------------
# Phase 2 tool fixtures (isolated SQLite database, read-only after seeding)
# --------------------------------------------------------------------------

def _sqlite_mysql_compat(dbapi_connection, _record):
    """Register MySQL functions used by the analytics repository."""
    import math

    dbapi_connection.create_function("year", 1, lambda value: int(str(value)[:4]) if value else None)
    dbapi_connection.create_function("floor", 1, lambda value: math.floor(value) if value is not None else None)


@pytest.fixture()
def tool_engine():
    from sqlalchemy import event
    from sqlalchemy.pool import StaticPool

    from backend.ai.tests.tool_fixture_data import seed_tool_fixture

    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    event.listen(engine, "connect", _sqlite_mysql_compat)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_tool_fixture(session)
    with engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA query_only = ON")  # tools must work without write access
    yield engine
    engine.dispose()


@pytest.fixture()
def tool_session_factory(tool_engine):
    from contextlib import contextmanager

    @contextmanager
    def factory():
        session = Session(bind=tool_engine)
        try:
            yield session
        finally:
            session.rollback()
            session.close()

    return factory


@pytest.fixture()
def tool_store(tool_session_factory, hashing_embedder, tmp_path):
    from backend.ai.chunking import chunk_documents
    from backend.ai.config import IndexConfig
    from backend.ai.documents import build_all_documents
    from backend.ai.vector_store import NobelVectorStore

    with tool_session_factory() as db:
        documents = build_all_documents(db)
    store = NobelVectorStore(hashing_embedder, IndexConfig(persist_dir=tmp_path / "tool_index",
                                                           collection_name="tool_test"))
    store.sync(chunk_documents(documents, hashing_embedder.count_tokens))
    return store


@pytest.fixture()
def tool_context(tool_session_factory, tool_store):
    from backend.ai.tools.context import ToolContext

    return ToolContext(session_factory=tool_session_factory, store_provider=lambda: tool_store)


@pytest.fixture()
def tools(tool_context):
    from backend.ai.tools.registry import get_tool_registry

    return get_tool_registry(tool_context)
