import re
from dataclasses import dataclass, field

_SMD_CODES = {
    "0201": (0.6, 0.3),
    "0402": (1.0, 0.5),
    "0603": (1.6, 0.8),
    "0805": (2.0, 1.25),
    "1206": (3.2, 1.6),
    "1210": (3.2, 2.5),
    "1812": (4.5, 3.2),
    "2010": (5.0, 2.5),
    "2512": (6.3, 3.2),
}


@dataclass
class CompartmentSpec:
    label: str | None = None
    part_id: str | None = None
    width: float | None = None
    depth: float | None = None
    height: float | None = None


@dataclass
class PackedCell:
    row: int
    col: int
    x: float
    y: float
    width: float
    depth: float
    height: float
    label: str | None = None
    part_id: str | None = None


@dataclass
class PackResult:
    cells: list[PackedCell] = field(default_factory=list)
    used_width: float = 0.0
    used_depth: float = 0.0
    rows: int = 0
    error: str | None = None


@dataclass
class _Shelf:
    y: float
    cells: list[PackedCell] = field(default_factory=list)
    used_width: float = 0.0
    depth: float = 0.0


def pack_compartments(
    inner_width: float,
    inner_depth: float,
    divider_thickness: float,
    compartments: list[CompartmentSpec],
    default_size: float = 30.0,
    default_height: float = 20.0,
) -> PackResult:
    """Greedy shelf-packing of variable-size compartments.

    Cells are placed left-to-right (X) in shelves; shelves stack along depth
    (Y). Each shelf's depth is the max depth of its cells. Compartments with no
    explicit size get the default square size.
    """
    result = PackResult()
    if not compartments:
        return result

    specs: list[tuple[CompartmentSpec, float, float]] = []
    for c in compartments:
        w = c.width or default_size
        d = c.depth or default_size
        if w <= 0 or d <= 0:
            result.error = "Compartment dimensions must be positive"
            return result
        specs.append((c, w, d))

    specs.sort(key=lambda s: -s[2])  # depth descending

    shelves: list[_Shelf] = []
    for spec, w, d in specs:
        placed = False
        for shelf in shelves:
            if (
                shelf.used_width + w <= inner_width
                and shelf.y + max(shelf.depth, d) <= inner_depth
            ):
                cell = PackedCell(
                    row=len(shelves) - 1,
                    col=len(shelf.cells),
                    x=shelf.used_width,
                    y=shelf.y,
                    width=w,
                    depth=d,
                    height=spec.height or default_height,
                    label=spec.label,
                    part_id=spec.part_id,
                )
                shelf.cells.append(cell)
                shelf.used_width += w
                shelf.depth = max(shelf.depth, d)
                placed = True
                break
        if not placed:
            new_y = 0.0
            if shelves:
                new_y = shelves[-1].y + shelves[-1].depth + divider_thickness
            if new_y + d > inner_depth:
                result.error = (
                    "Compartments do not fit within the requested dimensions "
                    f"(need more than {inner_depth:.1f}mm of depth)"
                )
                return result
            shelf = _Shelf(y=new_y)
            shelf.cells.append(
                PackedCell(
                    row=len(shelves),
                    col=0,
                    x=0,
                    y=new_y,
                    width=w,
                    depth=d,
                    height=spec.height or default_height,
                    label=spec.label,
                    part_id=spec.part_id,
                )
            )
            shelf.used_width = w
            shelf.depth = d
            shelves.append(shelf)

    for shelf in shelves:
        for cell in shelf.cells:
            result.cells.append(cell)
        result.used_width = max(result.used_width, shelf.used_width)
        result.used_depth = max(result.used_depth, shelf.y + shelf.depth)
    result.rows = len(shelves)
    return result


def _to_float(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _explicit_size(part) -> tuple[float, float, float] | None:
    specs = getattr(part, "other_specs", None)
    if not isinstance(specs, dict) or not specs:
        return None
    raw = specs.get("size")
    if isinstance(raw, (list, tuple)) and len(raw) >= 3:
        vals = [_to_float(x) for x in raw[:3]]
        if all(v and v > 0 for v in vals):
            return (vals[0], vals[1], vals[2])
    if isinstance(raw, dict):
        vals = [_to_float(raw.get(k)) for k in ("length", "width", "height")]
        if all(v and v > 0 for v in vals):
            return (vals[0], vals[1], vals[2])
    vals = [_to_float(specs.get(k)) for k in ("length", "width", "height")]
    if vals[0] and vals[1]:
        height = vals[2] if vals[2] and vals[2] > 0 else 5.0
        return (vals[0], vals[1], height)
    return None


def _package_footprint(package: str | None) -> tuple[float, float, float] | None:
    pkg = "" if package is None else str(package)
    p = "".join(ch for ch in pkg.upper() if ch.isalnum())

    if "SOT353" in p or "SC70" in p:
        return (2.2, 1.35, 1.1)
    if "SOT223" in p:
        return (6.5, 3.5, 1.8)
    if "SOT89" in p:
        return (4.5, 2.5, 1.5)
    if "SOT23" in p:
        return (3.0, 1.75, 1.2)
    if "TO220" in p:
        return (15.2, 10.4, 4.5)
    if "TO92" in p:
        return (4.5, 3.5, 4.5)

    m = re.search(r"DIP(\d+)", p)
    if m:
        n = int(m.group(1))
        length = 2.54 * (n / 2) + 2.54
        return (length, 7.5, 3.5)
    m = re.search(r"SOIC(\d+)", p)
    if m:
        width = 6.0 + (1.0 if int(m.group(1)) > 14 else 0.0)
        return (width, 5.0, 1.75)
    m = re.search(r"QFN(\d+)", p)
    if m:
        n = int(m.group(1))
        body = 4.0 if n <= 28 else 5.0 if n <= 32 else 6.0 if n <= 48 else 7.0
        return (body, body, 0.9)
    m = re.search(r"QFP(\d*)", p)
    if m:
        n = int(m.group(1)) if m.group(1) else 0
        body = 7.0 if n <= 48 else 10.0 if n <= 80 else 14.0
        return (body, body, 1.6)

    m = re.search(r"(?<!\d)(\d{4})(?!\d)", p)
    if m:
        code = m.group(1)
        if code in _SMD_CODES:
            w, d = _SMD_CODES[code]
            return (w, d, 1.6)
        w = int(code[:2]) * 0.254
        d = int(code[2:]) * 0.254
        return (round(w, 1), round(d, 1), 1.6)

    return None


def size_for_part(part) -> tuple[float, float, float]:
    """Suggested compartment size (mm) for a part: (width, depth, height).

    Uses explicit dimensions from part.other_specs when present, otherwise
    heuristics from the package string. Applies a clearance multiplier and
    wall padding so the part fits comfortably.
    """
    explicit = _explicit_size(part)
    package = getattr(part, "package", None)
    w, d, h = explicit or _package_footprint(package) or (12.0, 12.0, 10.0)
    cw = round(w * 1.4 + 2.0, 1)
    cd = round(d * 1.4 + 2.0, 1)
    ch = round(h * 1.5 + 2.0, 1)
    return (cw, cd, ch)
