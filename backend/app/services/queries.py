import re

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.inventory import InventoryItem
from app.models.part import Part
from app.models.reservation import Reservation
from app.models.supplier import SupplierPart

_QUANTITY_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*([pnuµmkKMGT]?)")
_SI_SUFFIX = {
    "p": 1e-12,
    "n": 1e-9,
    "u": 1e-6,
    "µ": 1e-6,
    "m": 1e-3,
    "k": 1e3,
    "K": 1e3,
    "M": 1e6,
    "G": 1e9,
    "T": 1e12,
}


def parse_quantity(text: str | None) -> float | None:
    if not text:
        return None
    match = _QUANTITY_RE.search(text)
    if not match:
        return None
    return float(match.group(1)) * _SI_SUFFIX.get(match.group(2), 1.0)


def part_on_hand(part: Part) -> int:
    return sum(item.quantity for item in part.inventory_items)


def stock_status_of(total: int, reserved: int, min_qty: int | None) -> str:
    if total <= 0:
        return "out"
    if min_qty is not None and total < min_qty:
        return "low"
    if total - reserved <= 0:
        return "reserved"
    return "in_stock"


def reserved_sums(db: Session, part_ids: list[str]) -> dict[str, int]:
    if not part_ids:
        return {}
    rows = (
        db.query(Reservation.part_id, func.coalesce(func.sum(Reservation.quantity), 0))
        .filter(Reservation.part_id.in_(part_ids), Reservation.status == "active")
        .group_by(Reservation.part_id)
        .all()
    )
    return {part_id: int(quantity) for part_id, quantity in rows}


def apply_part_filters(
    parts: list[Part],
    reserved_by_part: dict[str, int],
    *,
    stock_status: str | None = None,
    min_qty: int | None = None,
    max_qty: int | None = None,
    min_voltage: float | None = None,
    max_voltage: float | None = None,
    min_current: float | None = None,
    max_current: float | None = None,
    tolerance: str | None = None,
    msl: str | None = None,
) -> list[Part]:
    result: list[Part] = []
    for part in parts:
        total = part_on_hand(part)
        if stock_status and (
            stock_status_of(total, reserved_by_part.get(part.id, 0), part.min_qty)
            != stock_status
        ):
            continue
        if min_qty is not None and total < min_qty:
            continue
        if max_qty is not None and total > max_qty:
            continue
        if min_voltage is not None:
            voltage = parse_quantity(part.voltage_rating)
            if voltage is None or voltage < min_voltage:
                continue
        if max_voltage is not None:
            voltage = parse_quantity(part.voltage_rating)
            if voltage is None or voltage > max_voltage:
                continue
        if min_current is not None:
            current = parse_quantity(part.current_rating)
            if current is None or current < min_current:
                continue
        if max_current is not None:
            current = parse_quantity(part.current_rating)
            if current is None or current > max_current:
                continue
        if tolerance and (
            not part.tolerance or tolerance.lower() not in part.tolerance.lower()
        ):
            continue
        if msl and part.msl != msl:
            continue
        result.append(part)
    return result


def order_parts(parts: list[Part], sort_by: str) -> list[Part]:
    if sort_by == "internal_id":
        parts.sort(key=lambda p: (p.internal_id or "").lower())
    elif sort_by == "value":
        parts.sort(key=lambda p: (p.value or "").lower())
    elif sort_by == "manufacturer":
        parts.sort(key=lambda p: (p.manufacturer or "").lower())
    else:
        parts.sort(key=lambda p: p.created_at, reverse=True)
    return parts


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
