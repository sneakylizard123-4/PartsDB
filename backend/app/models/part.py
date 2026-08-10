from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModel


class Part(BaseModel, Base):
    __tablename__ = "parts"

    internal_id: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)
    manufacturer: Mapped[str | None] = mapped_column(String(128), index=True)
    mpn: Mapped[str | None] = mapped_column(String(128), index=True)
    lcsc_number: Mapped[str | None] = mapped_column(String(64), index=True)
    digikey_number: Mapped[str | None] = mapped_column(String(64), index=True)

    value: Mapped[str | None] = mapped_column(String(128), index=True)
    package: Mapped[str | None] = mapped_column(String(64), index=True)
    category: Mapped[str | None] = mapped_column(String(64), index=True)
    description: Mapped[str | None] = mapped_column(Text)

    tolerance: Mapped[str | None] = mapped_column(String(64))
    voltage_rating: Mapped[str | None] = mapped_column(String(64))
    current_rating: Mapped[str | None] = mapped_column(String(64))
    other_specs: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    datasheet_url: Mapped[str | None] = mapped_column(String(512))
    notes: Mapped[str | None] = mapped_column(Text)

    min_qty: Mapped[int | None] = mapped_column(Integer, default=None)
    desired_qty: Mapped[int | None] = mapped_column(Integer, default=None)
    reorder_qty: Mapped[int | None] = mapped_column(Integer, default=None)

    storage_status: Mapped[str] = mapped_column(
        String(16), default="unassigned", index=True
    )  # unassigned | assigned | printed | installed

    supplier_parts: Mapped[list["SupplierPart"]] = relationship(  # noqa: F821
        back_populates="part", cascade="all, delete-orphan"
    )
    inventory_items: Mapped[list["InventoryItem"]] = relationship(  # noqa: F821
        back_populates="part", cascade="all, delete-orphan"
    )
    attachments: Mapped[list["Attachment"]] = relationship(  # noqa: F821
        back_populates="part",
        primaryjoin="and_(Attachment.entity_type=='part', "
        "foreign(Attachment.entity_id)==Part.id)",
        cascade="all, delete-orphan",
    )
