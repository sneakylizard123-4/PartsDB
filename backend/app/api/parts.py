from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app.models.inventory import InventoryItem
from app.models.part import Part
from app.models.supplier import SupplierPart
from app.models.user import User
from app.schemas import (
    Page,
    PartCreate,
    PartFacets,
    PartOut,
    PartUpdate,
    SupplierPartCreate,
    SupplierPartOut,
)
from app.services.part_ids import generate_internal_id
from app.services.queries import (
    apply_part_filters,
    enrich_part,
    load_part,
    order_parts,
    reserved_sums,
)

router = APIRouter(prefix="/api/parts", tags=["parts"])


def _apply_update(part: Part, data: dict) -> None:
    for field, value in data.items():
        if value is not None or field in ("other_specs", "notes", "description"):
            setattr(part, field, value)


def _order_query(query, sort_by: str):
    if sort_by == "internal_id":
        return query.order_by(Part.internal_id.asc())
    if sort_by == "value":
        return query.order_by(Part.value.asc())
    if sort_by == "manufacturer":
        return query.order_by(Part.manufacturer.asc())
    return query.order_by(Part.created_at.desc())


@router.get("", response_model=Page[PartOut])
def list_parts(
    q: str | None = Query(default=None, description="Search term"),
    category: str | None = None,
    package: str | None = None,
    manufacturer: str | None = None,
    location_id: str | None = None,
    storage_status: str | None = None,
    stock_status: str | None = Query(
        default=None, description="in_stock | low | out | reserved"
    ),
    low_stock_only: bool = False,
    unassigned_only: bool = False,
    min_qty: int | None = Query(default=None, ge=0),
    max_qty: int | None = Query(default=None, ge=0),
    min_voltage: float | None = None,
    max_voltage: float | None = None,
    min_current: float | None = None,
    max_current: float | None = None,
    tolerance: str | None = None,
    msl: str | None = None,
    specs: list[str] | None = Query(
        default=None, description="Parametric spec filters as key:value"
    ),
    sort_by: str = Query(default="created_desc"),
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
                Part.notes.ilike(like),
            )
        )
    if category:
        query = query.filter(Part.category == category)
    if package:
        query = query.filter(Part.package == package)
    if manufacturer:
        query = query.filter(Part.manufacturer == manufacturer)
    if location_id:
        query = query.filter(
            Part.inventory_items.any(InventoryItem.location_id == location_id)
        )
    if unassigned_only and not storage_status:
        storage_status = "unassigned"
    if storage_status:
        query = query.filter(Part.storage_status == storage_status)
    for spec in specs or []:
        key, _, value = spec.partition(":")
        if not key:
            continue
        column = Part.other_specs[key].astext
        query = query.filter(column.ilike(f"%{value}%"))

    if low_stock_only and not stock_status:
        stock_status = "low"

    derived = any(
        value is not None
        for value in (
            stock_status,
            min_qty,
            max_qty,
            min_voltage,
            max_voltage,
            min_current,
            max_current,
            tolerance,
            msl,
        )
    )

    if derived:
        candidates = query.all()
        reserved = reserved_sums(db, [p.id for p in candidates])
        filtered = apply_part_filters(
            candidates,
            reserved,
            stock_status=stock_status,
            min_qty=min_qty,
            max_qty=max_qty,
            min_voltage=min_voltage,
            max_voltage=max_voltage,
            min_current=min_current,
            max_current=max_current,
            tolerance=tolerance,
            msl=msl,
        )
        total = len(filtered)
        items = order_parts(filtered, sort_by)[offset : offset + limit]
    else:
        total = query.count()
        items = (
            _order_query(query, sort_by).limit(limit).offset(offset).all()
        )

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


@router.get("/facets", response_model=PartFacets)
def part_facets(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    def distinct(column):
        rows = (
            db.query(column)
            .filter(column.isnot(None), column != "")
            .distinct()
            .order_by(column)
            .all()
        )
        return [row[0] for row in rows]

    return PartFacets(
        categories=distinct(Part.category),
        packages=distinct(Part.package),
        manufacturers=distinct(Part.manufacturer),
        storage_statuses=distinct(Part.storage_status),
    )


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
