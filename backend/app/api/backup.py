import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models import (
    Attachment,
    BOM,
    BOMItem,
    BOMRevision,
    ESP32Device,
    InventoryItem,
    InventoryLocation,
    InventoryTransaction,
    Organizer,
    OrganizerCompartment,
    Part,
    Project,
    Reservation,
    ShoppingList,
    ShoppingListItem,
    Supplier,
    SupplierPart,
)
from app.models.user import User
from app.schemas import BackupOut

router = APIRouter(prefix="/api/backup", tags=["backup"])

ALL_TABLES = [
    Part,
    Supplier,
    SupplierPart,
    InventoryLocation,
    InventoryItem,
    InventoryTransaction,
    Project,
    BOM,
    BOMRevision,
    BOMItem,
    Reservation,
    ShoppingList,
    ShoppingListItem,
    Organizer,
    OrganizerCompartment,
    ESP32Device,
    Attachment,
]


def _row_to_dict(obj) -> dict:
    data = {}
    for col in inspect(obj).mapper.column_attrs:
        value = getattr(obj, col.key)
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        data[col.key] = value
    return data


def export_zip(db: Session, dest: Path) -> Path:
    settings = get_settings()
    payload = {
        "app": "PartsDB",
        "version": "0.1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "tables": {},
    }
    for model in ALL_TABLES:
        table = model.__tablename__
        rows = [_row_to_dict(obj) for obj in db.query(model).all()]
        payload["tables"][table] = rows

    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("backup.json", json.dumps(payload, indent=2, default=str))
        att_dir = settings.attachments_path
        if att_dir.exists():
            for file in att_dir.iterdir():
                if file.is_file():
                    zf.write(file, f"attachments/{file.name}")
    return dest


@router.post("", response_model=BackupOut, status_code=201)
def create_backup(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    settings = get_settings()
    filename = f"partsdb-backup-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.zip"
    dest = settings.backups_path / filename
    export_zip(db, dest)
    return BackupOut(
        filename=filename, created_at=datetime.now(timezone.utc)
    )


@router.get("", response_model=list[BackupOut])
def list_backups(user: User = Depends(get_current_user)):
    settings = get_settings()
    results = []
    if settings.backups_path.exists():
        for file in sorted(settings.backups_path.glob("*.zip")):
            results.append(
                BackupOut(
                    filename=file.name,
                    created_at=datetime.fromtimestamp(file.stat().st_mtime, tz=timezone.utc),
                )
            )
    return results


@router.get("/{filename}")
def download_backup(
    filename: str,
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    path = (settings.backups_path / filename).resolve()
    if not str(path).startswith(str(settings.backups_path.resolve())):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Backup not found")
    return FileResponse(
        str(path),
        media_type="application/zip",
        filename=filename,
    )
