"""Opt-in integration tests: real MySQL (read-only) and the real embedding model.

    AI_RUN_LIVE_DB_TESTS=1 AI_RUN_REAL_MODEL_TESTS=1 pytest backend/ai/tests/test_tool_live.py

Statistics are cross-checked against independent raw SQL written separately
from the ORM code under test.
"""

import pytest
from sqlalchemy import text

pytest.importorskip("langchain_core")
pytest.importorskip("chromadb")


@pytest.fixture(scope="module")
def live_tools():
    from backend.ai.tools import get_tool_registry

    return get_tool_registry()


@pytest.fixture(scope="module")
def raw_sql():
    from backend.ai.documents import read_only_session

    def run(sql):
        with read_only_session() as db:
            return db.execute(text(sql)).fetchall()

    return run


@pytest.mark.live_db
def test_live_2022_chemistry(live_tools):
    data = live_tools["search_laureates"].invoke({"year": 2022, "category": "Chemistry"})["data"]
    assert [l["full_name"] for l in data["laureates"]] == [
        "Carolyn R. Bertozzi", "K. Barry Sharpless", "Morten Meldal"]


@pytest.mark.live_db
def test_live_tool_sessions_are_read_only():
    from backend.ai.tools.context import ToolContext

    with ToolContext().session_factory() as db:
        assert db.execute(text("SELECT @@session.transaction_read_only")).scalar() == 1
        with pytest.raises(Exception, match="READ ONLY|read only|1792"):
            db.execute(text("UPDATE laureate SET full_name = full_name WHERE laureate_id = -1"))


@pytest.mark.live_db
def test_live_summary_matches_independent_sql(live_tools, raw_sql):
    result = live_tools["get_nobel_statistics"].invoke({"operation": "summary"})["data"]["result"]
    assert result["distinct_laureates"] == raw_sql("SELECT COUNT(*) FROM laureate")[0][0]
    assert result["laureate_prize_awards"] == raw_sql("SELECT COUNT(*) FROM laureate_prize")[0][0]
    assert result["prizes"] == raw_sql("SELECT COUNT(*) FROM prize")[0][0]
    assert result["distinct_organization_laureates"] == raw_sql(
        "SELECT COUNT(*) FROM laureate WHERE laureate_type = 'Organization'")[0][0]


@pytest.mark.live_db
def test_live_category_counts_match_independent_sql(live_tools, raw_sql):
    rows = live_tools["get_nobel_statistics"].invoke({"operation": "laureates_by_category"})["data"]["result"]
    expected = dict(raw_sql(
        "SELECT c.name, COUNT(DISTINCT lp.laureate_id) FROM laureate_prize lp "
        "JOIN prize p ON p.prize_id = lp.prize_id JOIN category c ON c.category_id = p.category_id GROUP BY c.name"))
    assert {r["category"]: r["laureate_count"] for r in rows} == expected


@pytest.mark.live_db
def test_live_top_birth_countries_match_independent_sql(live_tools, raw_sql):
    rows = live_tools["get_nobel_statistics"].invoke({"operation": "top_birth_countries", "limit": 5})["data"]["result"]
    expected = raw_sql(
        "SELECT birth_country, COUNT(*) n FROM laureate WHERE laureate_type = 'Person' AND birth_country IS NOT NULL "
        "GROUP BY birth_country ORDER BY n DESC, birth_country ASC LIMIT 5")
    assert [(r["birth_country"], r["laureate_count"]) for r in rows] == [tuple(e) for e in expected]


@pytest.mark.live_db
def test_live_details_for_einstein(live_tools):
    data = live_tools["get_laureate_details"].invoke({"laureate_id": 249})["data"]
    assert data["laureate"]["full_name"] == "Albert Einstein"
    assert [c["title"] for c in data["contributions"]] == ["Photoelectric Effect", "General Relativity"]


@pytest.mark.live_db
@pytest.mark.real_model
def test_live_knowledge_weak_evidence(live_tools):
    relevant = live_tools["search_nobel_knowledge"].invoke({"query": "How do solar cells turn sunlight into electricity?",
                                                            "k": 3})["data"]
    assert relevant["results"][0]["doc_id"] == "connection:24" and relevant["results"][0]["weak_match"] is False

    sourdough = live_tools["search_nobel_knowledge"].invoke({"query": "What is a good recipe for sourdough bread?"})["data"]
    assert sourdough["all_results_weak"] is True

    incompatible = live_tools["search_nobel_knowledge"].invoke(
        {"query": "photoelectric effect", "level": "Expert", "laureate_id": 774})["data"]
    assert incompatible["results"][0]["similarity"] < 0 and incompatible["all_results_weak"] is True

    # False premise that still scores HIGH: the weak-match flag cannot catch it.
    maths = live_tools["search_nobel_knowledge"].invoke({"query": "Who won the Nobel Prize in Mathematics in 1950?"})["data"]
    assert maths["results"][0]["similarity"] > 0.6 and maths["results"][0]["weak_match"] is False
    # ...but structured validation does.
    structured = live_tools["search_laureates"].invoke({"category": "Mathematics", "year": 1950})
    assert structured["ok"] is False and "no Nobel Prize in Mathematics" in structured["error"]["message"]
