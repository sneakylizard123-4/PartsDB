import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.bom import BOM, BOMItem, BOMRevision
from app.models.part import Part
from app.models.project import Project
from app.models.user import User
from app.schemas import (
    BOMCreate,
    BOMItemOut,
    BOMOut,
    BOMRevisionOut,
    BomItemMatch,
    BomMatchApprove,
    BomMatchCandidate,
    BomReviewItem,
    BomReviewResponse,
    BomRevisionDiff,
    BomRevisionDiffItem,
    BOMSnapshotItem,
)
from app.services.bom_matching import match_bom_item
from app.services.shopping import part_available

router = APIRouter(prefix="/api/boms", tags=["boms"])

STANDARD_COLUMNS = {
    "designator": ["designator", "reference", "ref", "reference designator", "device"],
    "value": ["value", "comment", "comment 2"],
    "footprint": ["footprint", "package", "package (smd)"],
    "mpn": ["mpn", "manufacturer part number", "part number", "partnumber", "part no"],
    "manufacturer": ["manufacturer", "mfr", "manuf"],
    "qty": ["qty", "quantity", "amount", "count"],
    "description": ["description", "desc"],
}

ALLOWED_FIELDS = {"designator", "value", "footprint", "mpn", "manufacturer", "qty", "description"}


def _sniff_mapping(headers: list[str]) -> dict[str, str]:
    lowered = [h.strip().lower() for h in headers]
    mapping: dict[str, str] = {}
    for field, aliases in STANDARD_COLUMNS.items():
        for i, h in enumerate(lowered):
            if h in aliases:
                mapping[field] = headers[i]
                break
    return mapping


class CsvPreviewResponse(BaseModel):
    headers: list[str]
    rows: list[dict]
    detected_mapping: dict[str, str]
    total_rows: int


class NormalizeRequest(BaseModel):
    rows: list[dict]
    mapping: dict[str, str]


class BomItemCreatePayload(BaseModel):
    designator: str
    qty: int = 1
    value: str | None = None
    footprint: str | None = None
    mpn: str | None = None
    manufacturer: str | None = None
    description: str | None = None


@router.post("/preview-csv", response_model=CsvPreviewResponse)
async def preview_csv(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    if not headers:
        raise HTTPException(status_code=400, detail="CSV has no columns")
    rows = []
    for row in reader:
        rows.append({k: (v or "").strip() for k, v in row.items() if k})
    if len(rows) > 50:
        preview_rows = rows[:50]
    else:
        preview_rows = rows
    return CsvPreviewResponse(
        headers=headers,
        rows=preview_rows,
        detected_mapping=_sniff_mapping(headers),
        total_rows=len(rows),
    )


@router.post("/normalize", response_model=list[BomItemCreatePayload])
def normalize_items(
    body: NormalizeRequest,
    user: User = Depends(get_current_user),
):
    """Convert CSV rows into BOM items using the provided column mapping."""
    invalid = set(body.mapping.keys()) - ALLOWED_FIELDS
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown fields: {invalid}")
    items: list[BomItemCreatePayload] = []
    for row in body.rows:
        def col(field: str) -> str | None:
            src = body.mapping.get(field)
            if not src:
                return None
            value = row.get(src)
            if value is None:
                return None
            value = str(value).strip()
            return value or None

        designator_raw = col("designator")
        qty_raw = col("qty")
        qty = 1
        try:
            if qty_raw:
                qty = int(float(qty_raw.replace(",", "")))
        except (ValueError, AttributeError):
            qty = 1
        items.append(
            BomItemCreatePayload(
                designator=designator_raw or f"ITEM{len(items) + 1}",
                qty=max(1, qty),
                value=col("value"),
                footprint=col("footprint"),
                mpn=col("mpn"),
                manufacturer=col("manufacturer"),
                description=col("description"),
            )
        )
    return items


@router.get("", response_model=list[BOMOut])
def list_boms(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(BOM).all()


@router.get("/reviews", response_model=BomReviewResponse)
def list_review_items(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """List BOM items with compatible (candidate) matches across all BOMs."""
    items = db.query(BOMItem).filter(BOMItem.match_level == "compatible").all()
    return _review_items(db, items)


@router.get("/{bom_id}", response_model=BOMOut)
def get_bom(
    bom_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bom = db.get(BOM, bom_id)
    if bom is None:
        raise HTTPException(status_code=404, detail="BOM not found")
    return bom


@router.get("/{bom_id}/reviews", response_model=BomReviewResponse)
def list_bom_review_items(
    bom_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List BOM items with compatible (candidate) matches for one BOM."""
    bom = db.get(BOM, bom_id)
    if bom is None:
        raise HTTPException(status_code=404, detail="BOM not found")
    items = (
        db.query(BOMItem)
        .filter(BOMItem.bom_id == bom_id, BOMItem.match_level == "compatible")
        .all()
    )
    return _review_items(db, items)


@router.get("/{bom_id}/revisions", response_model=list[BOMRevisionOut])
def list_revisions(
    bom_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bom = db.get(BOM, bom_id)
    if bom is None:
        raise HTTPException(status_code=404, detail="BOM not found")
    return (
        db.query(BOMRevision)
        .filter(BOMRevision.bom_id == bom_id)
        .order_by(BOMRevision.version.asc())
        .all()
    )


@router.get("/{bom_id}/revisions/diff", response_model=BomRevisionDiff)
def revision_diff(
    bom_id: str,
    from_id: str,
    to_id: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Compare two BOM revisions and report per-item changes with stock impact."""
    bom = db.get(BOM, bom_id)
    if bom is None:
        raise HTTPException(status_code=404, detail="BOM not found")
    revisions = (
        db.query(BOMRevision)
        .filter(BOMRevision.bom_id == bom_id)
        .order_by(BOMRevision.version.asc())
        .all()
    )
    rev_from = db.get(BOMRevision, from_id)
    if rev_from is None or rev_from.bom_id != bom_id:
        raise HTTPException(status_code=404, detail="From revision not found")
    if to_id:
        rev_to = db.get(BOMRevision, to_id)
        if rev_to is None or rev_to.bom_id != bom_id:
            raise HTTPException(status_code=404, detail="To revision not found")
    else:
        rev_to = revisions[-1] if revisions else rev_from
    if rev_to.version < rev_from.version:
        raise HTTPException(
            status_code=400, detail="to revision must not be older than from revision"
        )

    from_items = {_snap_key(i): i for i in rev_from.items_snapshot}
    to_items = {_snap_key(i): i for i in rev_to.items_snapshot}
    project = bom.project

    rows: list[BomRevisionDiffItem] = []
    for designator in sorted(set(from_items) | set(to_items)):
        f = from_items.get(designator)
        t = to_items.get(designator)
        if f is not None and t is not None:
            same = (
                int(f.get("qty") or 0) == int(t.get("qty") or 0)
                and f.get("value") == t.get("value")
                and f.get("footprint") == t.get("footprint")
                and f.get("mpn") == t.get("mpn")
                and f.get("manufacturer") == t.get("manufacturer")
            )
            status = "unchanged" if same else "changed"
            qty_change = int(t.get("qty") or 0) - int(f.get("qty") or 0)
        elif t is not None:
            status = "added"
            qty_change = int(t.get("qty") or 0)
        else:
            status = "removed"
            qty_change = -int(f.get("qty") or 0)
        needed = qty_change * project.build_qty

        current = next((i for i in bom.items if i.designator == designator), None)
        part_info, available = _diff_part(db, current)
        shortfall = (
            max(0, needed - available) if needed > 0 and available is not None else 0
        )
        rows.append(
            BomRevisionDiffItem(
                designator=designator,
                status=status,
                from_item=_snap_item(f) if f is not None else None,
                to_item=_snap_item(t) if t is not None else None,
                qty_change=qty_change,
                part=part_info,
                needed=needed,
                available=available,
                shortfall=shortfall,
            )
        )

    summary = {
        "added": sum(1 for r in rows if r.status == "added"),
        "removed": sum(1 for r in rows if r.status == "removed"),
        "changed": sum(1 for r in rows if r.status == "changed"),
        "unchanged": sum(1 for r in rows if r.status == "unchanged"),
        "total_shortfall": sum(r.shortfall for r in rows),
    }
    return BomRevisionDiff(
        bom_id=bom.id,
        bom_name=bom.name,
        project_id=project.id,
        build_qty=project.build_qty,
        from_revision=rev_from,
        to_revision=rev_to,
        items=rows,
        summary=summary,
    )


@router.post("", response_model=BOMOut, status_code=201)
def create_bom(
    body: BOMCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = db.get(Project, body.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    bom = BOM(project_id=body.project_id, name=body.name, description=body.description)
    db.add(bom)
    db.commit()
    db.refresh(bom)
    _create_revision(db, bom, [], comment="Initial")
    return bom


@router.post("/{bom_id}/items", response_model=BOMOut, status_code=201)
def add_items(
    bom_id: str,
    body: list[BomItemCreatePayload],
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bom = db.get(BOM, bom_id)
    if bom is None:
        raise HTTPException(status_code=404, detail="BOM not found")
    for item in body:
        db.add(BOMItem(bom_id=bom_id, **item.model_dump()))
    db.flush()
    db.refresh(bom)
    items = list(bom.items)
    _create_revision(db, bom, items, comment=f"Added {len(body)} items")
    db.commit()
    db.refresh(bom)
    return bom


@router.post("/{bom_id}/match", response_model=list[BomItemMatch])
def match_bom(
    bom_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bom = db.get(BOM, bom_id)
    if bom is None:
        raise HTTPException(status_code=404, detail="BOM not found")
    matches = []
    for item in bom.items:
        candidates = match_bom_item(db, item)
        if not candidates:
            item.match_level = "none"
            continue
        best = candidates[0]
        item.matched_part_id = best["part_id"]
        item.match_level = best["match_level"]
        matches.append(
            BomItemMatch(
                bom_item_id=item.id,
                part_id=best["part_id"],
                match_level=best["match_level"],
                reason=best["reason"],
            )
        )
    db.commit()
    return matches


@router.post("/{bom_id}/items/{item_id}/match", response_model=BOMItemOut)
def match_item(
    bom_id: str,
    item_id: str,
    body: BomItemMatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = db.get(BOMItem, item_id)
    if item is None or item.bom_id != bom_id:
        raise HTTPException(status_code=404, detail="BOM item not found")
    if db.get(Part, body.part_id) is None:
        raise HTTPException(status_code=404, detail="Part not found")
    item.matched_part_id = body.part_id
    item.match_level = body.match_level or "manual"
    db.commit()
    db.refresh(item)
    return item


@router.post("/{bom_id}/items/{item_id}/match/approve", response_model=BOMItemOut)
def approve_item_match(
    bom_id: str,
    item_id: str,
    body: BomMatchApprove,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Accept a candidate substitution, permanently linking the part to the item."""
    item = db.get(BOMItem, item_id)
    if item is None or item.bom_id != bom_id:
        raise HTTPException(status_code=404, detail="BOM item not found")
    if db.get(Part, body.part_id) is None:
        raise HTTPException(status_code=404, detail="Part not found")
    item.matched_part_id = body.part_id
    item.match_level = "manual"
    db.commit()
    db.refresh(item)
    return item


@router.post("/{bom_id}/items/{item_id}/match/reject", response_model=BOMItemOut)
def reject_item_match(
    bom_id: str,
    item_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Reject all substitutions for an item, marking it for manual part selection."""
    item = db.get(BOMItem, item_id)
    if item is None or item.bom_id != bom_id:
        raise HTTPException(status_code=404, detail="BOM item not found")
    item.matched_part_id = None
    item.match_level = "none"
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{bom_id}", status_code=204)
def delete_bom(
    bom_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bom = db.get(BOM, bom_id)
    if bom is None:
        raise HTTPException(status_code=404, detail="BOM not found")
    db.delete(bom)
    db.commit()


def _create_revision(db: Session, bom: BOM, items: list[BOMItem], comment: str) -> None:
    existing = db.query(BOMRevision).filter(BOMRevision.bom_id == bom.id).count()
    snapshot = [
        {
            "designator": i.designator,
            "qty": i.qty,
            "value": i.value,
            "footprint": i.footprint,
            "mpn": i.mpn,
            "manufacturer": i.manufacturer,
        }
        for i in items
    ]
    db.add(
        BOMRevision(
            bom_id=bom.id,
            version=existing + 1,
            comment=comment,
            items_snapshot=snapshot,
        )
    )


def _review_items(db: Session, items: list[BOMItem]) -> BomReviewResponse:
    result: list[BomReviewItem] = []
    for item in items:
        candidates = []
        for c in match_bom_item(db, item):
            candidates.append(
                BomMatchCandidate(
                    part_id=c["part_id"],
                    internal_id=c["internal_id"],
                    value=c["value"],
                    package=c["package"],
                    manufacturer=c["manufacturer"],
                    mpn=c["mpn"],
                    match_level=c["match_level"],
                    reason=c["reason"],
                    available_quantity=part_available(db, c["part_id"]),
                )
            )
        result.append(
            BomReviewItem(
                bom_id=item.bom_id,
                bom_name=item.bom.name,
                item_id=item.id,
                designator=item.designator,
                qty=item.qty,
                value=item.value,
                footprint=item.footprint,
                mpn=item.mpn,
                manufacturer=item.manufacturer,
                match_level=item.match_level,
                candidates=candidates,
            )
        )
    return BomReviewResponse(total=len(result), items=result)


def _snap_key(item: dict) -> str:
    return str(item.get("designator") or "")


def _snap_item(item: dict) -> BOMSnapshotItem:
    return BOMSnapshotItem(
        designator=_snap_key(item),
        qty=int(item.get("qty") or 0),
        value=item.get("value"),
        footprint=item.get("footprint"),
        mpn=item.get("mpn"),
        manufacturer=item.get("manufacturer"),
    )


def _diff_part(db: Session, item: BOMItem | None) -> tuple[dict | None, int | None]:
    if item is None:
        return None, None
    part = None
    if item.matched_part_id:
        part = db.get(Part, item.matched_part_id)
    else:
        candidates = match_bom_item(db, item)
        if candidates:
            part = db.get(Part, candidates[0]["part_id"])
    if part is None:
        return None, None
    return (
        {
            "id": part.id,
            "internal_id": part.internal_id,
            "value": part.value,
            "package": part.package,
            "manufacturer": part.manufacturer,
            "mpn": part.mpn,
        },
        part_available(db, part.id),
    )
