from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModel


class InventoryItem(BaseModel, Base):
    """Physical stock of a part in a location. Quantities are exact, in pieces."""

    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint("part_id", "location_id", name="uq_part_location"),
    )

    part_id: Mapped[str] = mapped_column(
        ForeignKey("parts.id", ondelete="CASCADE"), index=True
    )
    location_id: Mapped[str] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    part: Mapped["Part"] = relationship(back_populates="inventory_items")  # noqa: F821
    location: Mapped["InventoryLocation"] = relationship()  # noqa: F821
