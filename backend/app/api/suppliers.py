import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal, get_db
from app.deps import get_current_user
from app.models.attachment import Attachment
from app.models.location import InventoryLocation
from app.models.part import Part
from app.models.supplier import Supplier, SupplierPart
from app.models.user import User
from app.schemas import (
    PartOut,
    SupplierCandidateOut,
    SupplierCreate,
    SupplierImportRequest,
    SupplierOut,
)
from app.services.datasheets import DatasheetFetchError, datasheet_filename, fetch_datasheet
from app.services.inventory import StockError, apply_transaction
from app.services.part_ids import generate_internal_id
from app.services.queries import enrich_part, load_part
from app.services.supplier_catalog import (
    SupplierUnavailableError,
    normalize_lcsc_id,
    supplier_lookup,
    supplier_search,
)

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


def _get_or_create_supplier(db: Session, name: str) -> Supplier:
    supplier = db.query(Supplier).filter(Supplier.name == name).first()
    if supplier is None:
        supplier = Supplier(name=name)
        db.add(supplier)
        db.flush()
    return supplier


def _save_datasheet(url: str | None, part_id: str) -> None:
    """Best-effort: download a datasheet and store it as an attachment."""
    if not url:
        return
    try:
        content, content_type = fetch_datasheet(url)
    except DatasheetFetchError:
        return
    mime = content_type.split(";")[0].strip().lower() or "application/octet-stream"
    if mime.startswith("text/"):
        return  # error page or HTML redirect, not a datasheet
    filename = datasheet_filename(url, part_id)
    if "pdf" in mime and not filename.lower().endswith(".pdf"):
        filename = f"{Path(filename).stem}.pdf"
    settings = get_settings()
    directory = settings.attachments_path
    directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{filename}"
    (directory / stored_name).write_bytes(content)
    attachment = Attachment(
        entity_type="part",
        entity_id=part_id,
        filename=filename,
        stored_name=stored_name,
        mime_type=mime,
        size=len(content),
        kind="datasheet" if "pdf" in mime else "file",
        source_url=url,
    )
    db = SessionLocal()
    try:
        db.add(attachment)
        db.commit()
    finally:
        db.close()


@router.get("", response_model=list[SupplierOut])
def list_suppliers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Supplier).order_by(Supplier.name.asc()).all()


@router.post("", response_model=SupplierOut, status_code=201)
def create_supplier(
    body: SupplierCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if db.query(Supplier).filter(Supplier.name == body.name).first():
        raise HTTPException(status_code=409, detail="Supplier already exists")
    supplier = Supplier(**body.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(
    supplier_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    db.delete(supplier)
    db.commit()


@router.get("/lookup", response_model=list[SupplierCandidateOut])
def lookup_products(
    source: str,
    q: str,
    user: User = Depends(get_current_user),
):
    """Search a supplier catalog by keyword or part number."""
    source = (source or "").strip().lower()
    query = (q or "").strip()
    if source == "lcsc":
        lcsc_id = normalize_lcsc_id(query)
        if lcsc_id:
            try:
                return [supplier_lookup(source, lcsc_id).to_dict()]
            except SupplierUnavailableError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
    try:
        candidates = supplier_search(source, query)
    except SupplierUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not candidates:
        try:
            candidates = [supplier_lookup(source, query)]
        except SupplierUnavailableError:
            return []
    return [c.to_dict() for c in candidates]


@router.post("/import", response_model=PartOut)
def import_product(
    body: SupplierImportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    response: Response = None,  # type: ignore[assignment]
):
    """Create a part from a supplier catalog lookup (or attach the supplier
    link when the part already exists)."""
    response.status_code = 201
    try:
        candidate = supplier_lookup(body.source, body.part_number)
    except SupplierUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    source = (body.source or "").strip().lower()
    supplier = _get_or_create_supplier(db, "LCSC" if source == "lcsc" else "DigiKey")

    existing = None
    if source == "lcsc":
        existing = (
            db.query(Part)
            .filter(Part.lcsc_number == candidate.part_number)
            .first()
        )
    elif source == "digikey":
        existing = (
            db.query(Part)
            .filter(Part.digikey_number == candidate.part_number)
            .first()
        )

    if existing is not None:
        link = (
            db.query(SupplierPart)
            .filter(
                SupplierPart.part_id == existing.id,
                SupplierPart.supplier_id == supplier.id,
            )
            .first()
        )
        if link is None:
            db.add(
                SupplierPart(
                    part_id=existing.id,
                    supplier_id=supplier.id,
                    supplier_sku=candidate.part_number,
                    url=candidate.url,
                    price=candidate.price,
                    currency=candidate.currency,
                    stock=candidate.stock,
                )
            )
            db.commit()
        return enrich_part(db, load_part(db, existing.id))

    part = Part(
        manufacturer=candidate.manufacturer,
        mpn=candidate.mpn,
        lcsc_number=candidate.part_number if source == "lcsc" else None,
        digikey_number=candidate.part_number if source == "digikey" else None,
        value=candidate.value,
        package=candidate.package,
        category=candidate.category,
        description=candidate.description,
        msl=candidate.msl,
        datasheet_url=candidate.datasheet_url,
        other_specs=candidate.specs,
    )
    part.internal_id = generate_internal_id(db, part.category)
    db.add(part)
    db.flush()

    db.add(
        SupplierPart(
            part_id=part.id,
            supplier_id=supplier.id,
            supplier_sku=candidate.part_number,
            url=candidate.url,
            price=candidate.price,
            currency=candidate.currency,
            stock=candidate.stock,
        )
    )

    if body.quantity and body.location_id:
        location = db.get(InventoryLocation, body.location_id)
        if location is None:
            db.rollback()
            raise HTTPException(status_code=404, detail="Location not found")
        try:
            apply_transaction(
                db,
                part_id=part.id,
                location_id=location.id,
                quantity_change=body.quantity,
                reason="import",
                source="web",
                notes=f"Imported from {candidate.source} ({candidate.part_number})",
            )
        except StockError as exc:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    db.refresh(part)
    _save_datasheet(candidate.datasheet_url, part.id)
    return enrich_part(db, load_part(db, part.id))


@router.get("/{supplier_id}/parts")
def supplier_parts(
    supplier_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if db.get(Supplier, supplier_id) is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return [
        {
            "id": sp.id,
            "part_id": sp.part_id,
            "internal_id": sp.part.internal_id,
            "value": sp.part.value,
            "supplier_sku": sp.supplier_sku,
            "price": sp.price,
            "currency": sp.currency,
            "stock": sp.stock,
        }
        for sp in db.query(SupplierPart).filter(SupplierPart.supplier_id == supplier_id).all()
    ]
