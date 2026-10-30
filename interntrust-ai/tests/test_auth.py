from app.models import User, Admin


def _signup(client, email="student@example.com", password="Password123"):
    return client.post("/auth/signup", data={
        "full_name": "Test Student",
        "email": email,
        "password": password,
        "confirm_password": password,
    }, follow_redirects=True)


def test_signup_creates_user(app, client):
    resp = _signup(client)
    assert resp.status_code == 200
    with app.app_context():
        assert User.query.filter_by(email="student@example.com").first() is not None


def test_signup_rejects_duplicate_email(app, client):
    _signup(client)
    resp = _signup(client)
    assert b"already exists" in resp.data


def test_password_is_hashed_not_plaintext(app, client):
    _signup(client)
    with app.app_context():
        user = User.query.filter_by(email="student@example.com").first()
        assert user.password_hash != "Password123"
        assert user.check_password("Password123") is True
        assert user.check_password("WrongPassword") is False


def test_login_and_dashboard_access(client):
    _signup(client)
    resp = client.post("/auth/login", data={
        "email": "student@example.com",
        "password": "Password123",
    }, follow_redirects=True)
    assert b"Welcome" in resp.data or resp.status_code == 200

    dash = client.get("/dashboard/")
    assert dash.status_code == 200


def test_student_cannot_access_admin_panel(app, client):
    with app.app_context():
        admin = Admin(name="Root Admin", email="admin@example.com")
        admin.set_password("SuperSecret123")
        from app.extensions import db
        db.session.add(admin)
        db.session.commit()

    _signup(client)
    client.post("/auth/login", data={"email": "student@example.com", "password": "Password123"})

    resp = client.get("/admin/")
    assert resp.status_code == 403


def test_dashboard_requires_login(client):
    resp = client.get("/dashboard/", follow_redirects=True)
    assert b"log in" in resp.data.lower() or b"login" in resp.data.lower()
