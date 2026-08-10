from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModel


class InventoryLocation(BaseModel, Base):
    __tablename__ = "locations"

    name: Mapped[str] = mapped_column(String(128), index=True)
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), index=True
    )
    location_type: Mapped[str | None] = mapped_column(
        String(32), default="compartment"
    )  # rack | bin | compartment
    dimensions: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    notes: Mapped[str | None] = mapped_column(String(512))
    qr_code: Mapped[str | None] = mapped_column(String(256), unique=True)

    parent: Mapped["InventoryLocation | None"] = relationship(
        remote_side="InventoryLocation.id", back_populates="children"
    )
    children: Mapped[list["InventoryLocation"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )

    def full_path(self) -> str:
        parts: list[str] = []
        node: InventoryLocation | None = self
        seen: set[str] = set()
        while node is not None and node.id not in seen:
            seen.add(node.id)
            parts.append(node.name)
            node = node.parent
        return " / ".join(reversed(parts))
