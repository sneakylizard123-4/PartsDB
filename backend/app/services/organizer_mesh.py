from pathlib import Path

from app.services.organizer_layout import PackResult, PackedCell
from app.services.stl import Mesh, Vec3


def build_organizer_mesh(
    outer_width: float,
    outer_depth: float,
    outer_height: float,
    wall_thickness: float,
    divider_thickness: float,
    pack: PackResult,
    floor_thickness: float = 1.6,
    features: dict[str, bool] | None = None,
) -> Mesh:
    mesh = Mesh()
    wt = wall_thickness
    inner_w = outer_width - 2 * wt
    inner_d = outer_depth - 2 * wt

    # Floor
    mesh.add_box(Vec3(0, 0, 0), Vec3(outer_width, outer_depth, floor_thickness))

    # Outer walls
    wall_h = outer_height - floor_thickness
    mesh.add_box(Vec3(0, 0, floor_thickness), Vec3(wt, outer_depth, wall_h))  # left
    mesh.add_box(
        Vec3(outer_width - wt, 0, floor_thickness),
        Vec3(wt, outer_depth, wall_h),
    )  # right
    mesh.add_box(
        Vec3(0, 0, floor_thickness), Vec3(outer_width, wt, wall_h)
    )  # front
    mesh.add_box(
        Vec3(0, outer_depth - wt, floor_thickness),
        Vec3(outer_width, wt, wall_h),
    )  # back

    # Group cells by row (shelf)
    rows: dict[int, list[PackedCell]] = {}
    for cell in pack.cells:
        rows.setdefault(cell.row, []).append(cell)

    # Horizontal dividers between shelves (span full interior width)
    shelf_boundaries = sorted({cell.y + cell.depth for cell in pack.cells})
    shelf_boundaries = [
        y for y in shelf_boundaries if y < inner_d
    ]
    for y in shelf_boundaries:
        mesh.add_box(
            Vec3(wt, wt + y - divider_thickness / 2, floor_thickness),
            Vec3(inner_w, divider_thickness, wall_h),
        )

    # Vertical dividers within each shelf, at cell boundaries
    for row_cells in rows.values():
        row_cells = sorted(row_cells, key=lambda c: c.x)
        row_y = min(c.y for c in row_cells)
        row_depth = max(c.y + c.depth for c in row_cells) - row_y
        xs = sorted({c.x for c in row_cells} | {c.x + c.width for c in row_cells})
        for x in xs[1:-1]:
            mesh.add_box(
                Vec3(wt + x - divider_thickness / 2, wt + row_y, floor_thickness),
                Vec3(divider_thickness, row_depth, wall_h),
            )

    features = features or {}
    if features.get("stackable"):
        _add_stacking_lips(mesh, outer_width, outer_depth, outer_height, wt)
    if features.get("wall_mount"):
        _add_wall_mount_plate(mesh, outer_width, outer_depth, outer_height)
    if features.get("qr"):
        _add_qr_pocket(mesh, outer_width, floor_thickness)

    return mesh


def _add_stacking_lips(
    mesh: Mesh,
    outer_width: float,
    outer_depth: float,
    outer_height: float,
    wall_thickness: float,
) -> None:
    lip_depth = 6.0
    lip_height = 3.0
    top = outer_height - lip_height
    span = outer_width - 2 * wall_thickness
    mesh.add_box(Vec3(wall_thickness, 0.0, top), Vec3(span, lip_depth, lip_height))
    mesh.add_box(
        Vec3(wall_thickness, outer_depth - lip_depth, top),
        Vec3(span, lip_depth, lip_height),
    )


def _add_wall_mount_plate(
    mesh: Mesh,
    outer_width: float,
    outer_depth: float,
    outer_height: float,
) -> None:
    plate_depth = 4.0
    plate_height = 3.0
    top = outer_height - plate_height
    mesh.add_box(
        Vec3(0.0, outer_depth, top),
        Vec3(outer_width, plate_depth, plate_height),
    )
    for frac in (0.25, 0.75):
        mesh.add_box(
            Vec3(outer_width * frac - 5.0, outer_depth + plate_depth, top),
            Vec3(10.0, 2.0, plate_height),
        )


def _add_qr_pocket(mesh: Mesh, outer_width: float, z: float) -> None:
    mesh.add_box(
        Vec3(outer_width - 26.0, -1.0, z + 2.0),
        Vec3(20.0, 1.0, 20.0),
    )


def write_organizer_stl(
    path: str | Path,
    outer_width: float,
    outer_depth: float,
    outer_height: float,
    wall_thickness: float,
    divider_thickness: float,
    pack: PackResult,
    features: dict[str, bool] | None = None,
) -> Path:
    mesh = build_organizer_mesh(
        outer_width=outer_width,
        outer_depth=outer_depth,
        outer_height=outer_height,
        wall_thickness=wall_thickness,
        divider_thickness=divider_thickness,
        pack=pack,
        features=features,
    )
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mesh.write_binary_stl(str(path))
    return path
