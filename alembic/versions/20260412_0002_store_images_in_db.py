"""store images in database

Revision ID: 20260412_0002
Revises: 20260412_0001
Create Date: 2026-04-12 00:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260412_0002"
down_revision: Union[str, Sequence[str], None] = "20260412_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_image", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("avatar_content_type", sa.String(length=100), nullable=True))
    op.drop_column("users", "avatar_path")

    op.add_column("books", sa.Column("cover_image", sa.LargeBinary(), nullable=True))
    op.add_column("books", sa.Column("cover_content_type", sa.String(length=100), nullable=True))
    op.drop_column("books", "cover_path")


def downgrade() -> None:
    op.add_column("books", sa.Column("cover_path", sa.String(length=255), nullable=True))
    op.drop_column("books", "cover_content_type")
    op.drop_column("books", "cover_image")

    op.add_column("users", sa.Column("avatar_path", sa.String(length=255), nullable=True))
    op.drop_column("users", "avatar_content_type")
    op.drop_column("users", "avatar_image")