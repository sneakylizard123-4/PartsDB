from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app.models.bom import BOM, BOMItem
from app.models.inventory import InventoryItem
from app.models.location import InventoryLocation
from app.models.part import Part
from app.models.project import Project
from app.models.reservation import Reservation
from app.models.shopping import ShoppingList, ShoppingListItem
from app.models.transaction import InventoryTransaction
from app.models.user import User
from app.schemas import (
    DashboardStats,
    EmptyStorageLocationOut,
    MissingBomItemOut,
    ReservationOut,
    TransactionOut,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardStats)
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    total_parts = db.query(Part).count()

    low_stock = 0
    for p in db.query(Part).filter(Part.min_qty.isnot(None)).all():
        total = (
            db.query(func.coalesce(func.sum(InventoryItem.quantity), 0))
            .filter(InventoryItem.part_id == p.id)
            .scalar()
        )
        if total < p.min_qty:
            low_stock += 1

    missing_bom = (
        db.query(BOMItem)
        .filter(BOMItem.matched_part_id.is_(None), BOMItem.match_level.is_(None))
        .count()
    )

    missing_items = (
        db.query(BOMItem)
        .options(joinedload(BOMItem.bom).joinedload(BOM.project))
        .filter(BOMItem.matched_part_id.is_(None), BOMItem.match_level.is_(None))
        .order_by(BOMItem.created_at.desc())
        .limit(50)
        .all()
    )
    missing_bom_items = []
    for item in missing_items:
        bom = item.bom
        project = bom.project if bom else None
        build_qty = project.build_qty if project else 1
        needed = (item.qty or 0) * build_qty
        missing_bom_items.append(
            MissingBomItemOut(
                item_id=item.id,
                bom_id=bom.id if bom else item.bom_id,
                bom_name=bom.name if bom else item.bom_id,
                project_id=project.id if project else "",
                project_name=project.name if project else "",
                designator=item.designator,
                qty=item.qty or 0,
                needed=needed,
                available=0,
                shortfall=needed,
                value=item.value,
                footprint=item.footprint,
                mpn=item.mpn,
                manufacturer=item.manufacturer,
                matched_part_id=item.matched_part_id,
            )
        )

    active_projects = (
        db.query(Project).filter(Project.status == "active").count()
    )

    shopping_requirements = (
        db.query(
            func.coalesce(
                func.sum(ShoppingListItem.quantity), 0
            )
        )
        .join(ShoppingList, ShoppingListItem.shopping_list_id == ShoppingList.id)
        .filter(ShoppingList.status == "open")
        .scalar()
    )

    recent_txs = (
        db.query(InventoryTransaction)
        .order_by(InventoryTransaction.timestamp.desc())
        .limit(8)
        .all()
    )
    tx_out = []
    for t in recent_txs:
        out = TransactionOut.model_validate(t)
        out.part_value = t.part.value if t.part else None
        out.part_internal_id = t.part.internal_id if t.part else None
        out.location_path = t.location.full_path() if t.location else ""
        tx_out.append(out)

    unassigned = (
        db.query(Part).filter(Part.storage_status == "unassigned").count()
    )

    occupied_ids = db.query(InventoryItem.location_id).distinct()
    container_ids = db.query(InventoryLocation.parent_id).distinct()
    empty_locations = (
        db.query(InventoryLocation)
        .filter(
            ~InventoryLocation.id.in_(occupied_ids),
            ~InventoryLocation.id.in_(container_ids),
        )
        .all()
    )
    empty_storage = len(empty_locations)
    empty_locations.sort(key=lambda loc: loc.full_path())
    empty_storage_locations = [
        EmptyStorageLocationOut(
            id=loc.id,
            name=loc.name,
            full_path=loc.full_path(),
        )
        for loc in empty_locations[:5]
    ]

    recent_res = (
        db.query(Reservation)
        .filter(Reservation.status == "active")
        .order_by(Reservation.created_at.desc())
        .limit(5)
        .all()
    )
    res_out = []
    for r in recent_res:
        out = ReservationOut.model_validate(r)
        out.project_name = r.project.name if r.project else None
        out.part_value = r.part.value if r.part else None
        out.part_internal_id = r.part.internal_id if r.part else None
        res_out.append(out)

    total_quantity = (
        db.query(func.coalesce(func.sum(InventoryItem.quantity), 0)).scalar()
    )

    return DashboardStats(
        total_parts=total_parts,
        low_stock_parts=low_stock,
        missing_bom_components=missing_bom,
        missing_bom_items=missing_bom_items,
        active_projects=active_projects,
        shopping_requirements=shopping_requirements or 0,
        recent_transactions=tx_out,
        unassigned_parts=unassigned,
        empty_storage=empty_storage,
        empty_storage_count=empty_storage,
        empty_storage_locations=empty_storage_locations,
        recent_reservations=res_out,
        total_quantity=total_quantity,
    )
