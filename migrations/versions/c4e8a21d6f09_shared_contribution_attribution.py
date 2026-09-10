"""Move contribution attribution to explicit laureate associations.

Revision ID: c4e8a21d6f09
Revises: 9b2f4c7d8e10

MySQL DDL is not transactional. Run with application writes stopped and a backup.
Upgrade verifies the complete backfill before removing any attribution columns.
Downgrade refuses shared/orphaned attribution or legacy uniqueness collisions.
"""
from alembic import op
import sqlalchemy as sa

revision = "c4e8a21d6f09"
down_revision = "9b2f4c7d8e10"
branch_labels = None
depends_on = None


def _reject(query, message):
    if op.get_bind().execute(sa.text(query)).first() is not None:
        raise RuntimeError(message)


def upgrade():
    _reject("""
        SELECT c.contribution_id FROM contribution c
        LEFT JOIN laureate_prize lp ON lp.laureate_prize_id=c.laureate_prize_id
        WHERE c.laureate_prize_id IS NOT NULL
          AND (lp.laureate_id IS NULL OR lp.laureate_id <> c.laureate_id)
        LIMIT 1
    """, "Contribution award attribution is inconsistent; backfill aborted.")
    op.create_table(
        "contribution_laureate",
        sa.Column("contribution_id", sa.Integer(), nullable=False),
        sa.Column("laureate_id", sa.Integer(), nullable=False),
        sa.Column("laureate_prize_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("contribution_id", "laureate_id"),
        sa.ForeignKeyConstraint(["contribution_id"], ["contribution.contribution_id"],
                                name="fk_credit_contribution"),
        sa.ForeignKeyConstraint(["laureate_id"], ["laureate.laureate_id"],
                                name="fk_credit_laureate"),
        sa.ForeignKeyConstraint(["laureate_prize_id"], ["laureate_prize.laureate_prize_id"],
                                name="fk_credit_award"),
    )
    op.create_index("ix_contribution_laureate_laureate_id", "contribution_laureate", ["laureate_id"])
    op.create_index("ix_contribution_laureate_award_id", "contribution_laureate", ["laureate_prize_id"])
    op.execute(sa.text("""
        INSERT INTO contribution_laureate (contribution_id, laureate_id, laureate_prize_id)
        SELECT contribution_id, laureate_id, laureate_prize_id FROM contribution
    """))
    # Compare every original attribution (including both existing Einstein rows).
    _reject("""
        SELECT c.contribution_id FROM contribution c
        LEFT JOIN contribution_laureate cl ON cl.contribution_id=c.contribution_id
          AND cl.laureate_id=c.laureate_id
        WHERE cl.contribution_id IS NULL
          OR NOT (cl.laureate_prize_id <=> c.laureate_prize_id)
        LIMIT 1
    """, "Attribution backfill verification failed; original columns retained.")
    bind = op.get_bind()
    count = bind.execute(sa.text("SELECT COUNT(*) FROM contribution")).scalar_one()
    copied = bind.execute(sa.text("SELECT COUNT(*) FROM contribution_laureate")).scalar_one()
    if count != copied:
        raise RuntimeError("Attribution backfill count mismatch; original columns retained.")

    # One atomic MySQL ALTER after successful verification. Child tables/IDs are untouched.
    op.execute(sa.text("""
        ALTER TABLE contribution
          DROP CHECK ck_contribution_prize_link,
          DROP FOREIGN KEY fk_contribution_laureate,
          DROP FOREIGN KEY fk_contribution_laureate_prize,
          DROP INDEX uq_contribution_laureate_type_title,
          DROP INDEX ix_contribution_laureate_id,
          DROP INDEX ix_contribution_laureate_prize_id,
          DROP COLUMN laureate_id,
          DROP COLUMN laureate_prize_id
    """))


def downgrade():
    _reject("""
        SELECT c.contribution_id FROM contribution c
        LEFT JOIN contribution_laureate cl ON cl.contribution_id=c.contribution_id
        GROUP BY c.contribution_id HAVING COUNT(cl.laureate_id) <> 1 LIMIT 1
    """, "Downgrade would lose shared attribution or encounter an uncredited contribution.")
    _reject("""
        SELECT cl.laureate_id FROM contribution c
        JOIN contribution_laureate cl ON cl.contribution_id=c.contribution_id
        GROUP BY cl.laureate_id, c.contribution_type, c.title
        HAVING COUNT(*) > 1 LIMIT 1
    """, "Downgrade would violate legacy contribution title uniqueness.")
    _reject("""
        SELECT c.contribution_id FROM contribution c
        JOIN contribution_laureate cl ON cl.contribution_id=c.contribution_id
        LEFT JOIN laureate_prize lp ON lp.laureate_prize_id=cl.laureate_prize_id
        WHERE (c.contribution_type='NOBEL_LINKED' AND cl.laureate_prize_id IS NULL)
           OR (c.contribution_type='BEYOND_NOBEL' AND cl.laureate_prize_id IS NOT NULL)
           OR (cl.laureate_prize_id IS NOT NULL AND
               (lp.laureate_id IS NULL OR lp.laureate_id <> cl.laureate_id))
        LIMIT 1
    """, "Downgrade cannot represent current award attribution.")
    op.add_column("contribution", sa.Column("laureate_id", sa.Integer(), nullable=True))
    op.add_column("contribution", sa.Column("laureate_prize_id", sa.Integer(), nullable=True))
    op.execute(sa.text("""
        UPDATE contribution c JOIN contribution_laureate cl ON cl.contribution_id=c.contribution_id
        SET c.laureate_id=cl.laureate_id, c.laureate_prize_id=cl.laureate_prize_id
    """))
    _reject("""
        SELECT c.contribution_id FROM contribution c
        JOIN contribution_laureate cl ON cl.contribution_id=c.contribution_id
        WHERE NOT (c.laureate_id <=> cl.laureate_id)
           OR NOT (c.laureate_prize_id <=> cl.laureate_prize_id) LIMIT 1
    """, "Reverse backfill verification failed; junction retained.")
    op.alter_column("contribution", "laureate_id", existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key("fk_contribution_laureate", "contribution", "laureate", ["laureate_id"], ["laureate_id"])
    op.create_foreign_key("fk_contribution_laureate_prize", "contribution", "laureate_prize", ["laureate_prize_id"], ["laureate_prize_id"])
    op.create_check_constraint("ck_contribution_prize_link", "contribution",
        "(contribution_type='NOBEL_LINKED' AND laureate_prize_id IS NOT NULL) OR "
        "(contribution_type='BEYOND_NOBEL' AND laureate_prize_id IS NULL)")
    op.create_unique_constraint("uq_contribution_laureate_type_title", "contribution", ["laureate_id", "contribution_type", "title"])
    op.create_index("ix_contribution_laureate_id", "contribution", ["laureate_id"])
    op.create_index("ix_contribution_laureate_prize_id", "contribution", ["laureate_prize_id"])
    op.drop_table("contribution_laureate")
