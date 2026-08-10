from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models.organizer import Organizer, OrganizerCompartment
from app.models.part import Part
from app.models.user import User
from app.schemas import CompartmentOut, OrganizerGenerate, OrganizerOut
from app.services.organizer_layout import CompartmentSpec, pack_compartments
from app.services.organizer_mesh import write_organizer_stl

router = APIRouter(prefix="/api/organizers", tags=["organizers"])

PRESETS = {
    "small-smd": {
        "name": "Small SMD",
        "outer_width": 100,
        "outer_depth": 80,
        "outer_height": 12,
        "default_size": 12,
        "wall_thickness": 1.2,
        "divider_thickness": 1.2,
    },
    "large-smd": {
        "name": "Large SMD",
        "outer_width": 120,
        "outer_depth": 90,
        "outer_height": 16,
        "default_size": 20,
        "wall_thickness": 1.2,
        "divider_thickness": 1.2,
    },
    "ics": {
        "name": "ICs",
        "outer_width": 120,
        "outer_depth": 100,
        "outer_height": 18,
        "default_size": 30,
        "wall_thickness": 1.4,
        "divider_thickness": 1.4,
    },
    "screws": {
        "name": "Screws",
        "outer_width": 140,
        "outer_depth": 110,
        "outer_height": 25,
        "default_size": 35,
        "wall_thickness": 1.6,
        "divider_thickness": 1.6,
    },
    "mixed": {
        "name": "Mixed",
        "outer_width": 120,
        "outer_depth": 100,
        "outer_height": 15,
        "default_size": 20,
        "wall_thickness": 1.2,
        "divider_thickness": 1.2,
    },
    "stackable-bin": {
        "name": "Stackable Bin",
        "outer_width": 160,
        "outer_depth": 120,
        "outer_height": 30,
        "default_size": 30,
        "wall_thickness": 1.6,
        "divider_thickness": 1.6,
    },
    "wall-mounted": {
        "name": "Wall-Mounted",
        "outer_width": 160,
        "outer_depth": 60,
        "outer_height": 25,
        "default_size": 25,
        "wall_thickness": 1.6,
        "divider_thickness": 1.6,
    },
}


def _to_out(db: Session, o: Organizer) -> OrganizerOut:
    out = OrganizerOut.model_validate(o)
    compartments = []
    for c in o.compartments:
        co = CompartmentOut.model_validate(c)
        co.part_value = c.part.value if c.part else None
        co.location_path = c.location.full_path() if c.location else ""
        compartments.append(co)
    out.compartments = compartments
    return out


@router.get("/presets")
def presets(user: User = Depends(get_current_user)):
    return PRESETS


@router.get("", response_model=list[OrganizerOut])
def list_organizers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [_to_out(db, o) for o in db.query(Organizer).order_by(Organizer.created_at.desc()).all()]


@router.get("/{organizer_id}", response_model=OrganizerOut)
def get_organizer(
    organizer_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    o = db.get(Organizer, organizer_id)
    if o is None:
        raise HTTPException(status_code=404, detail="Organizer not found")
    return _to_out(db, o)


@router.post("", response_model=OrganizerOut, status_code=201)
def create_organizer(
    body: OrganizerGenerate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    wt = body.wall_thickness or 1.2
    dt = body.divider_thickness or 1.2
    inner_w = body.outer_width - 2 * wt
    inner_d = body.outer_depth - 2 * wt

    specs = [
        CompartmentSpec(
            label=c.label,
            part_id=c.part_id,
            width=c.width,
            depth=c.depth,
            height=c.height,
        )
        for c in body.compartments
    ]
    default_size = 30.0
    if body.preset and body.preset in PRESETS:
        default_size = PRESETS[body.preset]["default_size"]
    if not specs:
        cols = int((inner_w + dt) / (default_size + dt))
        rows = int((inner_d + dt) / (default_size + dt))
        if cols < 1 or rows < 1:
            raise HTTPException(
                status_code=400,
                detail="Organizer too small for a single compartment",
            )
        for r in range(rows):
            for c in range(cols):
                specs.append(
                    CompartmentSpec(
                        label=f"R{r + 1}C{c + 1}",
                        width=default_size,
                        depth=default_size,
                    )
                )
    pack = pack_compartments(
        inner_w,
        inner_d,
        dt,
        specs,
        default_size=default_size,
        default_height=body.outer_height - 3.0,
    )
    if pack.error:
        raise HTTPException(status_code=400, detail=pack.error)

    organizer = Organizer(
        name=body.name,
        outer_width=body.outer_width,
        outer_depth=body.outer_depth,
        outer_height=body.outer_height,
        preset=body.preset,
        wall_thickness=wt,
        divider_thickness=dt,
        clearance=body.clearance,
    )
    db.add(organizer)
    db.flush()

    for cell in pack.cells:
        db.add(
            OrganizerCompartment(
                organizer_id=organizer.id,
                label=cell.label,
                row=cell.row,
                col=cell.col,
                width=cell.width,
                depth=cell.depth,
                height=cell.height,
                part_id=cell.part_id,
            )
        )

    stl_path = settings.backups_path.parent / "generated" / f"organizer-{organizer.id}.stl"
    write_organizer_stl(
        stl_path,
        body.outer_width,
        body.outer_depth,
        body.outer_height,
        wt,
        dt,
        pack,
    )
    organizer.stl_path = str(stl_path)
    db.commit()
    db.refresh(organizer)
    return _to_out(db, organizer)


@router.post("/{organizer_id}/assign", response_model=OrganizerOut)
def assign_compartments(
    organizer_id: str,
    assignments: list[dict],
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    o = db.get(Organizer, organizer_id)
    if o is None:
        raise HTTPException(status_code=404, detail="Organizer not found")
    for assignment in assignments:
        comp = db.get(OrganizerCompartment, assignment.get("compartment_id"))
        if comp is None or comp.organizer_id != organizer_id:
            raise HTTPException(status_code=404, detail="Compartment not found")
        part_id = assignment.get("part_id")
        if part_id and db.get(Part, part_id) is None:
            raise HTTPException(status_code=404, detail="Part not found")
        comp.part_id = part_id
        comp.label = assignment.get("label", comp.label)
        if part_id:
            part = db.get(Part, part_id)
            if part:
                part.storage_status = "assigned"
    db.commit()
    db.refresh(o)
    return _to_out(db, o)


@router.get("/{organizer_id}/stl")
def download_stl(
    organizer_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    o = db.get(Organizer, organizer_id)
    if o is None:
        raise HTTPException(status_code=404, detail="Organizer not found")
    if not o.stl_path:
        raise HTTPException(status_code=404, detail="STL not generated")
    return FileResponse(
        o.stl_path,
        media_type="model/stl",
        filename=f"{o.name.replace(' ', '_')}.stl",
    )


@router.delete("/{organizer_id}", status_code=204)
def delete_organizer(
    organizer_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    o = db.get(Organizer, organizer_id)
    if o is None:
        raise HTTPException(status_code=404, detail="Organizer not found")
    db.delete(o)
    db.commit()
