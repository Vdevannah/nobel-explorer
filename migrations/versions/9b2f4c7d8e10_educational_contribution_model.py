"""evolve educational content into contributions and connections

Revision ID: 9b2f4c7d8e10
Revises: 1439ccb7a517
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9b2f4c7d8e10"
down_revision: Union[str, Sequence[str], None] = "1439ccb7a517"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _stop_if_explanations_would_collide() -> None:
    connection = op.get_bind()
    collision = connection.execute(
        sa.text(
            """
            SELECT a.discovery_id, e.level, COUNT(*) AS duplicate_count
            FROM explanation AS e
            JOIN application AS a
              ON a.application_id = e.application_id
            GROUP BY a.discovery_id, e.level
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if collision is not None:
        raise RuntimeError(
            "Cannot migrate explanations: multiple application-level rows "
            "would collapse onto the same (contribution_id, level)."
        )


def upgrade() -> None:
    _stop_if_explanations_would_collide()

    op.create_table(
        "contribution",
        sa.Column("contribution_id", sa.Integer(), nullable=False),
        sa.Column("laureate_id", sa.Integer(), nullable=False),
        sa.Column("laureate_prize_id", sa.Integer(), nullable=True),
        sa.Column("contribution_type", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("significance", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "contribution_type IN ('NOBEL_LINKED', 'BEYOND_NOBEL')",
            name="ck_contribution_type",
        ),
        sa.CheckConstraint(
            "(contribution_type = 'NOBEL_LINKED' AND laureate_prize_id IS NOT NULL) "
            "OR (contribution_type = 'BEYOND_NOBEL' AND laureate_prize_id IS NULL)",
            name="ck_contribution_prize_link",
        ),
        sa.ForeignKeyConstraint(
            ["laureate_id"],
            ["laureate.laureate_id"],
            name="fk_contribution_laureate",
        ),
        sa.ForeignKeyConstraint(
            ["laureate_prize_id"],
            ["laureate_prize.laureate_prize_id"],
            name="fk_contribution_laureate_prize",
        ),
        sa.PrimaryKeyConstraint("contribution_id"),
        sa.UniqueConstraint(
            "laureate_id",
            "contribution_type",
            "title",
            name="uq_contribution_laureate_type_title",
        ),
    )
    op.create_index("ix_contribution_laureate_id", "contribution", ["laureate_id"])
    op.create_index(
        "ix_contribution_laureate_prize_id",
        "contribution",
        ["laureate_prize_id"],
    )

    op.execute(
        sa.text(
            """
            INSERT INTO contribution (
                contribution_id, laureate_id, laureate_prize_id,
                contribution_type, title, summary, significance, source_url
            )
            SELECT
                d.discovery_id, lp.laureate_id, d.laureate_prize_id,
                'NOBEL_LINKED', d.title, d.summary, d.significance, d.source_url
            FROM discovery AS d
            JOIN laureate_prize AS lp
              ON lp.laureate_prize_id = d.laureate_prize_id
            """
        )
    )

    op.create_table(
        "connection",
        sa.Column("connection_id", sa.Integer(), nullable=False),
        sa.Column("contribution_id", sa.Integer(), nullable=False),
        sa.Column("connection_type", sa.String(length=40), nullable=False),
        sa.Column("related_prize_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_name", sa.String(length=200), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "connection_type IN "
            "('APPLICATION', 'EXPERIMENTAL_VALIDATION', 'SCIENTIFIC_LEGACY')",
            name="ck_connection_type",
        ),
        sa.CheckConstraint(
            "related_prize_id IS NULL OR connection_type = 'SCIENTIFIC_LEGACY'",
            name="ck_connection_related_prize",
        ),
        sa.ForeignKeyConstraint(
            ["contribution_id"],
            ["contribution.contribution_id"],
            name="fk_connection_contribution",
        ),
        sa.ForeignKeyConstraint(
            ["related_prize_id"],
            ["prize.prize_id"],
            name="fk_connection_related_prize",
        ),
        sa.PrimaryKeyConstraint("connection_id"),
        sa.UniqueConstraint(
            "contribution_id",
            "connection_type",
            "title",
            name="uq_connection_contribution_type_title",
        ),
    )
    op.create_index("ix_connection_contribution_id", "connection", ["contribution_id"])
    op.create_index("ix_connection_related_prize_id", "connection", ["related_prize_id"])
    op.execute(
        sa.text(
            """
            INSERT INTO connection (
                connection_id, contribution_id, connection_type,
                related_prize_id, title, description, source_name, source_url
            )
            SELECT
                application_id, discovery_id, 'APPLICATION', NULL,
                title, description, source_name, source_url
            FROM application
            """
        )
    )

    op.create_table(
        "explanation_new",
        sa.Column("explanation_id", sa.Integer(), nullable=False),
        sa.Column("contribution_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=50), nullable=False),
        sa.Column("explanation_text", sa.Text(), nullable=False),
        sa.Column("key_concepts", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "level IN ('Simple', 'Explore', 'Advanced', 'Expert')",
            name="ck_explanation_level",
        ),
        sa.ForeignKeyConstraint(
            ["contribution_id"],
            ["contribution.contribution_id"],
            name="fk_explanation_contribution",
        ),
        sa.PrimaryKeyConstraint("explanation_id"),
        sa.UniqueConstraint(
            "contribution_id",
            "level",
            name="uq_explanation_contribution_level",
        ),
    )
    op.create_index(
        "ix_explanation_contribution_id",
        "explanation_new",
        ["contribution_id"],
    )
    op.execute(
        sa.text(
            """
            INSERT INTO explanation_new (
                explanation_id, contribution_id, level,
                explanation_text, key_concepts
            )
            SELECT
                e.explanation_id, a.discovery_id, e.level,
                e.explanation_text, e.key_concepts
            FROM explanation AS e
            JOIN application AS a
              ON a.application_id = e.application_id
            """
        )
    )

    op.create_table(
        "quiz_question_new",
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("contribution_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=50), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("choice_a", sa.String(length=500), nullable=False),
        sa.Column("choice_b", sa.String(length=500), nullable=False),
        sa.Column("choice_c", sa.String(length=500), nullable=False),
        sa.Column("choice_d", sa.String(length=500), nullable=False),
        sa.Column("correct_answer", sa.String(length=10), nullable=False),
        sa.Column("answer_explanation", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "level IN ('Simple', 'Explore', 'Advanced', 'Expert')",
            name="ck_quiz_question_level",
        ),
        sa.CheckConstraint(
            "correct_answer IN ('A', 'B', 'C', 'D')",
            name="ck_quiz_question_correct_answer",
        ),
        sa.ForeignKeyConstraint(
            ["contribution_id"],
            ["contribution.contribution_id"],
            name="fk_quiz_question_contribution",
        ),
        sa.PrimaryKeyConstraint("question_id"),
    )
    op.create_index(
        "ix_quiz_question_contribution_id",
        "quiz_question_new",
        ["contribution_id"],
    )
    op.execute(
        sa.text(
            """
            INSERT INTO quiz_question_new (
                question_id, contribution_id, level, question,
                choice_a, choice_b, choice_c, choice_d,
                correct_answer, answer_explanation
            )
            SELECT
                question_id, discovery_id, level, question,
                choice_a, choice_b, choice_c, choice_d,
                correct_answer, answer_explanation
            FROM quiz_question
            """
        )
    )

    op.drop_table("explanation")
    op.drop_table("quiz_question")
    op.drop_table("application")
    op.drop_table("discovery")
    op.rename_table("explanation_new", "explanation")
    op.rename_table("quiz_question_new", "quiz_question")


def downgrade() -> None:
    connection = op.get_bind()
    explanation_count = connection.execute(
        sa.text("SELECT COUNT(*) FROM explanation")
    ).scalar_one()
    incompatible_contribution = connection.execute(
        sa.text(
            "SELECT contribution_id FROM contribution "
            "WHERE contribution_type <> 'NOBEL_LINKED' LIMIT 1"
        )
    ).first()
    incompatible_connection = connection.execute(
        sa.text(
            "SELECT connection_id FROM connection "
            "WHERE connection_type <> 'APPLICATION' "
            "OR related_prize_id IS NOT NULL LIMIT 1"
        )
    ).first()
    if explanation_count or incompatible_contribution or incompatible_connection:
        raise RuntimeError(
            "Downgrade would lose contribution-level educational meaning. "
            "Remove or migrate incompatible educational rows explicitly first."
        )

    op.create_table(
        "discovery",
        sa.Column("discovery_id", sa.Integer(), nullable=False),
        sa.Column("laureate_prize_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("significance", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["laureate_prize_id"],
            ["laureate_prize.laureate_prize_id"],
        ),
        sa.PrimaryKeyConstraint("discovery_id"),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO discovery
            SELECT contribution_id, laureate_prize_id, title,
                   summary, significance, source_url
            FROM contribution
            """
        )
    )

    op.create_table(
        "application",
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("discovery_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_name", sa.String(length=200), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["discovery_id"], ["discovery.discovery_id"]),
        sa.PrimaryKeyConstraint("application_id"),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO application
            SELECT connection_id, contribution_id, title,
                   description, source_name, source_url
            FROM connection
            """
        )
    )

    op.create_table(
        "explanation_old",
        sa.Column("explanation_id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=50), nullable=False),
        sa.Column("explanation_text", sa.Text(), nullable=False),
        sa.Column("key_concepts", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["application_id"], ["application.application_id"]),
        sa.PrimaryKeyConstraint("explanation_id"),
        sa.UniqueConstraint(
            "application_id",
            "level",
            name="uq_explanation_application_level",
        ),
    )

    op.create_table(
        "quiz_question_old",
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("discovery_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=50), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("choice_a", sa.String(length=500), nullable=False),
        sa.Column("choice_b", sa.String(length=500), nullable=False),
        sa.Column("choice_c", sa.String(length=500), nullable=False),
        sa.Column("choice_d", sa.String(length=500), nullable=False),
        sa.Column("correct_answer", sa.String(length=10), nullable=False),
        sa.Column("answer_explanation", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["discovery_id"], ["discovery.discovery_id"]),
        sa.PrimaryKeyConstraint("question_id"),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO quiz_question_old
            SELECT question_id, contribution_id, level, question,
                   choice_a, choice_b, choice_c, choice_d,
                   correct_answer, answer_explanation
            FROM quiz_question
            """
        )
    )

    op.drop_table("explanation")
    op.drop_table("quiz_question")
    op.drop_table("connection")
    op.drop_table("contribution")
    op.rename_table("explanation_old", "explanation")
    op.rename_table("quiz_question_old", "quiz_question")
