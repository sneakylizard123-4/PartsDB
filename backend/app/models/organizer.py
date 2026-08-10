from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModel


class Organizer(BaseModel, Base):
    __tablename__ = "organizers"

    name: Mapped[str] = mapped_column(String(128))
    outer_width: Mapped[float] = mapped_column(Float, nullable=False)
    outer_depth: Mapped[float] = mapped_column(Float, nullable=False)
    outer_height: Mapped[float] = mapped_column(Float, nullable=False)
    preset: Mapped[str | None] = mapped_column(String(64))
    wall_thickness: Mapped[float] = mapped_column(Float, default=1.2)
    divider_thickness: Mapped[float] = mapped_column(Float, default=1.2)
    clearance: Mapped[float] = mapped_column(Float, default=0.2)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    storage_status: Mapped[str] = mapped_column(
        String(16), default="designed"
    )  # designed | printed | installed
    stl_path: Mapped[str | None] = mapped_column(String(512))

    compartments: Mapped[list["OrganizerCompartment"]] = relationship(  # noqa: F821
        back_populates="organizer", cascade="all, delete-orphan"
    )
    devices: Mapped[list["ESP32Device"]] = relationship(  # noqa: F821
        back_populates="organizer"
    )


class OrganizerCompartment(BaseModel, Base):
    __tablename__ = "organizer_compartments"

    organizer_id: Mapped[str] = mapped_column(
        ForeignKey("organizers.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str | None] = mapped_column(String(64))
    row: Mapped[int] = mapped_column(Integer, default=0)
    col: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[float] = mapped_column(Float, nullable=False)
    depth: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False)
    part_id: Mapped[str | None] = mapped_column(
        ForeignKey("parts.id", ondelete="SET NULL"), index=True
    )
    location_id: Mapped[str | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), index=True
    )

    organizer: Mapped["Organizer"] = relationship(  # noqa: F821
        back_populates="compartments"
    )
    part: Mapped["Part | None"] = relationship()  # noqa: F821
    location: Mapped["InventoryLocation | None"] = relationship()  # noqa: F821
