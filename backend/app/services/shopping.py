from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.inventory import InventoryItem
from app.models.part import Part
from app.models.project import Project
from app.models.reservation import Reservation
from app.models.shopping import ShoppingList, ShoppingListItem


def part_available(db: Session, part_id: str) -> int:
    total = (
        db.query(InventoryItem.quantity)
        .filter(InventoryItem.part_id == part_id)
        .all()
    )
    stock = sum(q for (q,) in total)
    reserved = sum(
        r.quantity
        for r in db.query(Reservation)
        .filter(Reservation.part_id == part_id, Reservation.status == "active")
        .all()
    )
    return stock - reserved


def analyze_requirements(db: Session, project: Project) -> dict:
    """Aggregate BOM needs multiplied by build_qty, with stock analysis."""
    needs: dict[str, dict] = defaultdict(
        lambda: {
            "required": 0,
            "available": 0,
            "reserved": 0,
            "missing": 0,
            "part": None,
            "items": [],
        }
    )
    for bom in project.boms:
        for item in bom.items:
            key = item.matched_part_id or f"raw:{item.mpn or item.value}:{item.footprint}"
            bucket = needs[key]
            bucket["required"] += item.qty * project.build_qty
            bucket["items"].append(
                {"id": item.id, "designator": item.designator, "qty": item.qty}
            )
            if item.matched_part_id:
                bucket["part"] = {
                    "id": item.matched_part.id,
                    "internal_id": item.matched_part.internal_id,
                    "value": item.matched_part.value,
                    "package": item.matched_part.package,
                    "mpn": item.matched_part.mpn,
                }
                bucket["available"] = part_available(db, item.matched_part_id)

    reserved_counts: dict[str, int] = {}
    for r in (
        db.query(Reservation)
        .filter(Reservation.project_id == project.id, Reservation.status == "active")
        .all()
    ):
        reserved_counts[r.part_id] = reserved_counts.get(r.part_id, 0) + r.quantity

    result = []
    for key, bucket in needs.items():
        required = bucket["required"]
        available = bucket["available"]
        if bucket["part"]:
            available -= reserved_counts.get(bucket["part"]["id"], 0)
        missing = max(0, required - available)
        result.append(
            {
                "part": bucket["part"],
                "required": required,
                "available": max(0, available),
                "reserved": reserved_counts.get(
                    bucket["part"]["id"] if bucket["part"] else "", 0
                ),
                "missing": missing,
                "items": bucket["items"],
            }
        )
    result.sort(key=lambda r: (r["missing"] == 0, r["part"]["internal_id"] if r["part"] else r["items"][0]["designator"]))
    return {"project": {"id": project.id, "name": project.name, "build_qty": project.build_qty}, "requirements": result}


def generate_shopping_list(db: Session, project: Project | None = None) -> ShoppingList:
    """Create a shopping list from project requirements and low-stock parts."""
    shopping_list = ShoppingList(name=f"Shopping List {project.name}" if project else "Shopping List")
    db.add(shopping_list)
    db.flush()

    if project:
        analysis = analyze_requirements(db, project)
        for req in analysis["requirements"]:
            if req["missing"] <= 0:
                continue
            if req["part"]:
                db.add(
                    ShoppingListItem(
                        shopping_list_id=shopping_list.id,
                        part_id=req["part"]["id"],
                        quantity=req["missing"],
                        status="missing",
                        source="project",
                    )
                )
            else:
                db.add(
                    ShoppingListItem(
                        shopping_list_id=shopping_list.id,
                        description=" / ".join(
                            str(x) for x in [i["designator"] for i in req["items"]][:5]
                        )
                        or "Unmatched BOM item",
                        quantity=req["missing"],
                        status="missing",
                        source="project",
                    )
                )

    # Low-stock additions
    for p in db.query(Part).filter(Part.min_qty.isnot(None)).all():
        stock = sum(
            q
            for (q,) in db.query(InventoryItem.quantity)
            .filter(InventoryItem.part_id == p.id)
            .all()
        )
        if stock < p.min_qty:
            want = (p.desired_qty or p.reorder_qty or p.min_qty) - stock
            if want > 0 and not db.query(ShoppingListItem).filter(
                ShoppingListItem.shopping_list_id == shopping_list.id,
                ShoppingListItem.part_id == p.id,
            ).first():
                db.add(
                    ShoppingListItem(
                        shopping_list_id=shopping_list.id,
                        part_id=p.id,
                        quantity=want,
                        status="missing",
                        source="low-stock",
                    )
                )
    db.commit()
    return shopping_list
