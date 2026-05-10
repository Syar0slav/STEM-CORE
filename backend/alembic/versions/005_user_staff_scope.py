"""Ролі admin/user та staff_scope для завучів/директора.

Revision ID: 005_staff_scope
Revises: 004_email_ver
Create Date: 2026-04-19

"""
from typing import Sequence, Union

from alembic import op

revision: str = "005_staff_scope"
down_revision: Union[str, None] = "004_email_ver"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS staff_scope VARCHAR(20)
        """
    )
    op.execute(
        """
        UPDATE users SET staff_scope = CASE
            WHEN role = 'director' THEN 'school'
            WHEN role = 'deputy' THEN 'parallel_a'
            ELSE NULL
        END
        WHERE role IN ('director', 'deputy')
        """
    )
    # Зняти будь-який CHECK на role: ім'я може не збігатися з users_role_check (create_all / старі збірки).
    op.execute(
        """
        DO $$
        DECLARE r record;
        BEGIN
            FOR r IN (
                SELECT c.conname::text AS cname
                FROM pg_constraint c
                JOIN pg_class t ON c.conrelid = t.oid
                JOIN pg_namespace n ON t.relnamespace = n.oid
                WHERE n.nspname = 'public'
                  AND t.relname = 'users'
                  AND c.contype = 'c'
                  AND pg_get_constraintdef(c.oid) ILIKE '%role%'
            ) LOOP
                EXECUTE format('ALTER TABLE public.users DROP CONSTRAINT IF EXISTS %I', r.cname);
            END LOOP;
        END $$;
        """
    )
    op.execute(
        """
        UPDATE users SET role = 'user' WHERE role <> 'admin'
        """
    )
    op.execute(
        """
        ALTER TABLE users ADD CONSTRAINT users_role_check
        CHECK (role IN ('admin', 'user'))
        """
    )
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_staff_scope_check")
    op.execute(
        """
        ALTER TABLE users ADD CONSTRAINT users_staff_scope_check
        CHECK (
            staff_scope IS NULL OR staff_scope IN ('parallel_a', 'parallel_b', 'school')
        )
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_staff_scope_check")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS staff_scope")
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check")
    op.execute(
        """
        ALTER TABLE users ADD CONSTRAINT users_role_check
        CHECK (role IN ('admin', 'director', 'deputy', 'teacher', 'student'))
        """
    )
