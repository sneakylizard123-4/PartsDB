from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModel


class Reservation(BaseModel, Base):
    """Reserved stock for a project. Reduces available, not physical, inventory."""

    __tablename__ = "reservations"
    __table_args__ = (
        UniqueConstraint("project_id", "part_id", name="uq_project_part_reservation"),
    )

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    part_id: Mapped[str] = mapped_column(
        ForeignKey("parts.id", ondelete="CASCADE"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)

    project: Mapped["Project"] = relationship(back_populates="reservations")  # noqa: F821
    part: Mapped["Part"] = relationship()  # noqa: F821
