import getpass
from sqlalchemy import select
from app.core.security import hash_password
from app.db.models import User, UserRole
from app.db.session import SessionLocal


def main():
    email = input("Admin email: ").strip().lower()
    full_name = input("Admin full name: ").strip()
    password = getpass.getpass("Admin password (minimum 12 characters): ")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("User already exists")
        db.add(
            User(
                full_name=full_name,
                email=email,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
                is_active=True,
            )
        )
        db.commit()
    print("Admin created")


if __name__ == "__main__":
    main()
