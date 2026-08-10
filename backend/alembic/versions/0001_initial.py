"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("entity_type", sa.String(length=16), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=256), nullable=False),
        sa.Column("stored_name", sa.String(length=256), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attachments_entity_type", "attachments", ["entity_type"])
    op.create_index("ix_attachments_entity_id", "attachments", ["entity_id"])

    op.create_table(
        "locations",
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("parent_id", sa.String(length=36), nullable=True),
        sa.Column("location_type", sa.String(length=32), nullable=True),
        sa.Column("dimensions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("notes", sa.String(length=512), nullable=True),
        sa.Column("qr_code", sa.String(length=256), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["locations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("qr_code"),
    )
    op.create_index("ix_locations_parent_id", "locations", ["parent_id"])
    op.create_index("ix_locations_name", "locations", ["name"])

    op.create_table(
        "organizers",
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("outer_width", sa.Float(), nullable=False),
        sa.Column("outer_depth", sa.Float(), nullable=False),
        sa.Column("outer_height", sa.Float(), nullable=False),
        sa.Column("preset", sa.String(length=64), nullable=True),
        sa.Column("wall_thickness", sa.Float(), nullable=False),
        sa.Column("divider_thickness", sa.Float(), nullable=False),
        sa.Column("clearance", sa.Float(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("storage_status", sa.String(length=16), nullable=False),
        sa.Column("stl_path", sa.String(length=512), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "parts",
        sa.Column("internal_id", sa.String(length=128), nullable=True),
        sa.Column("manufacturer", sa.String(length=128), nullable=True),
        sa.Column("mpn", sa.String(length=128), nullable=True),
        sa.Column("lcsc_number", sa.String(length=64), nullable=True),
        sa.Column("digikey_number", sa.String(length=64), nullable=True),
        sa.Column("value", sa.String(length=128), nullable=True),
        sa.Column("package", sa.String(length=64), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tolerance", sa.String(length=64), nullable=True),
        sa.Column("voltage_rating", sa.String(length=64), nullable=True),
        sa.Column("current_rating", sa.String(length=64), nullable=True),
        sa.Column("other_specs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("datasheet_url", sa.String(length=512), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("min_qty", sa.Integer(), nullable=True),
        sa.Column("desired_qty", sa.Integer(), nullable=True),
        sa.Column("reorder_qty", sa.Integer(), nullable=True),
        sa.Column("storage_status", sa.String(length=16), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_parts_lcsc_number", "parts", ["lcsc_number"])
    op.create_index("ix_parts_digikey_number", "parts", ["digikey_number"])
    op.create_index("ix_parts_manufacturer", "parts", ["manufacturer"])
    op.create_index("ix_parts_mpn", "parts", ["mpn"])
    op.create_index("ix_parts_category", "parts", ["category"])
    op.create_index("ix_parts_internal_id", "parts", ["internal_id"], unique=True)
    op.create_index("ix_parts_storage_status", "parts", ["storage_status"])
    op.create_index("ix_parts_value", "parts", ["value"])
    op.create_index("ix_parts_package", "parts", ["package"])

    op.create_table(
        "projects",
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column("build_qty", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_name", "projects", ["name"])
    op.create_index("ix_projects_status", "projects", ["status"])

    op.create_table(
        "shopping_lists",
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shopping_lists_status", "shopping_lists", ["status"])

    op.create_table(
        "suppliers",
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("website", sa.String(length=512), nullable=True),
        sa.Column("notes", sa.String(length=512), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "users",
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("email", sa.String(length=256), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "api_keys",
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("key_hash", sa.String(length=256), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )

    op.create_table(
        "boms",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_boms_project_id", "boms", ["project_id"])

    op.create_table(
        "esp32_devices",
        sa.Column("organizer_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("api_key_hash", sa.String(length=256), nullable=False),
        sa.Column("firmware_version", sa.String(length=32), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("online", sa.Boolean(), nullable=False),
        sa.Column("mac_address", sa.String(length=32), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organizer_id"], ["organizers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("api_key_hash"),
    )
    op.create_index("ix_esp32_devices_organizer_id", "esp32_devices", ["organizer_id"])

    op.create_table(
        "inventory_items",
        sa.Column("part_id", sa.String(length=36), nullable=False),
        sa.Column("location_id", sa.String(length=36), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["part_id"], ["parts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("part_id", "location_id", name="uq_part_location"),
    )
    op.create_index("ix_inventory_items_location_id", "inventory_items", ["location_id"])
    op.create_index("ix_inventory_items_part_id", "inventory_items", ["part_id"])

    op.create_table(
        "organizer_compartments",
        sa.Column("organizer_id", sa.String(length=36), nullable=False),
        sa.Column("label", sa.String(length=64), nullable=True),
        sa.Column("row", sa.Integer(), nullable=False),
        sa.Column("col", sa.Integer(), nullable=False),
        sa.Column("width", sa.Float(), nullable=False),
        sa.Column("depth", sa.Float(), nullable=False),
        sa.Column("height", sa.Float(), nullable=False),
        sa.Column("part_id", sa.String(length=36), nullable=True),
        sa.Column("location_id", sa.String(length=36), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organizer_id"], ["organizers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["part_id"], ["parts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organizer_compartments_location_id", "organizer_compartments", ["location_id"])
    op.create_index("ix_organizer_compartments_part_id", "organizer_compartments", ["part_id"])
    op.create_index("ix_organizer_compartments_organizer_id", "organizer_compartments", ["organizer_id"])

    op.create_table(
        "reservations",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("part_id", sa.String(length=36), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["part_id"], ["parts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "part_id", name="uq_project_part_reservation"),
    )
    op.create_index("ix_reservations_status", "reservations", ["status"])
    op.create_index("ix_reservations_part_id", "reservations", ["part_id"])
    op.create_index("ix_reservations_project_id", "reservations", ["project_id"])

    op.create_table(
        "supplier_parts",
        sa.Column("part_id", sa.String(length=36), nullable=False),
        sa.Column("supplier_id", sa.String(length=36), nullable=False),
        sa.Column("supplier_sku", sa.String(length=128), nullable=True),
        sa.Column("url", sa.String(length=512), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=True),
        sa.Column("stock", sa.Integer(), nullable=True),
        sa.Column("price_breaks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("datasheet_url", sa.String(length=512), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["part_id"], ["parts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_supplier_parts_part_id", "supplier_parts", ["part_id"])
    op.create_index("ix_supplier_parts_supplier_id", "supplier_parts", ["supplier_id"])
    op.create_index("ix_supplier_parts_supplier_sku", "supplier_parts", ["supplier_sku"])

    op.create_table(
        "bom_revisions",
        sa.Column("bom_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("comment", sa.String(length=512), nullable=True),
        sa.Column("items_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["bom_id"], ["boms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bom_revisions_bom_id", "bom_revisions", ["bom_id"])

    op.create_table(
        "bom_items",
        sa.Column("bom_id", sa.String(length=36), nullable=False),
        sa.Column("designator", sa.String(length=64), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("value", sa.String(length=128), nullable=True),
        sa.Column("footprint", sa.String(length=128), nullable=True),
        sa.Column("mpn", sa.String(length=128), nullable=True),
        sa.Column("manufacturer", sa.String(length=128), nullable=True),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("matched_part_id", sa.String(length=36), nullable=True),
        sa.Column("match_level", sa.String(length=16), nullable=True),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["bom_id"], ["boms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["matched_part_id"], ["parts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bom_items_bom_id", "bom_items", ["bom_id"])
    op.create_index("ix_bom_items_matched_part_id", "bom_items", ["matched_part_id"])
    op.create_index("ix_bom_items_designator", "bom_items", ["designator"])

    op.create_table(
        "shopping_list_items",
        sa.Column("shopping_list_id", sa.String(length=36), nullable=False),
        sa.Column("part_id", sa.String(length=36), nullable=True),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("supplier_part_id", sa.String(length=36), nullable=True),
        sa.Column("notes", sa.String(length=512), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["part_id"], ["parts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shopping_list_id"], ["shopping_lists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supplier_part_id"], ["supplier_parts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shopping_list_items_part_id", "shopping_list_items", ["part_id"])
    op.create_index("ix_shopping_list_items_shopping_list_id", "shopping_list_items", ["shopping_list_id"])

    op.create_table(
        "inventory_transactions",
        sa.Column("part_id", sa.String(length=36), nullable=False),
        sa.Column("location_id", sa.String(length=36), nullable=False),
        sa.Column("quantity_change", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=True),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("reservation_id", sa.String(length=36), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=True),
        sa.Column("notes", sa.String(length=512), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["part_id"], ["parts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reservation_id"], ["reservations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_transactions_location_id", "inventory_transactions", ["location_id"])
    op.create_index("ix_inventory_transactions_project_id", "inventory_transactions", ["project_id"])
    op.create_index("ix_inventory_transactions_part_id", "inventory_transactions", ["part_id"])
    op.create_index("ix_inventory_transactions_timestamp", "inventory_transactions", ["timestamp"])


def downgrade() -> None:
    op.drop_table("inventory_transactions")
    op.drop_table("shopping_list_items")
    op.drop_table("bom_items")
    op.drop_table("bom_revisions")
    op.drop_table("supplier_parts")
    op.drop_table("reservations")
    op.drop_table("organizer_compartments")
    op.drop_table("inventory_items")
    op.drop_table("esp32_devices")
    op.drop_table("boms")
    op.drop_table("api_keys")
    op.drop_table("users")
    op.drop_table("suppliers")
    op.drop_table("shopping_lists")
    op.drop_table("projects")
    op.drop_table("parts")
    op.drop_table("organizers")
    op.drop_table("locations")
    op.drop_table("attachments")
