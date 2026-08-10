from typing import Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModel


class BOM(BaseModel, Base):
    __tablename__ = "boms"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(128), default="BOM")
    description: Mapped[str | None] = mapped_column(String(512))

    project: Mapped["Project"] = relationship(back_populates="boms")  # noqa: F821
    revisions: Mapped[list["BOMRevision"]] = relationship(  # noqa: F821
        back_populates="bom", cascade="all, delete-orphan", order_by="BOMRevision.version"
    )
    items: Mapped[list["BOMItem"]] = relationship(  # noqa: F821
        back_populates="bom", cascade="all, delete-orphan"
    )


class BOMRevision(BaseModel, Base):
    __tablename__ = "bom_revisions"

    bom_id: Mapped[str] = mapped_column(
        ForeignKey("boms.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(String(512))
    items_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)

    bom: Mapped["BOM"] = relationship(back_populates="revisions")  # noqa: F821


class BOMItem(BaseModel, Base):
    __tablename__ = "bom_items"

    bom_id: Mapped[str] = mapped_column(
        ForeignKey("boms.id", ondelete="CASCADE"), index=True
    )
    designator: Mapped[str] = mapped_column(String(64), index=True)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    value: Mapped[str | None] = mapped_column(String(128))
    footprint: Mapped[str | None] = mapped_column(String(128))
    mpn: Mapped[str | None] = mapped_column(String(128))
    manufacturer: Mapped[str | None] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(String(512))
    matched_part_id: Mapped[str | None] = mapped_column(
        ForeignKey("parts.id", ondelete="SET NULL"), index=True
    )
    match_level: Mapped[str | None] = mapped_column(String(16))  # exact | strong | compatible | manual | none
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    bom: Mapped["BOM"] = relationship(back_populates="items")  # noqa: F821
    matched_part: Mapped["Part | None"] = relationship()  # noqa: F821
