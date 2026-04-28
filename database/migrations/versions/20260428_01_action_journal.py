from alembic import op
import sqlalchemy as sa


revision = "20260428_01"
down_revision = "20260422_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "action_journal",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("action_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("undo_policy", sa.String(length=64), nullable=False),
        sa.Column("undo_tool", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("before_snapshot", sa.JSON(), nullable=False),
        sa.Column("after_snapshot", sa.JSON(), nullable=False),
        sa.Column("natural_summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("action_id"),
    )
    op.create_index("ix_action_journal_action_id", "action_journal", ["action_id"], unique=True)
    op.create_index("ix_action_journal_session_id", "action_journal", ["session_id"])
    op.create_index("ix_action_journal_user_id", "action_journal", ["user_id"])
    op.create_index("ix_action_journal_action_type", "action_journal", ["action_type"])


def downgrade() -> None:
    op.drop_index("ix_action_journal_action_type", table_name="action_journal")
    op.drop_index("ix_action_journal_user_id", table_name="action_journal")
    op.drop_index("ix_action_journal_session_id", table_name="action_journal")
    op.drop_index("ix_action_journal_action_id", table_name="action_journal")
    op.drop_table("action_journal")
