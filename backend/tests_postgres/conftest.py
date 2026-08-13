import os
URL=os.getenv("POSTGRES_TEST_DATABASE_URL","")
if not URL or "test" not in URL.lower():
    import pytest
    pytest.skip("POSTGRES_TEST_DATABASE_URL pointing to an isolated test database is required",allow_module_level=True)
os.environ["DATABASE_URL"]=URL
import pytest
from fastapi.testclient import TestClient
from app.database import Base,engine
from app.main import app
@pytest.fixture(autouse=True)
def clean():
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine);yield;Base.metadata.drop_all(engine)
@pytest.fixture
def client():return TestClient(app)
@pytest.fixture
def owner(client):
    token=client.post('/api/auth/register',json={'email':'pg@example.com','password':'password1','name':'Owner'}).json()['access_token'];h={'Authorization':f'Bearer {token}'};s=client.post('/api/shops',headers=h,json={'name':'PG Test'}).json();return h,s
