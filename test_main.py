

import pytest
from sqlalchemy import event
from database import engine, Session
from main import get_db
from fastapi.testclient import TestClient
from main import app  
from auth import get_current_user


# TestClient is a wrapper around the FastAPI app that allows us to make requests to it
client = TestClient(app)

def override_get_db():
    # Otwieramy połączenie i zaczynamy główną transakcję
    connection = engine.connect()
    transaction = connection.begin()
    
    # Tworzymy sesję powiązaną z tym połączeniem
    session = Session(bind=connection)
    # Rozpoczynamy zagnieżdżoną transakcję (savepoint)
    session.begin_nested()


    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, trans):
    # Jeśli transakcja była zagnieżdżona i nie jest już aktywna, rozpocznij nową
        if trans.nested and not trans._parent.nested:
            session.begin_nested()

    try:
        yield session
    finally:
        session.close()
        # Cofnij główną transakcję i zamknij połączenie – wszystkie zmiany zostaną wycofane
        transaction.rollback()
        connection.close()




def test_read_tasks_without_token():
    
    # Without a token, we should get a 401 Unauthorized error
    response = client.get("/tasks")
    assert response.status_code == 401


# To test endpoints that require authorization
def override_get_current_user():
    
    # Returns a mock user object
    class MockUser:
        users_id = 1
        username = "testuser"
    return MockUser()

# Override the dependency for the test

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

def test_read_tasks_with_token():
    
    # Testing the endpoint with authorization - thanks to override we don't need to send a real token
    headers = {"Authorization": "Bearer faketoken"}
    response = client.get("/tasks", headers=headers)
    # Status code should be 200 OK
    assert response.status_code == 200


def test_create_task_without_token():
        
        # Without a token, we should get a 401 Unauthorized error
        response = client.post("/tasks", json={
            "task_title": "Test Task",
            "task_description": "This is a test task",
            "task_is_complete": False,
            "task_date": None,
            "task_priority": 3
        })
        assert response.status_code == 401


def test_create_task_with_token():
    headers = {"Authorization": "Bearer faketoken"}
    response = client.post("/tasks", json={
            "task_title": "Test Task",
            "task_description": "This is a test task",
            "task_is_complete": False,
            "task_date": None,
            "task_priority": 3
        }, headers=headers)
    
    assert response.status_code == 201
     

def test_update_task_without_token():
        
        # Without a token, we should get a 401 Unauthorized error
        response = client.put("/tasks/40", json={
            "task_title": "Updated Task",
            "task_description": "This is an updated test task",
            "task_is_complete": False,
            "task_date": None,
            "task_priority": 2
        })
        assert response.status_code == 401


def test_update_task_with_token():
    headers = {"Authorization": "Bearer faketoken"}
    response = client.put("/tasks/41", json={
        "task_title": "Updated Task",
        "task_description": "This is an updated test task",
        "task_is_complete": False,
        "task_date": None,
        "task_priority": 2
        }, headers=headers)
    
    assert response.status_code == 201


def test_delete_task_without_token():
        
        # Without a token, we should get a 401 Unauthorized error
        response = client.delete("/tasks/47")
        assert response.status_code == 401


def test_delete_task_with_token():
    headers = {"Authorization": "Bearer faketoken"}
    response = client.delete("/tasks/45", headers=headers)

    assert response.status_code == 204
    
     
     

