"""Exercise real MySQL DDL in a disposable database, never in the app schema."""
import importlib

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text

from backend.database.connection import engine

migration = importlib.import_module(
    "migrations.versions.c4e8a21d6f09_shared_contribution_attribution"
)


@pytest.fixture
def migration_db():
    # The app DB user is only granted CREATE/DROP on this exact,
    # pre-provisioned schema name (not on databases in general), so this
    # must stay a fixed name rather than a per-run random one. Tests using
    # it run sequentially (no xdist), and the fixture drops it on
    # teardown, so reuse across runs is safe.
    name = "nobel_explorer_migration_test"
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as admin:
        admin.exec_driver_sql(f"DROP DATABASE IF EXISTS `{name}`")
        admin.exec_driver_sql(f"CREATE DATABASE `{name}`")
    scratch = create_engine(engine.url.set(database=name), isolation_level="AUTOCOMMIT")
    try:
        with scratch.connect() as db:
            for ddl in [
                "CREATE TABLE laureate (laureate_id INT PRIMARY KEY)",
                "CREATE TABLE laureate_prize (laureate_prize_id INT PRIMARY KEY, laureate_id INT NOT NULL, FOREIGN KEY (laureate_id) REFERENCES laureate(laureate_id))",
                """CREATE TABLE contribution (
                    contribution_id INT PRIMARY KEY, laureate_id INT NOT NULL,
                    laureate_prize_id INT NULL, contribution_type VARCHAR(30) NOT NULL,
                    title VARCHAR(200) NOT NULL, summary TEXT, significance TEXT, source_url TEXT,
                    CONSTRAINT fk_contribution_laureate FOREIGN KEY (laureate_id) REFERENCES laureate(laureate_id),
                    CONSTRAINT fk_contribution_laureate_prize FOREIGN KEY (laureate_prize_id) REFERENCES laureate_prize(laureate_prize_id),
                    CONSTRAINT ck_contribution_type CHECK (contribution_type IN ('NOBEL_LINKED','BEYOND_NOBEL')),
                    CONSTRAINT ck_contribution_prize_link CHECK (
                        (contribution_type='NOBEL_LINKED' AND laureate_prize_id IS NOT NULL) OR
                        (contribution_type='BEYOND_NOBEL' AND laureate_prize_id IS NULL)),
                    UNIQUE KEY uq_contribution_laureate_type_title (laureate_id,contribution_type,title),
                    KEY ix_contribution_laureate_id (laureate_id),
                    KEY ix_contribution_laureate_prize_id (laureate_prize_id))""",
            ]:
                db.exec_driver_sql(ddl)
            for table in ("explanation", "connection", "quiz_question"):
                db.exec_driver_sql(f"CREATE TABLE `{table}` (id INT PRIMARY KEY, contribution_id INT NOT NULL, content TEXT, FOREIGN KEY (contribution_id) REFERENCES contribution(contribution_id))")
            db.exec_driver_sql("INSERT INTO laureate VALUES (249),(999)")
            db.exec_driver_sql("INSERT INTO laureate_prize VALUES (226,249),(999,999)")
            db.exec_driver_sql("INSERT INTO contribution VALUES (38,249,226,'NOBEL_LINKED','Photoelectric Effect','summary','significance','source'),(39,249,NULL,'BEYOND_NOBEL','General Relativity','summary2','significance2','source2')")
            for table in ("explanation", "connection", "quiz_question"):
                db.exec_driver_sql(f"INSERT INTO `{table}` VALUES (38,38,'unchanged content'),(39,39,'unchanged content 2')")
            with Operations.context(MigrationContext.configure(db)):
                yield db
    finally:
        scratch.dispose()
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as admin:
            admin.exec_driver_sql(f"DROP DATABASE IF EXISTS `{name}`")


def snapshot(db):
    return {
        table: list(db.execute(text(f"SELECT * FROM `{table}` ORDER BY 1")))
        for table in ("contribution", "explanation", "connection", "quiz_question")
    }


def test_migration_preserves_content_and_reverses(migration_db):
    db = migration_db
    before = snapshot(db)
    migration.upgrade()
    assert list(db.execute(text("SELECT * FROM contribution_laureate ORDER BY contribution_id"))) == [(38,249,226),(39,249,None)]
    after = snapshot(db)
    for table in ("explanation", "connection", "quiz_question"):
        assert after[table] == before[table]
    assert after["contribution"] == [(row[0], *row[3:]) for row in before["contribution"]]
    migration.downgrade()
    # Restored columns are appended, so compare mappings rather than column order.
    assert list(db.execute(text("SELECT contribution_id,laureate_id,laureate_prize_id,contribution_type,title,summary,significance,source_url FROM contribution ORDER BY contribution_id"))) == before["contribution"]
    for table in ("explanation", "connection", "quiz_question"):
        assert snapshot(db)[table] == before[table]
    migration.upgrade()
    assert db.execute(text("SELECT COUNT(*) FROM contribution_laureate")).scalar_one() == 2


def test_downgrade_refuses_shared_attribution_before_ddl(migration_db):
    db = migration_db
    migration.upgrade()
    db.exec_driver_sql("INSERT INTO contribution_laureate VALUES (38,999,999)")
    before = snapshot(db)
    with pytest.raises(RuntimeError, match="shared attribution"):
        migration.downgrade()
    assert snapshot(db) == before
    assert db.execute(text("SELECT COUNT(*) FROM contribution_laureate")).scalar_one() == 3


def test_upgrade_rejects_mismatched_award_before_ddl(migration_db):
    db = migration_db
    db.exec_driver_sql("UPDATE contribution SET laureate_prize_id=999 WHERE contribution_id=38")
    before = snapshot(db)
    with pytest.raises(RuntimeError, match="inconsistent"):
        migration.upgrade()
    assert snapshot(db) == before
    assert not db.exec_driver_sql("SHOW TABLES LIKE 'contribution_laureate'").first()
