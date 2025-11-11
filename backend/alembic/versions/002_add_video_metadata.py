"""Add video metadata fields for pipeline processing

Revision ID: 002_add_metadata
Revises: 001_initial
Create Date: 2025-11-11 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_add_metadata'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add thumbnail_key, audio_url, audio_key, and resolution fields to videos table"""

    # Add thumbnail_key column
    op.add_column('videos', sa.Column('thumbnailKey', sa.String(length=500), nullable=True))

    # Add audio_url column
    op.add_column('videos', sa.Column('audioUrl', sa.Text(), nullable=True))

    # Add audio_key column
    op.add_column('videos', sa.Column('audioKey', sa.String(length=500), nullable=True))

    # Add resolution column
    op.add_column('videos', sa.Column('resolution', sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Remove added metadata fields"""

    op.drop_column('videos', 'resolution')
    op.drop_column('videos', 'audioKey')
    op.drop_column('videos', 'audioUrl')
    op.drop_column('videos', 'thumbnailKey')
