from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.inventory import InventoryItem
from app.models.transaction import InventoryTransaction


class StockError(ValueError):
    pass


def get_or_create_item(
    db: Session, part_id: str, location_id: str
) -> InventoryItem:
    item = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.part_id == part_id,
            InventoryItem.location_id == location_id,
        )
        .first()
    )
    if item is None:
        item = InventoryItem(part_id=part_id, location_id=location_id, quantity=0)
        db.add(item)
        db.flush()
    return item


def apply_transaction(
    db: Session,
    *,
    part_id: str,
    location_id: str,
    quantity_change: int,
    reason: str = "adjustment",
    project_id: str | None = None,
    reservation_id: str | None = None,
    source: str = "web",
    notes: str | None = None,
    timestamp: datetime | None = None,
    allow_negative: bool = False,
    tx_metadata: dict | None = None,
) -> InventoryTransaction:
    """Apply a quantity change and record an immutable transaction."""
    if quantity_change == 0:
        raise StockError("Quantity change must not be zero")

    item = get_or_create_item(db, part_id, location_id)
    new_qty = item.quantity + quantity_change
    if new_qty < 0 and not allow_negative:
        raise StockError(
            f"Insufficient stock: have {item.quantity}, tried to remove {-quantity_change}"
        )
    item.quantity = new_qty
    db.flush()

    tx = InventoryTransaction(
        part_id=part_id,
        location_id=location_id,
        quantity_change=quantity_change,
        reason=reason,
        project_id=project_id,
        reservation_id=reservation_id,
        source=source,
        notes=notes,
        timestamp=timestamp or datetime.now(timezone.utc),
        tx_metadata=tx_metadata or {},
    )
    db.add(tx)
    db.flush()
    return tx


def move_stock(
    db: Session,
    *,
    part_id: str,
    from_location_id: str,
    to_location_id: str,
    quantity: int,
    notes: str | None = None,
) -> tuple[InventoryTransaction, InventoryTransaction]:
    """Move stock between locations, recording a paired transaction pair."""
    if from_location_id == to_location_id:
        raise StockError("Source and destination locations are identical")
    if quantity <= 0:
        raise StockError("Quantity must be positive")

    apply_transaction(
        db,
        part_id=part_id,
        location_id=from_location_id,
        quantity_change=-quantity,
        reason="move",
        source="web",
        notes=notes,
    )
    tx_in = apply_transaction(
        db,
        part_id=part_id,
        location_id=to_location_id,
        quantity_change=quantity,
        reason="move",
        source="web",
        notes=notes,
    )
    return tx_in  # callers can query the pair if needed
