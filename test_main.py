import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from database import Base, Task, User
import database
from main import app, get_db
from auth import get_current_user
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}/{os.getenv('MYSQL_TEST_DATABASE')}"

test_engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=test_engine)

# Overwrite the database engine and session in the app
database.engine = test_engine
database.Session = TestingSessionLocal

client = TestClient(app)



@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    # dodaj użytkownika testowego users_id=1
    db = TestingSessionLocal()
    test_user = User(
        users_id=1,
        users_username="testuser",
        users_hashed_password="hashed"
    )
    db.add(test_user)
    db.commit()
    db.close()

    yield

    # After tests are done, drop the test database
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()



def override_get_current_user():
    class MockUser:
        users_id = 1
        username = "testuser"
    return MockUser()

app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[get_db] = lambda: TestingSessionLocal()



def create_sample_task(db):
    new_task = Task(
        task_title="Sample Task",
        task_description="For test purposes",
        task_is_complete=False,
        task_date=datetime.now() + timedelta(days=1),
        task_priority=2,
        users_id=1
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task.task_id



def test_read_tasks_without_token():
    response = client.get("/tasks")
    assert response.status_code == 401

def test_read_tasks_with_token():
    headers = {"Authorization": "Bearer faketoken"}
    response = client.get("/tasks", headers=headers)
    assert response.status_code == 200

def test_create_task_without_token():
    response = client.post("/tasks", json={
        "task_title": "No Token Task",
        "task_description": "Should not work",
        "task_is_complete": False,
        "task_date": None,
        "task_priority": 3
    })
    assert response.status_code == 401

def test_create_task_with_token():
    headers = {"Authorization": "Bearer faketoken"}
    response = client.post("/tasks", json={
        "task_title": "Create Task",
        "task_description": "Task to be created",
        "task_is_complete": False,
        "task_date": (datetime.now() + timedelta(days=1)).isoformat(),
        "task_priority": 3
    }, headers=headers)
    assert response.status_code == 201

def test_update_task_without_token(db_session):
    task_id = create_sample_task(db_session)
    response = client.put(f"/tasks/{task_id}", json={
        "task_title": "Should Not Update",
        "task_description": "Unauthorized",
        "task_is_complete": True,
        "task_date": (datetime.now() + timedelta(days=2)).isoformat(),
        "task_priority": 1
    })
    assert response.status_code == 401

def test_update_task_with_token(db_session):
    task_id = create_sample_task(db_session)
    headers = {"Authorization": "Bearer faketoken"}
    response = client.put(f"/tasks/{task_id}", json={
        "task_title": "Updated Title",
        "task_description": "Updated Description",
        "task_is_complete": True,
        "task_date": (datetime.now() + timedelta(days=2)).isoformat(),
        "task_priority": 1
    }, headers=headers)
    assert response.status_code == 201

def test_delete_task_without_token(db_session):
    task_id = create_sample_task(db_session)
    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 401

def test_delete_task_with_token(db_session):
    task_id = create_sample_task(db_session)
    headers = {"Authorization": "Bearer faketoken"}
    response = client.delete(f"/tasks/{task_id}", headers=headers)
    assert response.status_code == 204
