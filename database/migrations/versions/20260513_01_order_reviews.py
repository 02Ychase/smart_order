from alembic import op
import sqlalchemy as sa


revision = "20260513_01"
down_revision = "20260428_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "order_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("checkout_order_id", sa.Integer(), sa.ForeignKey("checkout_orders.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_order_reviews_checkout_order_id", "order_reviews", ["checkout_order_id"])
    op.create_index("ix_order_reviews_user_id", "order_reviews", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_order_reviews_user_id", table_name="order_reviews")
    op.drop_index("ix_order_reviews_checkout_order_id", table_name="order_reviews")
    op.drop_table("order_reviews")
