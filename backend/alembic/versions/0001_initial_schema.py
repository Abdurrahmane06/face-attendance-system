"""Initial database schema.

Creates all tables from scratch: work_schedules, users, face_encodings,
absence_types, attendances, justifications, refresh_tokens.

Revision ID: 0001
Revises: (none)
Create Date: 2026-06-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None
# ---------------------------------------------------------------------------


def upgrade() -> None:
    # ── Postgres ENUM types ─────────────────────────────────────────────────
    user_role = postgresql.ENUM("ADMIN", "USER", name="user_role")
    attendance_status = postgresql.ENUM("present", "late", "absent", name="attendance_status")
    recognition_method = postgresql.ENUM("FACE", "MANUAL", name="recognition_method")

    user_role.create(op.get_bind(), checkfirst=True)
    attendance_status.create(op.get_bind(), checkfirst=True)
    recognition_method.create(op.get_bind(), checkfirst=True)

    # ── work_schedules ──────────────────────────────────────────────────────
    op.create_table(
        "work_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("expected_start_time", sa.Time(), nullable=False),
        sa.Column("grace_period_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── users (profiles) ────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("ADMIN", "USER", name="user_role", create_type=False),
            nullable=False,
            server_default="USER",
        ),
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column(
            "work_schedule_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("work_schedules.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── face_encodings ──────────────────────────────────────────────────────
    op.create_table(
        "face_encodings",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("encoding", sa.Text(), nullable=False),
        sa.Column("image_path", sa.String(500), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_face_encodings_user_id", "face_encodings", ["user_id"])

    # ── absence_types ───────────────────────────────────────────────────────
    op.create_table(
        "absence_types",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "requires_justification", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── attendances ─────────────────────────────────────────────────────────
    op.create_table(
        "attendances",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("check_in", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_out", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("present", "late", "absent", name="attendance_status", create_type=False),
            nullable=False,
            server_default="present",
        ),
        sa.Column("late_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "recognized_by",
            sa.Enum("FACE", "MANUAL", name="recognition_method", create_type=False),
            nullable=False,
            server_default="FACE",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "date", name="uq_attendance_user_date"),
    )
    op.create_index("ix_attendances_user_id", "attendances", ["user_id"])

    # ── justifications ──────────────────────────────────────────────────────
    op.create_table(
        "justifications",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "attendance_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("attendances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "absence_type_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("absence_types.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("document_url", sa.String(500), nullable=True),
        sa.Column(
            "approved_by",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_justifications_attendance_id", "justifications", ["attendance_id"])

    # ── refresh_tokens ──────────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.String(500), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token", "refresh_tokens", ["token"], unique=True)


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_table("justifications")
    op.drop_table("attendances")
    op.drop_table("absence_types")
    op.drop_table("face_encodings")
    op.drop_table("users")
    op.drop_table("work_schedules")

    op.execute("DROP TYPE IF EXISTS recognition_method")
    op.execute("DROP TYPE IF EXISTS attendance_status")
    op.execute("DROP TYPE IF EXISTS user_role")
