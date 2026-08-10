import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import hash_api_key
from app.database import get_db
from app.deps import get_current_user
from app.models.user import ApiKey, User
from app.schemas import (
    ApiKeyCreated,
    ApiKeyCreate,
    ApiKeyResponse,
    UserResponse,
)

router = APIRouter(prefix="/api", tags=["account"])


@router.get("/auth/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()


@router.post("/api-keys", response_model=ApiKeyCreated, status_code=201)
def create_api_key(
    body: ApiKeyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    key = f"pdb_{uuid.uuid4().hex}"
    entry = ApiKey(name=body.name, key_hash=hash_api_key(key))
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return ApiKeyCreated(
        **ApiKeyResponse.model_validate(entry).model_dump(), key=key
    )


@router.delete("/api-keys/{key_id}", status_code=204)
def revoke_api_key(
    key_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    entry = db.get(ApiKey, key_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="API key not found")
    db.delete(entry)
    db.commit()
