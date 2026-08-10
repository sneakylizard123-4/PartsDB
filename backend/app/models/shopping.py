from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import BaseModel


class ShoppingList(BaseModel, Base):
    __tablename__ = "shopping_lists"

    name: Mapped[str] = mapped_column(String(128), default="Shopping List")
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)

    items: Mapped[list["ShoppingListItem"]] = relationship(  # noqa: F821
        back_populates="shopping_list", cascade="all, delete-orphan"
    )


class ShoppingListItem(BaseModel, Base):
    __tablename__ = "shopping_list_items"

    shopping_list_id: Mapped[str] = mapped_column(
        ForeignKey("shopping_lists.id", ondelete="CASCADE"), index=True
    )
    part_id: Mapped[str | None] = mapped_column(
        ForeignKey("parts.id", ondelete="SET NULL"), index=True
    )
    description: Mapped[str | None] = mapped_column(String(256))
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="missing"
    )  # missing | available | reserved | purchased
    source: Mapped[str] = mapped_column(String(32), default="manual")
    supplier_part_id: Mapped[str | None] = mapped_column(
        ForeignKey("supplier_parts.id", ondelete="SET NULL")
    )
    notes: Mapped[str | None] = mapped_column(String(512))

    shopping_list: Mapped["ShoppingList"] = relationship(  # noqa: F821
        back_populates="items"
    )
    part: Mapped["Part | None"] = relationship()  # noqa: F821
    supplier_part: Mapped["SupplierPart | None"] = relationship()  # noqa: F821
