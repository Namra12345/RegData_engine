

from passlib.context import CryptContext # type: ignore
from database import SessionLocal, engine, Base
from models import User

# Use pbkdf2_sha256 to completely avoid bcrypt's 72-byte limit and version issues
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def seed_users():
    # Ensure tables are created in Neon PostgreSQL
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    demo_users = [
        {"username": "compliance_user", "password": "Password123!", "role": "compliance_officer"},
        {"username": "auditor_user", "password": "Password123!", "role": "auditor"},
        {"username": "data_engineer_user", "password": "Password123!", "role": "data_engineer"},
        {"username": "admin_user", "password": "Password123!", "role": "admin"},
    ]

    for user_data in demo_users:
        existing_user = db.query(User).filter(User.username == user_data["username"]).first()
        if not existing_user:
            hashed_pw = pwd_context.hash(user_data["password"])
            new_user = User(
                username=user_data["username"],
                hashed_password=hashed_pw,
                role=user_data["role"],
                is_active=True
            )
            db.add(new_user)
            print(f"Created user: {user_data['username']} with role: {user_data['role']}")
        else:
            print(f"User already exists: {user_data['username']}")

    db.commit()
    db.close()
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed_users()