"""Initial migration - Create all tables

Revision ID: 001
Revises:
Create Date: 2025-11-11 16:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables for English Video Learning Platform"""

    # Create users table
    op.create_table('users',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('openId', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=True),
    sa.Column('email', sa.String(length=320), nullable=True),
    sa.Column('loginMethod', sa.String(length=64), nullable=True),
    sa.Column('role', sa.Enum('user', 'admin', name='userrole'), nullable=False),
    sa.Column('createdAt', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updatedAt', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('lastSignedIn', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('openId')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_index(op.f('ix_users_openId'), 'users', ['openId'], unique=False)

    # Create categories table
    op.create_table('categories',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('slug', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('createdAt', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_categories_slug'), 'categories', ['slug'], unique=False)

    # Create videos table
    op.create_table('videos',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('slug', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('videoUrl', sa.Text(), nullable=False),
    sa.Column('videoKey', sa.String(length=500), nullable=False),
    sa.Column('thumbnailUrl', sa.Text(), nullable=True),
    sa.Column('duration', sa.Integer(), nullable=True),
    sa.Column('level', sa.Enum('A1', 'A2', 'B1', 'B2', 'C1', 'C2', name='videolevel'), nullable=False),
    sa.Column('language', sa.String(length=10), server_default='en', nullable=False),
    sa.Column('categoryId', sa.Integer(), nullable=True),
    sa.Column('uploadedBy', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('draft', 'processing', 'published', 'archived', name='videostatus'), server_default='draft', nullable=False),
    sa.Column('viewCount', sa.Integer(), server_default='0', nullable=False),
    sa.Column('createdAt', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updatedAt', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('publishedAt', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['categoryId'], ['categories.id'], ),
    sa.ForeignKeyConstraint(['uploadedBy'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_videos_slug'), 'videos', ['slug'], unique=False)

    # Create subtitles table
    op.create_table('subtitles',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('videoId', sa.Integer(), nullable=False),
    sa.Column('language', sa.String(length=10), nullable=False),
    sa.Column('languageName', sa.String(length=50), nullable=False),
    sa.Column('subtitleUrl', sa.Text(), nullable=False),
    sa.Column('subtitleKey', sa.String(length=500), nullable=False),
    sa.Column('isDefault', sa.Integer(), server_default='0', nullable=False),
    sa.Column('source', sa.Enum('manual', 'ai_generated', 'imported', name='subtitlesource'), server_default='manual', nullable=False),
    sa.Column('createdAt', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updatedAt', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['videoId'], ['videos.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # Create transcripts table
    op.create_table('transcripts',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('videoId', sa.Integer(), nullable=False),
    sa.Column('language', sa.String(length=10), server_default='en', nullable=False),
    sa.Column('source', sa.String(length=50), server_default='whisperx', nullable=False),
    sa.Column('rawData', sa.JSON(), nullable=True),
    sa.Column('isProcessed', sa.Integer(), server_default='0', nullable=False),
    sa.Column('createdAt', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updatedAt', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['videoId'], ['videos.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('videoId')
    )

    # Create transcript_sentences table
    op.create_table('transcript_sentences',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('transcriptId', sa.Integer(), nullable=False),
    sa.Column('videoId', sa.Integer(), nullable=False),
    sa.Column('sentenceIndex', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('startTime', sa.Float(), nullable=False),
    sa.Column('endTime', sa.Float(), nullable=False),
    sa.Column('words', sa.JSON(), nullable=True),
    sa.Column('createdAt', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['transcriptId'], ['transcripts.id'], ),
    sa.ForeignKeyConstraint(['videoId'], ['videos.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transcript_sentences_transcriptId'), 'transcript_sentences', ['transcriptId'], unique=False)
    op.create_index(op.f('ix_transcript_sentences_videoId'), 'transcript_sentences', ['videoId'], unique=False)

    # Create user_vocabulary table
    op.create_table('user_vocabulary',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('userId', sa.Integer(), nullable=False),
    sa.Column('word', sa.String(length=200), nullable=False),
    sa.Column('translation', sa.Text(), nullable=True),
    sa.Column('phonetic', sa.String(length=100), nullable=True),
    sa.Column('definition', sa.Text(), nullable=True),
    sa.Column('example', sa.Text(), nullable=True),
    sa.Column('videoId', sa.Integer(), nullable=True),
    sa.Column('timestamp', sa.Integer(), nullable=True),
    sa.Column('context', sa.Text(), nullable=True),
    sa.Column('masteryLevel', sa.Integer(), server_default='0', nullable=False),
    sa.Column('reviewCount', sa.Integer(), server_default='0', nullable=False),
    sa.Column('lastReviewedAt', sa.DateTime(), nullable=True),
    sa.Column('createdAt', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['userId'], ['users.id'], ),
    sa.ForeignKeyConstraint(['videoId'], ['videos.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_vocabulary_userId'), 'user_vocabulary', ['userId'], unique=False)

    # Create clips table
    op.create_table('clips',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('userId', sa.Integer(), nullable=False),
    sa.Column('videoId', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=True),
    sa.Column('searchPhrase', sa.String(length=500), nullable=True),
    sa.Column('startTime', sa.Float(), nullable=False),
    sa.Column('endTime', sa.Float(), nullable=False),
    sa.Column('duration', sa.Integer(), nullable=True),
    sa.Column('clipUrl', sa.Text(), nullable=True),
    sa.Column('clipKey', sa.String(length=500), nullable=True),
    sa.Column('thumbnailUrl', sa.Text(), nullable=True),
    sa.Column('subtitleUrl', sa.Text(), nullable=True),
    sa.Column('subtitleKey', sa.String(length=500), nullable=True),
    sa.Column('status', sa.Enum('pending', 'processing', 'ready', 'failed', name='clipstatus'), server_default='pending', nullable=False),
    sa.Column('errorMessage', sa.Text(), nullable=True),
    sa.Column('isPublic', sa.Integer(), server_default='0', nullable=False),
    sa.Column('createdAt', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updatedAt', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('completedAt', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['userId'], ['users.id'], ),
    sa.ForeignKeyConstraint(['videoId'], ['videos.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_clips_userId'), 'clips', ['userId'], unique=False)
    op.create_index(op.f('ix_clips_videoId'), 'clips', ['videoId'], unique=False)

    # Create user_quota table
    op.create_table('user_quota',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('userId', sa.Integer(), nullable=False),
    sa.Column('quotaDate', sa.Date(), nullable=False),
    sa.Column('clipsCreated', sa.Integer(), server_default='0', nullable=False),
    sa.Column('maxClips', sa.Integer(), server_default='5', nullable=False),
    sa.Column('isPremium', sa.Integer(), server_default='0', nullable=False),
    sa.Column('createdAt', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updatedAt', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['userId'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_quota_quotaDate'), 'user_quota', ['quotaDate'], unique=False)
    op.create_index(op.f('ix_user_quota_userId'), 'user_quota', ['userId'], unique=False)


def downgrade() -> None:
    """Drop all tables"""
    op.drop_table('user_quota')
    op.drop_table('clips')
    op.drop_table('user_vocabulary')
    op.drop_table('transcript_sentences')
    op.drop_table('transcripts')
    op.drop_table('subtitles')
    op.drop_table('videos')
    op.drop_table('categories')
    op.drop_table('users')
