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
    BomItemMatch,
)
from app.services.bom_matching import match_bom_item

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
