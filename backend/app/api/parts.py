from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app.models.part import Part
from app.models.supplier import SupplierPart
from app.models.user import User
from app.schemas import (
    Page,
    PartCreate,
    PartOut,
    PartUpdate,
    SupplierPartCreate,
    SupplierPartOut,
)
from app.services.part_ids import generate_internal_id
from app.services.queries import enrich_part, load_part

router = APIRouter(prefix="/api/parts", tags=["parts"])


def _apply_update(part: Part, data: dict) -> None:
    for field, value in data.items():
        if value is not None or field in ("other_specs", "notes", "description"):
            setattr(part, field, value)


@router.get("", response_model=Page[PartOut])
def list_parts(
    q: str | None = Query(default=None, description="Search term"),
    category: str | None = None,
    low_stock_only: bool = False,
    unassigned_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Part).options(
        joinedload(Part.supplier_parts).joinedload(SupplierPart.supplier),
        joinedload(Part.inventory_items),
    )

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Part.internal_id.ilike(like),
                Part.manufacturer.ilike(like),
                Part.mpn.ilike(like),
                Part.lcsc_number.ilike(like),
                Part.digikey_number.ilike(like),
                Part.value.ilike(like),
                Part.package.ilike(like),
                Part.category.ilike(like),
                Part.description.ilike(like),
            )
        )
    if category:
        query = query.filter(Part.category == category)
    if unassigned_only:
        query = query.filter(Part.storage_status == "unassigned")

    total = query.count()
    items = query.order_by(Part.created_at.desc()).limit(limit).offset(offset).all()

    if low_stock_only:
        items = [p for p in items if p.min_qty is not None]
        items = [
            p
            for p in items
            if sum(i.quantity for i in p.inventory_items) < p.min_qty
        ]

    return Page(
        items=[enrich_part(db, p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=PartOut, status_code=201)
def create_part(
    body: PartCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = body.model_dump()
    if not data.get("internal_id"):
        data["internal_id"] = generate_internal_id(db, data.get("category"))
    part = Part(**data)
    if part.internal_id and (
        db.query(Part).filter(Part.internal_id == part.internal_id).first()
    ):
        raise HTTPException(status_code=409, detail="Internal ID already exists")
    db.add(part)
    db.commit()
    db.refresh(part)
    return enrich_part(db, load_part(db, part.id))


@router.get("/{part_id}", response_model=PartOut)
def get_part(
    part_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    part = load_part(db, part_id)
    if part is None:
        raise HTTPException(status_code=404, detail="Part not found")
    return enrich_part(db, part)


@router.patch("/{part_id}", response_model=PartOut)
def update_part(
    part_id: str,
    body: PartUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    part = db.get(Part, part_id)
    if part is None:
        raise HTTPException(status_code=404, detail="Part not found")
    data = body.model_dump(exclude_unset=True)
    if "internal_id" in data and data["internal_id"]:
        existing = (
            db.query(Part)
            .filter(Part.internal_id == data["internal_id"], Part.id != part_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="Internal ID already exists")
    _apply_update(part, data)
    db.commit()
    db.refresh(part)
    return enrich_part(db, load_part(db, part.id))


@router.delete("/{part_id}", status_code=204)
def delete_part(
    part_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    part = db.get(Part, part_id)
    if part is None:
        raise HTTPException(status_code=404, detail="Part not found")
    db.delete(part)
    db.commit()


@router.post("/{part_id}/supplier-parts", response_model=SupplierPartOut, status_code=201)
def add_supplier_part(
    part_id: str,
    body: SupplierPartCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    part = db.get(Part, part_id)
    if part is None:
        raise HTTPException(status_code=404, detail="Part not found")
    sp = SupplierPart(part_id=part_id, **body.model_dump())
    db.add(sp)
    db.commit()
    db.refresh(sp)
    supplier = sp.supplier
    return SupplierPartOut(
        **SupplierPartOut.model_validate(sp).model_dump(),
        supplier_name=supplier.name if supplier else None,
    )
