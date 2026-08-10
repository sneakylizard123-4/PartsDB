from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.bom import BOMItem
from app.models.part import Part


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def _value_matches(req: str | None, cand: str | None) -> bool:
    """Fuzzy value comparison: handles '10k', '10K', '10 kΩ', '10kΩ' variants."""
    r = _norm(req)
    c = _norm(cand)
    if not r or not c:
        return True
    if r == c:
        return True
    for ch in ["Ω", "ohm", " ", "±", "%"]:
        r = r.replace(ch, "")
        c = c.replace(ch, "")
    return r == c and r != ""


def match_bom_item(db: Session, item: BOMItem) -> list[dict]:
    """Find candidate parts for a BOM item, ranked by match level."""
    candidates: list[dict] = []

    def add(part: Part, level: str, reason: str) -> None:
        candidates.append(
            {
                "part_id": part.id,
                "internal_id": part.internal_id,
                "value": part.value,
                "package": part.package,
                "manufacturer": part.manufacturer,
                "mpn": part.mpn,
                "match_level": level,
                "reason": reason,
            }
        )

    if item.mpn:
        exact = (
            db.query(Part)
            .filter(
                or_(
                    Part.mpn == item.mpn,
                    Part.internal_id == item.mpn,
                    Part.lcsc_number == item.mpn,
                    Part.digikey_number == item.mpn,
                )
            )
            .all()
        )
        for p in exact:
            if not any(c["part_id"] == p.id for c in candidates):
                add(p, "exact", "Manufacturer part number matches")

    query = db.query(Part)
    if item.value:
        query = query.filter(Part.value.isnot(None))
    if item.manufacturer:
        query = query.filter(Part.manufacturer == item.manufacturer)
    if item.footprint:
        query = query.filter(Part.package.isnot(None))
    for p in query.limit(500):
        if any(c["part_id"] == p.id for c in candidates):
            continue
        score = 0
        reasons = []
        if item.value:
            if p.value and _value_matches(item.value, p.value):
                score += 2
                reasons.append("value")
            elif p.value:
                continue
            elif item.footprint and _norm(item.footprint) != _norm(p.package):
                continue
        if item.footprint and _norm(item.footprint) == _norm(p.package):
            score += 2
            reasons.append("package")
        elif item.footprint and p.package and _norm(item.footprint) in _norm(p.package):
            score += 1
            reasons.append("package(substring)")
        if item.manufacturer and _norm(item.manufacturer) == _norm(p.manufacturer):
            score += 1
            reasons.append("manufacturer")

        if score >= 4:
            add(p, "strong", f"Strong match ({', '.join(reasons)})")
        elif score >= 2:
            add(p, "compatible", f"Compatible ({', '.join(reasons)})")

    # dedupe by part
    seen: set[str] = set()
    deduped = []
    for c in candidates:
        if c["part_id"] in seen:
            continue
        seen.add(c["part_id"])
        deduped.append(c)
    return deduped
