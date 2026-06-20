def test_signup_success(client):
    res = client.post("/auth/signup", json={"email": "new@example.com", "password": "password123"})
    assert res.status_code == 201
    assert res.json()["email"] == "new@example.com"


def test_signup_duplicate_email(client, db):
    client.post("/auth/signup", json={"email": "dup@example.com", "password": "password123"})
    res = client.post("/auth/signup", json={"email": "dup@example.com", "password": "password123"})
    assert res.status_code == 409


def test_signup_invalid_email(client):
    res = client.post("/auth/signup", json={"email": "not-an-email", "password": "password123"})
    assert res.status_code == 422


def test_signup_short_password(client):
    res = client.post("/auth/signup", json={"email": "test@example.com", "password": "123"})
    assert res.status_code == 422
