from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.inventory import InventoryItem
from app.models.location import InventoryLocation
from app.models.part import Part
from app.models.user import User
from app.schemas import InventoryAdjust, InventoryItemOut, MoveInventory
from app.services.inventory import StockError, apply_transaction, move_stock

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("", response_model=list[InventoryItemOut])
def list_inventory(
    part_id: str | None = Query(default=None),
    location_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(InventoryItem)
    if part_id:
        query = query.filter(InventoryItem.part_id == part_id)
    if location_id:
        query = query.filter(InventoryItem.location_id == location_id)
    items = query.order_by(InventoryItem.created_at.desc()).all()
    out = []
    for i in items:
        item = InventoryItemOut.model_validate(i)
        item.part_internal_id = i.part.internal_id
        item.part_value = i.part.value
        item.part_package = i.part.package
        item.part_manufacturer = i.part.manufacturer
        item.part_mpn = i.part.mpn
        item.location_path = i.location.full_path() if i.location else ""
        out.append(item)
    return out


@router.post("/adjust", status_code=201)
def adjust_inventory(
    body: InventoryAdjust,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if db.get(Part, body.part_id) is None:
        raise HTTPException(status_code=404, detail="Part not found")
    if db.get(InventoryLocation, body.location_id) is None:
        raise HTTPException(status_code=404, detail="Location not found")
    try:
        tx = apply_transaction(
            db,
            part_id=body.part_id,
            location_id=body.location_id,
            quantity_change=body.quantity_change,
            reason=body.reason,
            project_id=body.project_id,
            notes=body.notes,
            source=body.source,
        )
    except StockError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    db.commit()
    return {"ok": True, "transaction_id": tx.id, "quantity_change": tx.quantity_change}


@router.post("/move", status_code=201)
def move_inventory(
    body: MoveInventory,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if db.get(Part, body.part_id) is None:
        raise HTTPException(status_code=404, detail="Part not found")
    if db.get(InventoryLocation, body.from_location_id) is None:
        raise HTTPException(status_code=404, detail="Source location not found")
    if db.get(InventoryLocation, body.to_location_id) is None:
        raise HTTPException(status_code=404, detail="Destination location not found")
    try:
        tx_in = move_stock(
            db,
            part_id=body.part_id,
            from_location_id=body.from_location_id,
            to_location_id=body.to_location_id,
            quantity=body.quantity,
            notes=body.notes,
        )
    except StockError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    db.commit()
    return {"ok": True, "moved": body.quantity, "transaction_id": tx_in.id}
