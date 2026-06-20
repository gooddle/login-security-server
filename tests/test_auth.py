from unittest.mock import patch

from app.models.user import User
from app.services.auth_service import hash_password


def make_user(db, email="test@example.com", password="password123"):
    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_login_success(client, db):
    make_user(db)
    with patch("app.services.auth_service.send_new_ip_alert"):
        res = client.post("/auth/login", json={"email": "test@example.com", "password": "password123"})
    assert res.status_code == 200


def test_login_wrong_password(client, db):
    make_user(db)
    res = client.post("/auth/login", json={"email": "test@example.com", "password": "wrong"})
    assert res.status_code == 401


def test_new_ip_triggers_email(client, db):
    make_user(db)
    with patch("app.services.auth_service.send_new_ip_alert") as mock_email:
        client.post("/auth/login", json={"email": "test@example.com", "password": "password123"})
        mock_email.assert_called_once()


def test_known_ip_no_email(client, db):
    make_user(db)
    with patch("app.services.auth_service.send_new_ip_alert") as mock_email:
        client.post("/auth/login", json={"email": "test@example.com", "password": "password123"})
        client.post("/auth/login", json={"email": "test@example.com", "password": "password123"})
        assert mock_email.call_count == 1
