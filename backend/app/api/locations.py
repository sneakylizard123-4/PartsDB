import io

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app.models.inventory import InventoryItem
from app.models.location import InventoryLocation
from app.models.organizer import OrganizerCompartment
from app.models.base import new_id
from app.models.user import User
from app.schemas import DrawerGridCreate, LocationCreate, LocationOut, LocationUpdate

router = APIRouter(prefix="/api/locations", tags=["locations"])


def _to_out(db: Session, loc: InventoryLocation) -> LocationOut:
    out = LocationOut(
        id=loc.id,
        name=loc.name,
        parent_id=loc.parent_id,
        location_type=loc.location_type,
        dimensions=loc.dimensions,
        notes=loc.notes,
        qr_code=loc.qr_code,
        created_at=loc.created_at,
    )
    out.full_path = loc.full_path()
    out.children_count = (
        db.query(InventoryLocation)
        .filter(InventoryLocation.parent_id == loc.id)
        .count()
    )
    return out


@router.get("", response_model=list[LocationOut])
def list_locations(
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(InventoryLocation).options(joinedload(InventoryLocation.parent))
    if q:
        like = f"%{q}%"
        query = query.filter(InventoryLocation.name.ilike(like))
    locs = query.order_by(InventoryLocation.created_at.asc()).all()
    return [_to_out(db, loc) for loc in locs]


@router.get("/tree")
def location_tree(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    locs = db.query(InventoryLocation).all()
    nodes = {
        loc.id: {
            "id": loc.id,
            "name": loc.name,
            "location_type": loc.location_type,
            "children": [],
        }
        for loc in locs
    }
    roots = []
    for loc in locs:
        node = nodes[loc.id]
        if loc.parent_id and loc.parent_id in nodes:
            nodes[loc.parent_id]["children"].append(node)
        else:
            roots.append(node)
    return roots


@router.post("", response_model=LocationOut, status_code=201)
def create_location(
    body: LocationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.parent_id and db.get(InventoryLocation, body.parent_id) is None:
        raise HTTPException(status_code=404, detail="Parent location not found")
    loc = InventoryLocation(**body.model_dump())
    loc.id = new_id()
    loc.qr_code = f"/locations/{loc.id}"
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return _to_out(db, loc)


def _cell_name(row: int, col: int) -> str:
    """Grid cell name: rows lettered A..Z, columns numbered 1..N.

    Example for a 4x4 grid: A1 A2 A3 A4, B1 ... D4.
    """
    return f"{chr(ord('A') + row)}{col + 1}"


@router.post("/grid", response_model=list[LocationOut], status_code=201)
def create_drawer_grid(
    body: DrawerGridCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a drawer location plus a rows×cols grid of compartment children."""
    if body.parent_id and db.get(InventoryLocation, body.parent_id) is None:
        raise HTTPException(status_code=404, detail="Parent location not found")

    drawer = InventoryLocation(
        name=body.name,
        parent_id=body.parent_id,
        location_type="drawer",
        dimensions={"rows": body.rows, "cols": body.cols, "cells": body.rows * body.cols},
        notes=body.notes,
    )
    drawer.id = new_id()
    drawer.qr_code = f"/locations/{drawer.id}"
    db.add(drawer)

    cells = []
    for row in range(body.rows):
        for col in range(body.cols):
            cell = InventoryLocation(
                name=_cell_name(row, col),
                parent_id=drawer.id,
                location_type="compartment",
                dimensions={"row": row, "col": col},
            )
            cell.id = new_id()
            cell.qr_code = f"/locations/{cell.id}"
            db.add(cell)
            cells.append(cell)

    db.commit()
    return [_to_out(db, c) for c in cells]


@router.get("/{location_id}", response_model=LocationOut)
def get_location(
    location_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    loc = db.get(InventoryLocation, location_id)
    if loc is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return _to_out(db, loc)


@router.get("/{location_id}/contents")
def get_location_contents(
    location_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    loc = db.get(InventoryLocation, location_id)
    if loc is None:
        raise HTTPException(status_code=404, detail="Location not found")
    items = (
        db.query(InventoryItem)
        .filter(InventoryItem.location_id == location_id)
        .all()
    )
    children = db.query(InventoryLocation).filter(InventoryLocation.parent_id == location_id).all()
    return {
        "location": _to_out(db, loc),
        "items": [
            {
                "id": i.id,
                "part_id": i.part_id,
                "quantity": i.quantity,
                "internal_id": i.part.internal_id,
                "value": i.part.value,
                "package": i.part.package,
                "manufacturer": i.part.manufacturer,
                "mpn": i.part.mpn,
            }
            for i in items
        ],
        "children": [_to_out(db, c) for c in children],
        "compartments": [
            {
                "id": c.id,
                "label": c.label,
                "part_id": c.part_id,
                "organizer_id": c.organizer_id,
            }
            for c in db.query(OrganizerCompartment)
            .filter(OrganizerCompartment.location_id == location_id)
            .all()
        ],
    }


@router.patch("/{location_id}", response_model=LocationOut)
def update_location(
    location_id: str,
    body: LocationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    loc = db.get(InventoryLocation, location_id)
    if loc is None:
        raise HTTPException(status_code=404, detail="Location not found")
    data = body.model_dump(exclude_unset=True)
    if "parent_id" in data and data["parent_id"] == location_id:
        raise HTTPException(status_code=400, detail="Cannot be its own parent")
    if data.get("parent_id") and db.get(InventoryLocation, data["parent_id"]) is None:
        raise HTTPException(status_code=404, detail="Parent location not found")
    for field, value in data.items():
        setattr(loc, field, value)
    db.commit()
    db.refresh(loc)
    return _to_out(db, loc)


@router.delete("/{location_id}", status_code=204)
def delete_location(
    location_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    loc = db.get(InventoryLocation, location_id)
    if loc is None:
        raise HTTPException(status_code=404, detail="Location not found")
    if loc.children:
        raise HTTPException(
            status_code=400,
            detail="Location has children. Delete or move them first.",
        )
    db.delete(loc)
    db.commit()


@router.get("/{location_id}/qr.png")
def location_qr(
    location_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    loc = db.get(InventoryLocation, location_id)
    if loc is None:
        raise HTTPException(status_code=404, detail="Location not found")
    content = loc.qr_code or f"/locations/{loc.id}"
    img = qrcode.make(content)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(
        content=buf.getvalue(),
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="qr-{loc.name}.png"'},
    )
