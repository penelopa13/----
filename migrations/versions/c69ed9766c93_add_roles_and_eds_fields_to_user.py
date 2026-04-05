"""add roles and eds fields to User

Revision ID: c69ed9766c93
Revises: 
Create Date: 2026-04-04 00:14:53.427408

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c69ed9766c93'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Добавляем новые колонки в существующую таблицу "user"
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('role', sa.String(length=20), nullable=False, server_default='applicant'))
        batch_op.add_column(sa.Column('eds_serial_number', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('eds_iin', sa.String(length=12), nullable=True))
        batch_op.add_column(sa.Column('eds_full_name', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('eds_certificate_data', sa.JSON(), nullable=True))

    # Добавляем уникальные индексы
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_user_eds_serial_number', ['eds_serial_number'])
        batch_op.create_unique_constraint('uq_user_eds_iin', ['eds_iin'])


def downgrade():
    # Удаляем добавленные колонки (откат миграции)
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_constraint('uq_user_eds_serial_number', type_='unique')
        batch_op.drop_constraint('uq_user_eds_iin', type_='unique')
        
        batch_op.drop_column('eds_certificate_data')
        batch_op.drop_column('eds_full_name')
        batch_op.drop_column('eds_iin')
        batch_op.drop_column('eds_serial_number')
        batch_op.drop_column('role')