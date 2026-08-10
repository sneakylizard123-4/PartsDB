from sqlalchemy.orm import Session, joinedload

from app.models.inventory import InventoryItem
from app.models.part import Part
from app.models.reservation import Reservation
from app.models.supplier import SupplierPart


def part_stats(db: Session, part: Part) -> dict:
    total = 0
    locations: list[dict] = []
    for item in part.inventory_items:
        total += item.quantity
        locations.append(
            {
                "location_id": item.location_id,
                "quantity": item.quantity,
                "path": item.location.full_path() if item.location else "",
            }
        )
    reserved = sum(
        r.quantity
        for r in db.query(Reservation)
        .filter(Reservation.part_id == part.id, Reservation.status == "active")
        .all()
    )
    available = total - reserved
    low_stock = bool(
        part.min_qty is not None and total < part.min_qty
    )
    return {
        "total_quantity": total,
        "reserved_quantity": reserved,
        "available_quantity": available,
        "low_stock": low_stock,
        "locations": locations,
    }


def load_part(db: Session, part_id: str) -> Part | None:
    return (
        db.query(Part)
        .options(
            joinedload(Part.supplier_parts).joinedload(SupplierPart.supplier),
            joinedload(Part.inventory_items).joinedload(InventoryItem.location),
        )
        .filter(Part.id == part_id)
        .first()
    )


def enrich_part(db: Session, part: Part) -> dict:
    stats = part_stats(db, part)
    supplier_parts = [
        {
            "id": sp.id,
            "supplier_id": sp.supplier_id,
            "supplier_name": sp.supplier.name if sp.supplier else None,
            "supplier_sku": sp.supplier_sku,
            "url": sp.url,
            "price": sp.price,
            "currency": sp.currency,
            "stock": sp.stock,
            "price_breaks": sp.price_breaks,
        }
        for sp in part.supplier_parts
    ]
    data = {
        "id": part.id,
        "internal_id": part.internal_id,
        "manufacturer": part.manufacturer,
        "mpn": part.mpn,
        "lcsc_number": part.lcsc_number,
        "digikey_number": part.digikey_number,
        "value": part.value,
        "package": part.package,
        "category": part.category,
        "description": part.description,
        "tolerance": part.tolerance,
        "voltage_rating": part.voltage_rating,
        "current_rating": part.current_rating,
        "msl": part.msl,
        "other_specs": part.other_specs,
        "datasheet_url": part.datasheet_url,
        "notes": part.notes,
        "min_qty": part.min_qty,
        "desired_qty": part.desired_qty,
        "reorder_qty": part.reorder_qty,
        "storage_status": part.storage_status,
        "created_at": part.created_at,
        "updated_at": part.updated_at,
        "supplier_parts": supplier_parts,
        **stats,
    }
    return data
