"""Turn Nobel Explorer database records into retrieval documents.

Reads go through the existing SQLAlchemy models, repositories and services.
Nothing in this module writes to the database; ``read_only_session`` also
asks MySQL to enforce READ ONLY transactions for the extraction session.

Document identifiers are deterministic and derived from stable keys:

* ``laureate:nobel-<nobel_laureate_id>``   official Nobel API id
* ``contribution:<contribution_id>``
* ``explanation:<contribution_id>:<level>``
* ``connection:<connection_id>``
"""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.pool import NullPool

from backend.ai.config import (
    CITATION_SOURCE_LINKED,
    CITATION_STRUCTURED_RECORD,
    CITATION_UNVERIFIED_EDUCATIONAL,
    EDUCATIONAL_LEVELS,
)
from backend.models.award_affiliation import AwardAffiliation
from backend.models.laureate import Laureate
from backend.models.laureate_prize import LaureatePrize
from backend.models.prize import Prize
from backend.repositories import contribution_repository
from backend.services import connection_service

NOBEL_API_SOURCE_NAME = "Nobel Prize API v2.1 (imported by Nobel Explorer ETL)"

CONNECTION_TYPE_LABELS = {
    "APPLICATION": "Application",
    "EXPERIMENTAL_VALIDATION": "Experimental validation",
    "SCIENTIFIC_LEGACY": "Scientific legacy",
}


@dataclass(frozen=True)
class SourceDocument:
    """One logical record before chunking."""

    doc_id: str
    doc_type: str
    title: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        payload = self.text + "\x1f" + repr(sorted(self.metadata.items()))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@contextmanager
def read_only_session() -> Iterator[Session]:
    """Session on a dedicated, unpooled engine with READ ONLY transactions.

    A separate NullPool engine guarantees the session-level READ ONLY flag
    never leaks into the application's connection pool.
    """
    from backend.database.connection import engine as app_engine

    engine = create_engine(app_engine.url, poolclass=NullPool)
    if engine.dialect.name == "mysql":
        @event.listens_for(engine, "connect")
        def _set_read_only(dbapi_connection, _record):  # pragma: no cover - MySQL only
            cursor = dbapi_connection.cursor()
            cursor.execute("SET SESSION TRANSACTION READ ONLY")
            cursor.close()

    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        engine.dispose()


# --------------------------------------------------------------------------
# Laureate records
# --------------------------------------------------------------------------

def _clean(value: str | None) -> str:
    return " ".join(value.split()) if value else ""


def _place(city: str | None, state: str | None, country: str | None) -> str:
    return ", ".join(part for part in (city, state, country) if part)


def _laureate_text(laureate: Laureate, awards: list[LaureatePrize]) -> str:
    kind = "organization" if laureate.laureate_type.lower() == "organization" else "person"
    lines = [f"{laureate.full_name} (Nobel laureate, {kind})."]

    birth_bits = []
    if laureate.birth_date:
        birth_bits.append(f"Born {laureate.birth_date.isoformat()}")
    place = _place(laureate.birth_city, laureate.birth_state, laureate.birth_country)
    if place:
        birth_bits.append(("in " if birth_bits else "Born in ") + place)
    if birth_bits:
        lines.append(" ".join(birth_bits) + ".")

    for award in awards:
        prize = award.prize
        line = f"Nobel Prize in {prize.category.name} {prize.year}"
        if award.prize_share:
            line += f" (prize share {award.prize_share})"
        motivation = _clean(award.motivation)
        if motivation:
            line += f": {motivation}"
        line += "."
        institutions = [
            _place(aff.institution.name, None, _place(aff.institution.city, aff.institution.state, aff.institution.country))
            for aff in sorted(award.award_affiliations, key=lambda a: a.institution_id)
        ]
        if institutions:
            line += " Affiliation at time of award: " + "; ".join(institutions) + "."
        lines.append(line)
    return "\n".join(lines)


def build_laureate_documents(db: Session) -> list[SourceDocument]:
    statement = (
        select(Laureate)
        .options(
            selectinload(Laureate.laureate_prizes)
            .selectinload(LaureatePrize.prize)
            .selectinload(Prize.category),
            selectinload(Laureate.laureate_prizes)
            .selectinload(LaureatePrize.award_affiliations)
            .selectinload(AwardAffiliation.institution),
        )
        .order_by(Laureate.laureate_id)
    )
    documents = []
    for laureate in db.scalars(statement).all():
        awards = sorted(
            laureate.laureate_prizes,
            key=lambda a: (a.prize.year, a.prize.category.name, a.laureate_prize_id),
        )
        metadata: dict[str, Any] = {
            "laureate_ids": [laureate.laureate_id],
            "nobel_laureate_id": laureate.nobel_laureate_id,
            "laureate_names": laureate.full_name,
            "laureate_type": laureate.laureate_type,
            "source_name": NOBEL_API_SOURCE_NAME,
            "citation_status": CITATION_STRUCTURED_RECORD,
        }
        if awards:
            metadata["prize_years"] = sorted({a.prize.year for a in awards})
            metadata["categories"] = sorted({a.prize.category.name for a in awards})
        documents.append(SourceDocument(
            doc_id=f"laureate:nobel-{laureate.nobel_laureate_id}",
            doc_type="laureate_record",
            title=laureate.full_name,
            text=_laureate_text(laureate, awards),
            metadata=metadata,
        ))
    return documents


# --------------------------------------------------------------------------
# Contributions, explanations and connections
# --------------------------------------------------------------------------

def _credit_metadata(contribution) -> dict[str, Any]:
    credits = sorted(contribution.credited_laureates, key=lambda c: c.laureate_id)
    metadata: dict[str, Any] = {
        "laureate_ids": [c.laureate_id for c in credits],
        "laureate_names": "; ".join(c.laureate.full_name for c in credits),
        "contribution_id": contribution.contribution_id,
        "contribution_title": contribution.title,
        "contribution_type": contribution.contribution_type,
    }
    prizes = [c.laureate_prize.prize for c in credits if c.laureate_prize is not None]
    if prizes:
        metadata["prize_years"] = sorted({p.year for p in prizes})
        metadata["categories"] = sorted({p.category.name for p in prizes})
    return metadata


def _credit_line(contribution) -> str:
    parts = []
    for credit in sorted(contribution.credited_laureates, key=lambda c: c.laureate_id):
        label = credit.laureate.full_name
        if credit.laureate_prize is not None:
            prize = credit.laureate_prize.prize
            label += f" (Nobel Prize in {prize.category.name} {prize.year})"
        parts.append(label)
    return "; ".join(parts)


def _source_name_for(url: str | None) -> str:
    # Contributions store only a URL; derive a display name from the host
    # without inventing anything beyond what the URL already states.
    if not url:
        return ""
    host = url.split("//", 1)[-1].split("/", 1)[0].lower()
    return "NobelPrize.org" if host.endswith("nobelprize.org") else host


def build_education_documents(db: Session) -> list[SourceDocument]:
    documents: list[SourceDocument] = []
    for contribution in contribution_repository.list_catalog(db):
        base = _credit_metadata(contribution)
        credit_line = _credit_line(contribution)
        kind = (
            "Nobel-linked contribution"
            if contribution.contribution_type == "NOBEL_LINKED"
            else "contribution beyond the Nobel Prize"
        )
        source_url = contribution.source_url or ""
        source_name = _source_name_for(source_url)

        body = [f"Discovery: {contribution.title} ({kind})."]
        if credit_line:
            body.append(f"Credited laureates: {credit_line}.")
        if contribution.summary:
            body.append(f"Summary: {_clean(contribution.summary)}")
        if contribution.significance:
            body.append(f"Significance: {_clean(contribution.significance)}")
        contribution_meta = {**base, "citation_status": CITATION_SOURCE_LINKED if source_url else CITATION_UNVERIFIED_EDUCATIONAL}
        if source_url:
            contribution_meta.update(source_name=source_name, source_url=source_url)
        documents.append(SourceDocument(
            doc_id=f"contribution:{contribution.contribution_id}",
            doc_type="contribution",
            title=contribution.title,
            text="\n".join(body),
            metadata=contribution_meta,
        ))

        level_order = {level: i for i, level in enumerate(EDUCATIONAL_LEVELS)}
        for explanation in sorted(contribution.explanations, key=lambda e: level_order.get(e.level, 99)):
            text = explanation.explanation_text.strip()
            concepts = [c.strip() for c in (explanation.key_concepts or "").splitlines() if c.strip()]
            if concepts:
                text += "\n\nKey concepts: " + "; ".join(concepts) + "."
            meta = {**base, "level": explanation.level, "citation_status": CITATION_UNVERIFIED_EDUCATIONAL}
            if source_url:
                # Context only: NOT a citation for the explanation text.
                meta.update(related_source_name=source_name, related_source_url=source_url)
            documents.append(SourceDocument(
                doc_id=f"explanation:{contribution.contribution_id}:{explanation.level.lower()}",
                doc_type="explanation",
                title=f"{contribution.title} - {explanation.level} explanation",
                text=text,
                metadata=meta,
            ))

        for connection in connection_service.list_connections(db, contribution.contribution_id):
            label = CONNECTION_TYPE_LABELS.get(connection.connection_type, connection.connection_type)
            text = f"{contribution.title} - {label}: {connection.title}."
            if connection.related_prize is not None:
                rp = connection.related_prize
                text += f" Related Nobel Prize: {rp.category} {rp.year}."
            if connection.description:
                text += f"\n{_clean(connection.description)}"
            meta = {**base, "connection_type": connection.connection_type}
            if connection.source_url:
                meta.update(
                    source_name=connection.source_name or _source_name_for(connection.source_url),
                    source_url=connection.source_url,
                    citation_status=CITATION_SOURCE_LINKED,
                )
            else:
                meta["citation_status"] = CITATION_UNVERIFIED_EDUCATIONAL
            if connection.related_prize is not None:
                meta["related_prize_year"] = connection.related_prize.year
                meta["related_prize_category"] = connection.related_prize.category
            documents.append(SourceDocument(
                doc_id=f"connection:{connection.connection_id}",
                doc_type="connection",
                title=f"{contribution.title} - {connection.title}",
                text=text,
                metadata=meta,
            ))
    return documents


def build_all_documents(db: Session) -> list[SourceDocument]:
    documents = build_laureate_documents(db) + build_education_documents(db)
    duplicates = {doc_id for doc_id, n in Counter(d.doc_id for d in documents).items() if n > 1}
    if duplicates:
        raise ValueError(f"Duplicate document ids: {sorted(duplicates)[:5]}")
    return documents
