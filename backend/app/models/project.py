from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModel


class Project(BaseModel, Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str | None] = mapped_column(String(1024))
    build_qty: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)

    boms: Mapped[list["BOM"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    reservations: Mapped[list["Reservation"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    attachments: Mapped[list["Attachment"]] = relationship(  # noqa: F821
        back_populates="project",
        primaryjoin="and_(Attachment.entity_type=='project', "
        "foreign(Attachment.entity_id)==Project.id)",
        cascade="all, delete-orphan",
    )
