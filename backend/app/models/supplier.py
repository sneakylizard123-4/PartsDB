from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModel


class Supplier(BaseModel, Base):
    __tablename__ = "suppliers"

    name: Mapped[str] = mapped_column(String(128), unique=True)
    website: Mapped[str | None] = mapped_column(String(512))
    notes: Mapped[str | None] = mapped_column(String(512))

    parts: Mapped[list["SupplierPart"]] = relationship(  # noqa: F821
        back_populates="supplier", cascade="all, delete-orphan"
    )


class SupplierPart(BaseModel, Base):
    __tablename__ = "supplier_parts"

    part_id: Mapped[str] = mapped_column(
        ForeignKey("parts.id", ondelete="CASCADE"), index=True
    )
    supplier_id: Mapped[str] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"), index=True
    )
    supplier_sku: Mapped[str | None] = mapped_column(String(128), index=True)
    url: Mapped[str | None] = mapped_column(String(512))
    price: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str | None] = mapped_column(String(8), default="USD")
    stock: Mapped[int | None] = mapped_column(Integer)
    price_breaks: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    description: Mapped[str | None] = mapped_column(String(512))
    datasheet_url: Mapped[str | None] = mapped_column(String(512))

    part: Mapped["Part"] = relationship(back_populates="supplier_parts")  # noqa: F821
    supplier: Mapped["Supplier"] = relationship(back_populates="parts")  # noqa: F821
