from datetime import datetime, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth import decode_token, verify_api_key
from app.database import get_db
from app.models.user import ApiKey, User

bearer_scheme = HTTPBearer(auto_error=False)
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    db: Session = Depends(get_db),
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    api_key: str | None = Depends(api_key_scheme),
) -> User:
    if bearer is not None:
        try:
            payload = decode_token(bearer.credentials)
        except jwt.PyJWTError:
            raise _CREDENTIALS_EXC
        user = db.get(User, payload.get("sub"))
        if user is None or not user.is_active:
            raise _CREDENTIALS_EXC
        return user

    if api_key is not None:
        for key in db.query(ApiKey).filter(ApiKey.is_active.is_(True)).all():
            if verify_api_key(api_key, key.key_hash):
                key.last_used_at = datetime.now(timezone.utc)
                db.commit()
                return db.query(User).first()  # single-user app
        raise _CREDENTIALS_EXC

    raise _CREDENTIALS_EXC
