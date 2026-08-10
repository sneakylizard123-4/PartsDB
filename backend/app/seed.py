from sqlalchemy.orm import Session

from app.auth import hash_password
from app.config import get_settings
from app.database import SessionLocal
from app.models.supplier import Supplier
from app.models.user import User


def seed(db: Session) -> None:
    settings = get_settings()

    user = db.query(User).filter(User.username == settings.admin_username).first()
    if user is None:
        user = User(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
            email=settings.admin_email,
        )
        db.add(user)
        print(f"Created admin user '{settings.admin_username}'")

    for name, website in [
        ("LCSC", "https://www.lcsc.com"),
        ("DigiKey", "https://www.digikey.com"),
    ]:
        if db.query(Supplier).filter(Supplier.name == name).first() is None:
            db.add(Supplier(name=name, website=website))

    db.commit()


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
