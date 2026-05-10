import re

TEST_PW = "Test1!pass"


def _captcha(client):
    r = client.get("/api/auth/register-captcha")
    assert r.status_code == 200
    j = r.json()
    m = re.match(r"(\d+)\s*\+\s*(\d+)", j["question"])
    assert m, j["question"]
    ans = int(m.group(1)) + int(m.group(2))
    return j["token"], str(ans)


def _post_register(client, email, password=TEST_PW, **extra):
    cap_token, cap_ans = _captcha(client)
    body = {
        "email": email,
        "password": password,
        "password_confirm": password,
        "captcha_token": cap_token,
        "captcha_answer": cap_ans,
        **extra,
    }
    return client.post("/api/auth/register", json=body)


def test_register_creates_student(client, db, seed_school_survey_class):
    from models import User

    r = _post_register(
        client,
        "new_student@example.com",
        school_id="a0000000-0000-0000-0000-000000000001",
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("email_verification_pending") is False
    assert data.get("access_token")
    token = data["access_token"]
    me = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "user"
    u = db.query(User).filter(User.email == "new_student@example.com").first()
    assert u is not None
    assert u.role == "user"


def test_register_staff_requires_secret(client, seed_school_survey_class):
    r = client.post(
        "/api/auth/register-staff",
        json={
            "email": "bad@example.com",
            "password": TEST_PW,
            "full_name": "X",
            "role": "teacher",
            "invite_secret": "wrong",
        },
    )
    assert r.status_code == 403


def test_register_staff_with_secret(client, db, seed_school_survey_class):
    import os

    from models import User

    secret = os.environ.get("STAFF_INVITE_SECRET", "test-invite-secret")
    r = client.post(
        "/api/auth/register-staff",
        json={
            "email": "teacher_test@example.com",
            "password": TEST_PW,
            "full_name": "Вчитель",
            "role": "teacher",
            "invite_secret": secret,
            "school_id": "a0000000-0000-0000-0000-000000000001",
        },
    )
    assert r.status_code == 200
    u = db.query(User).filter(User.email == "teacher_test@example.com").first()
    assert u is not None
    assert u.role == "user"
    assert u.staff_scope is None


def test_register_and_login_password_longer_than_bcrypt_limit(client, seed_school_survey_class):
    long_pw = "Aa1!x" + ("b" * 100)
    r = _post_register(
        client,
        "long_password_user@example.com",
        password=long_pw,
        school_id="a0000000-0000-0000-0000-000000000001",
    )
    assert r.status_code == 200
    r2 = client.post(
        "/api/auth/login",
        json={"email": "long_password_user@example.com", "password": long_pw},
    )
    assert r2.status_code == 200
    assert r2.json().get("access_token")


def test_login_blocks_unverified_when_flag_off(client, db, seed_school_survey_class):
    from models import User
    from auth import get_password_hash

    u = User(
        email="unverified@example.com",
        password_hash=get_password_hash(TEST_PW),
        full_name="U",
        role="user",
        school_id=None,
        email_verified=False,
    )
    db.add(u)
    db.commit()
    r = client.post(
        "/api/auth/login",
        json={"email": "unverified@example.com", "password": TEST_PW},
    )
    assert r.status_code == 403
