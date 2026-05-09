"""add profile fields to user

Revision ID: c555b5442446
Revises: a1b2c3d4e5f6
Create Date: 2026-05-10 00:07:02.936663

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c555b5442446'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None

def upgrade():
    # Колонки профиля уже добавлены ранее
    pass

def downgrade():
    # Удаляем колонки при откате
    op.drop_column('user', 'graduation_year')
    op.drop_column('user', 'school_name')
    op.drop_column('user', 'address')
    op.drop_column('user', 'iin')
    op.drop_column('user', 'birth_date')
    op.drop_column('user', 'phone')
    op.drop_column('user', 'middle_name')
    op.drop_column('user', 'last_name')
    op.drop_column('user', 'first_name')