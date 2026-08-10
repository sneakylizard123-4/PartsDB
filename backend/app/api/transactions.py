from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.transaction import InventoryTransaction
from app.models.user import User
from app.schemas import Page, TransactionOut

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=Page[TransactionOut])
def list_transactions(
    part_id: str | None = Query(default=None),
    location_id: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(InventoryTransaction)
    if part_id:
        query = query.filter(InventoryTransaction.part_id == part_id)
    if location_id:
        query = query.filter(InventoryTransaction.location_id == location_id)
    if project_id:
        query = query.filter(InventoryTransaction.project_id == project_id)
    total = query.count()
    txs = (
        query.order_by(InventoryTransaction.timestamp.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    items = []
    for t in txs:
        out = TransactionOut.model_validate(t)
        out.part_value = t.part.value if t.part else None
        out.part_internal_id = t.part.internal_id if t.part else None
        out.location_path = t.location.full_path() if t.location else ""
        items.append(out)
    return Page(items=items, total=total, limit=limit, offset=offset)
