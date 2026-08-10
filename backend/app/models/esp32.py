from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModel


class ESP32Device(BaseModel, Base):
    __tablename__ = "esp32_devices"

    organizer_id: Mapped[str | None] = mapped_column(
        ForeignKey("organizers.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(128))
    api_key_hash: Mapped[str] = mapped_column(String(256), unique=True)
    firmware_version: Mapped[str | None] = mapped_column(String(32))
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    online: Mapped[bool] = mapped_column(Boolean, default=False)
    mac_address: Mapped[str | None] = mapped_column(String(32))

    organizer: Mapped["Organizer | None"] = relationship(  # noqa: F821
        back_populates="devices"
    )
