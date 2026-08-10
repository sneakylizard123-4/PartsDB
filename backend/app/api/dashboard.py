from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.bom import BOMItem
from app.models.inventory import InventoryItem
from app.models.location import InventoryLocation
from app.models.part import Part
from app.models.project import Project
from app.models.reservation import Reservation
from app.models.shopping import ShoppingList, ShoppingListItem
from app.models.transaction import InventoryTransaction
from app.models.user import User
from app.schemas import DashboardStats, ReservationOut, TransactionOut

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

    empty_storage = db.query(InventoryLocation).filter(
        ~InventoryLocation.id.in_(
            db.query(InventoryItem.location_id).distinct()
        )
    ).count()

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
        active_projects=active_projects,
        shopping_requirements=shopping_requirements or 0,
        recent_transactions=tx_out,
        unassigned_parts=unassigned,
        empty_storage=empty_storage,
        recent_reservations=res_out,
        total_quantity=total_quantity,
    )
