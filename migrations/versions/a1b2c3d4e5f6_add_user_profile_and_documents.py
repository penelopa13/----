"""add user profile fields, user_documents table, fix is_admin column

Revision ID: a1b2c3d4e5f6
Revises: c69ed9766c93
Create Date: 2026-05-09 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'c69ed9766c93'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        try:
            batch_op.drop_column('is_admin')
        except Exception:
            pass

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('first_name',      sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('last_name',       sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('middle_name',     sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('phone',           sa.String(20),  nullable=True))
        batch_op.add_column(sa.Column('birth_date',      sa.Date(),      nullable=True))
        batch_op.add_column(sa.Column('iin',             sa.String(12),  nullable=True))
        batch_op.add_column(sa.Column('address',         sa.String(300), nullable=True))
        batch_op.add_column(sa.Column('school_name',     sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('graduation_year', sa.Integer(),   nullable=True))

    with op.batch_alter_table('applications', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id',         sa.Integer(),  nullable=True))
        batch_op.add_column(sa.Column('education_level', sa.String(50), nullable=True))
        batch_op.create_foreign_key('fk_applications_user_id', 'user', ['user_id'], ['id'])

    op.create_table(
        'user_documents',
        sa.Column('id',           sa.Integer(),     primary_key=True),
        sa.Column('user_id',      sa.Integer(),     sa.ForeignKey('user.id'), nullable=False),
        sa.Column('doc_type',     sa.String(50),    nullable=False),
        sa.Column('display_name', sa.String(200),   nullable=True),
        sa.Column('filename',     sa.String(200),   nullable=False),
        sa.Column('file_data',    sa.LargeBinary(), nullable=False),
        sa.Column('mime_type',    sa.String(100),   nullable=False),
        sa.Column('file_size',    sa.Integer(),     nullable=True),
        sa.Column('uploaded_at',  sa.DateTime(),    nullable=True),
    )
    op.create_index('ix_user_documents_user_id',  'user_documents', ['user_id'])
    op.create_index('ix_user_documents_doc_type', 'user_documents', ['doc_type'])


def downgrade():
    op.drop_table('user_documents')
    with op.batch_alter_table('applications', schema=None) as batch_op:
        batch_op.drop_constraint('fk_applications_user_id', type_='foreignkey')
        batch_op.drop_column('education_level')
        batch_op.drop_column('user_id')
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('graduation_year')
        batch_op.drop_column('school_name')
        batch_op.drop_column('address')
        batch_op.drop_column('iin')
        batch_op.drop_column('birth_date')
        batch_op.drop_column('phone')
        batch_op.drop_column('middle_name')
        batch_op.drop_column('last_name')
        batch_op.drop_column('first_name')
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_admin', sa.Boolean(), nullable=True, server_default='false'))