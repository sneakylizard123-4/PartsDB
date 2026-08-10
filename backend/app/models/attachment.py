from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModel


class Attachment(BaseModel, Base):
    __tablename__ = "attachments"

    entity_type: Mapped[str] = mapped_column(String(16), index=True)  # part | project
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    filename: Mapped[str] = mapped_column(String(256))
    stored_name: Mapped[str] = mapped_column(String(256))
    mime_type: Mapped[str | None] = mapped_column(String(128))
    size: Mapped[int] = mapped_column(default=0)
    kind: Mapped[str] = mapped_column(String(16), default="file")  # file | image | datasheet
    source_url: Mapped[str | None] = mapped_column(String(512), index=True)

    part: Mapped["Part | None"] = relationship(  # noqa: F821
        back_populates="attachments",
        primaryjoin="and_(Attachment.entity_type=='part', "
        "foreign(Attachment.entity_id)==Part.id)",
        viewonly=True,
        overlaps="project",
    )
    project: Mapped["Project | None"] = relationship(  # noqa: F821
        back_populates="attachments",
        primaryjoin="and_(Attachment.entity_type=='project', "
        "foreign(Attachment.entity_id)==Project.id)",
        viewonly=True,
        overlaps="part",
    )
