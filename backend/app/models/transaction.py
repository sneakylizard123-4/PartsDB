from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModel


class InventoryTransaction(BaseModel, Base):
    """Immutable record of an inventory quantity change."""

    __tablename__ = "inventory_transactions"

    part_id: Mapped[str] = mapped_column(
        ForeignKey("parts.id", ondelete="CASCADE"), index=True
    )
    location_id: Mapped[str] = mapped_column(
        ForeignKey("locations.id", ondelete="RESTRICT"), index=True
    )
    quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(64))  # restock | usage | ...
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), index=True
    )
    reservation_id: Mapped[str | None] = mapped_column(
        ForeignKey("reservations.id", ondelete="SET NULL")
    )
    source: Mapped[str | None] = mapped_column(String(32), default="web")
    notes: Mapped[str | None] = mapped_column(String(512))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    tx_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)

    part: Mapped["Part"] = relationship()  # noqa: F821
    location: Mapped["InventoryLocation"] = relationship()  # noqa: F821
    project: Mapped["Project | None"] = relationship()  # noqa: F821
