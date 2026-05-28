import sys
import uuid

if len(sys.argv) < 3:
    print("Usage: py create_admin.py <email> <password>")
    sys.exit(1)

email, password = sys.argv[1], sys.argv[2]
if len(password) < 8:
    print("Password must be at least 8 characters")
    sys.exit(1)

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent / "backend"))
from password_hashing import hash_password
from sqlalchemy import create_engine, text

h = hash_password(password)
uid = str(uuid.uuid4())
school = "a0000000-0000-0000-0000-000000000001"

import os
from pathlib import Path

env = Path(__file__).parent.parent / "backend" / ".env"
url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/stem_diagnostic")
if env.exists() and "DATABASE_URL" not in os.environ:
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("DATABASE_URL="):
            url = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

engine = create_engine(url)
with engine.begin() as conn:
    conn.execute(
        text(
            """
            INSERT INTO users (id, email, password_hash, full_name, role, school_id, email_verified, staff_scope)
            VALUES (:id::uuid, :email, :hash, 'Admin', 'admin', :sid::uuid, TRUE, NULL)
            ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash
            """
        ),
        {"id": uid, "email": email, "hash": h, "sid": school},
    )
print("Admin user OK:", email)
