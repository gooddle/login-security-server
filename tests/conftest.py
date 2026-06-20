import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.main import app, get_context

TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


class MockClient:
    host = "127.0.0.1"


class MockRequest:
    client = MockClient()


@pytest.fixture
def client(db):
    async def override_context(request=None):
        yield {"db": db, "request": MockRequest()}

    app.dependency_overrides[get_context] = override_context
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
