import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models.attachment import Attachment
from app.models.part import Part
from app.models.project import Project
from app.models.user import User
from app.schemas import AttachmentFetchRequest, ORMModel
from app.services.datasheets import (
    DatasheetFetchError,
    datasheet_filename,
    fetch_datasheet,
)

router = APIRouter(prefix="/api/attachments", tags=["attachments"])


class AttachmentOut(ORMModel):
    id: str
    entity_type: str
    entity_id: str
    filename: str
    mime_type: str | None
    size: int
    kind: str
    source_url: str | None
    created_at: object


@router.post("", response_model=AttachmentOut, status_code=201)
async def upload_attachment(
    entity_type: str = Query(pattern="^(part|project)$"),
    entity_id: str = Query(),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if entity_type == "part":
        if db.get(Part, entity_id) is None:
            raise HTTPException(status_code=404, detail="Part not found")
    elif entity_type == "project":
        if db.get(Project, entity_id) is None:
            raise HTTPException(status_code=404, detail="Project not found")

    settings = get_settings()
    directory = settings.attachments_path
    directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{file.filename}"
    safe_path = (directory / stored_name).resolve()
    if not str(safe_path).startswith(str(directory.resolve())):
        raise HTTPException(status_code=400, detail="Invalid filename")

    content = await file.read()
    mime = file.content_type or "application/octet-stream"
    kind = "image" if mime.startswith("image/") else "file"
    if file.filename and file.filename.lower().endswith(".pdf"):
        kind = "datasheet"
    safe_path.write_bytes(content)

    attachment = Attachment(
        entity_type=entity_type,
        entity_id=entity_id,
        filename=file.filename or "file",
        stored_name=stored_name,
        mime_type=mime,
        size=len(content),
        kind=kind,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("", response_model=list[AttachmentOut])
def list_attachments(
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Attachment)
    if entity_type:
        query = query.filter(Attachment.entity_type == entity_type)
    if entity_id:
        query = query.filter(Attachment.entity_id == entity_id)
    return query.order_by(Attachment.created_at.desc()).all()


@router.post("/fetch", response_model=AttachmentOut, status_code=201)
def fetch_attachment(
    body: AttachmentFetchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Download a file (e.g. datasheet) from a remote URL and store it locally."""
    if body.entity_type == "part":
        entity = db.get(Part, body.entity_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Part not found")
    elif body.entity_type == "project":
        entity = db.get(Project, body.entity_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Project not found")
    else:
        raise HTTPException(status_code=422, detail="entity_type must be 'part' or 'project'")

    existing = (
        db.query(Attachment)
        .filter(
            Attachment.entity_type == body.entity_type,
            Attachment.entity_id == body.entity_id,
            Attachment.source_url == body.url,
        )
        .first()
    )
    if existing is not None:
        return existing

    try:
        content, content_type = fetch_datasheet(body.url)
    except DatasheetFetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    mime = content_type.split(";")[0].strip().lower() or "application/octet-stream"
    kind = "datasheet" if "pdf" in mime else ("image" if mime.startswith("image/") else "file")
    filename = datasheet_filename(body.url, getattr(entity, "internal_id", None) or entity.id)
    if "pdf" in mime and not filename.lower().endswith(".pdf"):
        filename = f"{Path(filename).stem}.pdf"

    settings = get_settings()
    directory = settings.attachments_path
    directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{filename}"
    (directory / stored_name).write_bytes(content)

    attachment = Attachment(
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        filename=filename,
        stored_name=stored_name,
        mime_type=mime,
        size=len(content),
        kind=kind,
        source_url=body.url,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("/{attachment_id}/download")
def download_attachment(
    attachment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    attachment = db.get(Attachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    settings = get_settings()
    path = settings.attachments_path / attachment.stored_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")
    return FileResponse(str(path), filename=attachment.filename)


@router.delete("/{attachment_id}", status_code=204)
def delete_attachment(
    attachment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    attachment = db.get(Attachment, attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    settings = get_settings()
    path = settings.attachments_path / attachment.stored_name
    if path.exists():
        path.unlink()
    db.delete(attachment)
    db.commit()
