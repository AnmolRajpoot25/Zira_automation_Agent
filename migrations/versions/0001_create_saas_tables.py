"""create saas tables

Revision ID: 0001_create_saas_tables
Revises:
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_create_saas_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("email", sa.String(length=256), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("encrypted_gemini_key", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "jira_connections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("cloud_id", sa.String(length=128), nullable=False),
        sa.Column("encrypted_access_token", sa.Text(), nullable=False),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_jira_connections_user_id"),
    )
    op.create_index(op.f("ix_jira_connections_user_id"), "jira_connections", ["user_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_jira_connections_user_id"), table_name="jira_connections")
    op.drop_table("jira_connections")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
