import sys
import os
from pathlib import Path
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Ensure required environment variables for testing
os.environ.setdefault("JWT_SECRET_KEY", "evidentia_test_secret_key_at_least_32_characters_long_for_security")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from database import Base, get_db
from models import User, Case, CaseMember
from auth import hash_password, create_access_token
from app import app

# Create in-memory SQLite database engine with StaticPool to retain tables across connections
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def seed_users(db):
    """Creates a standard set of users for RBAC testing."""
    users = {}
    roles = [
        ("admin", "admin@evidentia.test", "Admin User"),
        ("lead_investigator", "lead@evidentia.test", "Lead Investigator"),
        ("analyst", "analyst@evidentia.test", "Analyst User"),
        ("reviewer", "reviewer@evidentia.test", "Reviewer User"),
    ]
    for role, email, name in roles:
        existing = db.query(User).filter(User.email == email).first()
        if not existing:
            u = User(
                email=email,
                full_name=name,
                hashed_password=hash_password("password123"),
                role=role,
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            db.add(u)
            db.commit()
            db.refresh(u)
            users[role] = u
        else:
            users[role] = existing
    return users

@pytest.fixture
def admin_headers(seed_users):
    token = create_access_token({"sub": str(seed_users["admin"].id), "email": seed_users["admin"].email, "role": "admin"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def analyst_headers(seed_users):
    token = create_access_token({"sub": str(seed_users["analyst"].id), "email": seed_users["analyst"].email, "role": "analyst"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def reviewer_headers(seed_users):
    token = create_access_token({"sub": str(seed_users["reviewer"].id), "email": seed_users["reviewer"].email, "role": "reviewer"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def lead_headers(seed_users):
    token = create_access_token({"sub": str(seed_users["lead_investigator"].id), "email": seed_users["lead_investigator"].email, "role": "lead_investigator"})
    return {"Authorization": f"Bearer {token}"}
