from unittest.mock import patch

from app.models.user import User
from app.services.auth_service import hash_password

SIGNUP = """
mutation Signup($email: String!, $password: String!) {
    signup(email: $email, password: $password) {
        email
    }
}
"""

LOGIN = """
mutation Login($email: String!, $password: String!) {
    login(email: $email, password: $password) {
        message
        email
    }
}
"""


def gql(client, query, variables=None):
    return client.post("/graphql", json={"query": query, "variables": variables or {}})


def make_user(db, email="test@example.com", password="password123"):
    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_signup_success(client):
    res = gql(client, SIGNUP, {"email": "new@example.com", "password": "password123"})
    assert res.status_code == 200
    assert res.json()["data"]["signup"]["email"] == "new@example.com"


def test_signup_duplicate_email(client, db):
    make_user(db, email="dup@example.com")
    res = gql(client, SIGNUP, {"email": "dup@example.com", "password": "password123"})
    assert res.json()["errors"] is not None


def test_signup_invalid_email(client):
    res = gql(client, SIGNUP, {"email": "not-an-email", "password": "password123"})
    assert res.json()["errors"] is not None


def test_signup_short_password(client):
    res = gql(client, SIGNUP, {"email": "test@example.com", "password": "123"})
    assert res.json()["errors"] is not None


def test_login_success(client, db):
    make_user(db)
    with patch("app.services.auth_service.send_new_ip_alert"):
        res = gql(client, LOGIN, {"email": "test@example.com", "password": "password123"})
    assert res.json()["data"]["login"]["message"] == "로그인 성공"


def test_login_wrong_password(client, db):
    make_user(db)
    res = gql(client, LOGIN, {"email": "test@example.com", "password": "wrong"})
    assert res.json()["errors"] is not None


def test_new_ip_triggers_email(client, db):
    make_user(db)
    with patch("app.services.auth_service.send_new_ip_alert") as mock_email:
        gql(client, LOGIN, {"email": "test@example.com", "password": "password123"})
        mock_email.assert_called_once()


def test_known_ip_no_email(client, db):
    make_user(db)
    with patch("app.services.auth_service.send_new_ip_alert") as mock_email:
        gql(client, LOGIN, {"email": "test@example.com", "password": "password123"})
        gql(client, LOGIN, {"email": "test@example.com", "password": "password123"})
        assert mock_email.call_count == 1
