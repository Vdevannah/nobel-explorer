"""Read-only extraction checks against the live local Nobel Explorer database.

Opt-in: AI_RUN_LIVE_DB_TESTS=1 with DB_* variables pointing at a dev database.
"""

import pytest
from sqlalchemy import func, select, text

from backend.models import Connection, Contribution, Explanation, Laureate

pytestmark = pytest.mark.live_db


@pytest.fixture(scope="module")
def live_documents():
    from backend.ai.documents import build_all_documents, read_only_session

    with read_only_session() as db:
        counts = {
            "laureate_record": db.scalar(select(func.count()).select_from(Laureate)),
            "contribution": db.scalar(select(func.count()).select_from(Contribution)),
            "explanation": db.scalar(select(func.count()).select_from(Explanation)),
            "connection": db.scalar(select(func.count()).select_from(Connection)),
        }
        return counts, build_all_documents(db)


def test_one_document_per_source_record(live_documents):
    counts, documents = live_documents
    for doc_type, expected in counts.items():
        assert sum(1 for d in documents if d.doc_type == doc_type) == expected


def test_extraction_session_is_read_only():
    from backend.ai.documents import read_only_session

    with read_only_session() as db:
        if db.bind.dialect.name != "mysql":
            pytest.skip("read-only enforcement is MySQL specific")
        assert db.execute(text("SELECT @@session.transaction_read_only")).scalar() == 1


def test_live_metadata_is_chroma_compatible(live_documents):
    pytest.importorskip("chromadb")
    from backend.ai.chunking import chunk_documents
    from backend.ai.embeddings import HashingEmbedder
    from backend.ai.vector_store import validate_metadata

    _, documents = live_documents
    for chunk in chunk_documents(documents, HashingEmbedder().count_tokens):
        validate_metadata(chunk.metadata)
