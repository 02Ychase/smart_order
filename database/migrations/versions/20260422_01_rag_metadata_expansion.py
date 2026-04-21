from alembic import op
import sqlalchemy as sa


revision = "20260422_01"
down_revision = "20260420_01"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    if op.get_context().as_sql:
        return set()

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    merchant_columns = _column_names("merchants")
    dish_columns = _column_names("dishes")

    if "phone" not in merchant_columns:
        op.add_column("merchants", sa.Column("phone", sa.String(length=32), nullable=False, server_default=""))
    if "business_hours" not in merchant_columns:
        op.add_column("merchants", sa.Column("business_hours", sa.String(length=64), nullable=False, server_default=""))
    if "detailed_address" not in merchant_columns:
        op.add_column("merchants", sa.Column("detailed_address", sa.Text(), nullable=True))
    op.execute(sa.text("UPDATE merchants SET detailed_address = address WHERE detailed_address IS NULL"))
    op.alter_column("merchants", "detailed_address", existing_type=sa.Text(), nullable=False)
    if "address_note" not in merchant_columns:
        op.add_column("merchants", sa.Column("address_note", sa.String(length=128), nullable=False, server_default=""))
    if "merchant_tags" not in merchant_columns:
        op.add_column("merchants", sa.Column("merchant_tags", sa.JSON(), nullable=True))
    op.execute(sa.text("UPDATE merchants SET merchant_tags = '[]' WHERE merchant_tags IS NULL"))
    op.alter_column("merchants", "merchant_tags", existing_type=sa.JSON(), nullable=False)

    if "cuisine_type" not in dish_columns:
        op.add_column("dishes", sa.Column("cuisine_type", sa.String(length=64), nullable=False, server_default=""))
    if "flavor_profile" not in dish_columns:
        op.add_column("dishes", sa.Column("flavor_profile", sa.String(length=64), nullable=False, server_default=""))
    if "ingredients" not in dish_columns:
        op.add_column("dishes", sa.Column("ingredients", sa.JSON(), nullable=True))
    op.execute(sa.text("UPDATE dishes SET ingredients = '[]' WHERE ingredients IS NULL"))
    op.alter_column("dishes", "ingredients", existing_type=sa.JSON(), nullable=False)
    if "allergens" not in dish_columns:
        op.add_column("dishes", sa.Column("allergens", sa.JSON(), nullable=True))
    op.execute(sa.text("UPDATE dishes SET allergens = '[]' WHERE allergens IS NULL"))
    op.alter_column("dishes", "allergens", existing_type=sa.JSON(), nullable=False)
    if "cooking_method" not in dish_columns:
        op.add_column("dishes", sa.Column("cooking_method", sa.String(length=64), nullable=False, server_default=""))


def downgrade() -> None:
    merchant_columns = _column_names("merchants")
    dish_columns = _column_names("dishes")

    if "cooking_method" in dish_columns:
        op.drop_column("dishes", "cooking_method")
    if "allergens" in dish_columns:
        op.drop_column("dishes", "allergens")
    if "ingredients" in dish_columns:
        op.drop_column("dishes", "ingredients")
    if "flavor_profile" in dish_columns:
        op.drop_column("dishes", "flavor_profile")
    if "cuisine_type" in dish_columns:
        op.drop_column("dishes", "cuisine_type")

    if "merchant_tags" in merchant_columns:
        op.drop_column("merchants", "merchant_tags")
    if "address_note" in merchant_columns:
        op.drop_column("merchants", "address_note")
    if "detailed_address" in merchant_columns:
        op.drop_column("merchants", "detailed_address")
    if "business_hours" in merchant_columns:
        op.drop_column("merchants", "business_hours")
    if "phone" in merchant_columns:
        op.drop_column("merchants", "phone")

