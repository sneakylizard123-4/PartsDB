from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.bom import BOM
from app.models.location import InventoryLocation
from app.models.part import Part
from app.models.project import Project
from app.models.user import User
from app.schemas import SearchResult

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=list[SearchResult])
def search(
    q: str = Query(min_length=1),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    term = q.strip()
    if not term:
        return []
    like = f"%{term}%"
    results: list[SearchResult] = []

    parts = (
        db.query(Part)
        .filter(
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
        .limit(limit)
        .all()
    )
    for p in parts:
        total = sum(i.quantity for i in p.inventory_items)
        results.append(
            SearchResult(
                id=p.id,
                type="part",
                title=p.internal_id or p.value or p.mpn or "Part",
                subtitle=f"{p.value or ''} {p.package or ''}".strip() or p.description,
                location_path=", ".join(
                    i.location.full_path() for i in p.inventory_items if i.location
                )
                or None,
            )
        )

    locs = (
        db.query(InventoryLocation)
        .filter(
            or_(
                InventoryLocation.name.ilike(like),
                InventoryLocation.notes.ilike(like),
            )
        )
        .limit(limit)
        .all()
    )
    for loc in locs:
        results.append(
            SearchResult(
                id=loc.id,
                type="location",
                title=loc.name,
                subtitle=loc.location_type,
                location_path=loc.full_path(),
            )
        )

    projects = (
        db.query(Project)
        .filter(
            or_(
                Project.name.ilike(like),
                Project.description.ilike(like),
            )
        )
        .limit(limit)
        .all()
    )
    for pr in projects:
        results.append(
            SearchResult(
                id=pr.id, type="project", title=pr.name, subtitle=pr.description
            )
        )

    boms = db.query(BOM).filter(BOM.name.ilike(like)).limit(limit).all()
    for b in boms:
        results.append(
            SearchResult(
                id=b.id,
                type="bom",
                title=f"{b.name} ({b.project.name})",
                subtitle="BOM",
            )
        )

    order = {"part": 0, "location": 1, "project": 2, "bom": 3}
    results.sort(key=lambda r: (order.get(r.type, 9), r.title))
    return results[:limit]
