from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.part import Part
from app.models.project import Project
from app.models.reservation import Reservation
from app.models.user import User
from app.schemas import ReservationCreate, ReservationOut
from app.services.inventory import StockError, apply_transaction
from app.services.shopping import part_available

router = APIRouter(prefix="/api/reservations", tags=["reservations"])


def _to_out(r: Reservation) -> ReservationOut:
    out = ReservationOut.model_validate(r)
    out.project_name = r.project.name if r.project else None
    out.part_value = r.part.value if r.part else None
    out.part_internal_id = r.part.internal_id if r.part else None
    return out


@router.get("", response_model=list[ReservationOut])
def list_reservations(
    project_id: str | None = None,
    part_id: str | None = None,
    status: str = "active",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Reservation)
    if project_id:
        query = query.filter(Reservation.project_id == project_id)
    if part_id:
        query = query.filter(Reservation.part_id == part_id)
    if status:
        query = query.filter(Reservation.status == status)
    return [_to_out(r) for r in query.order_by(Reservation.created_at.desc()).all()]


@router.post("", response_model=ReservationOut, status_code=201)
def create_reservation(
    body: ReservationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if db.get(Project, body.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if db.get(Part, body.part_id) is None:
        raise HTTPException(status_code=404, detail="Part not found")
    available = part_available(db, body.part_id)
    if body.quantity > available:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reserve {body.quantity}, only {available} available",
        )
    existing = (
        db.query(Reservation)
        .filter(
            Reservation.project_id == body.project_id,
            Reservation.part_id == body.part_id,
            Reservation.status == "active",
        )
        .first()
    )
    if existing:
        existing.quantity += body.quantity
        reservation = existing
    else:
        reservation = Reservation(**body.model_dump())
        db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return _to_out(reservation)


@router.post("/{reservation_id}/fulfill", response_model=ReservationOut)
def fulfill_reservation(
    reservation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    location = None
    for item in reservation.part.inventory_items:
        if item.quantity > 0:
            location = item.location
            break
    if location is None:
        raise HTTPException(
            status_code=400, detail="No stock available to fulfill reservation"
        )
    try:
        apply_transaction(
            db,
            part_id=reservation.part_id,
            location_id=location.id,
            quantity_change=-reservation.quantity,
            reason="project usage",
            project_id=reservation.project_id,
            reservation_id=reservation.id,
        )
    except StockError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    reservation.status = "fulfilled"
    db.commit()
    db.refresh(reservation)
    return _to_out(reservation)


@router.post("/{reservation_id}/release", response_model=ReservationOut)
def release_reservation(
    reservation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    reservation.status = "released"
    db.commit()
    db.refresh(reservation)
    return _to_out(reservation)


@router.delete("/{reservation_id}", status_code=204)
def delete_reservation(
    reservation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    db.delete(reservation)
    db.commit()
