import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
import pytest
from fastapi.testclient import TestClient
from app.database import Base, engine
from app.main import app

@pytest.fixture(autouse=True)
def clean():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def owner(client):
    result = client.post('/api/auth/register', json={'email':'owner@example.com','password':'password1','name':'Owner'})
    headers = {'Authorization': f"Bearer {result.json()['access_token']}"}
    shop = client.post('/api/shops', headers=headers, json={'name':'Demo Shop'}).json()
    return headers, shop
