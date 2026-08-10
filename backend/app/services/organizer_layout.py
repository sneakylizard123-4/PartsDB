from dataclasses import dataclass, field


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
