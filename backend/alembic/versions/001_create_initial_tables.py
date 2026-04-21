"""create initial tables

Revision ID: 001
Revises: 
Create Date: 2025-11-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Create user_role enum type
    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'supervisor', 'operator')")
    
    # Create waste_type enum type
    op.execute("CREATE TYPE waste_type AS ENUM ('recyclable', 'non-recyclable')")
    
    # Create users table
    op.create_table(
        'user',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('username', sa.String(50), unique=True, nullable=False),
        sa.Column('email', sa.String(100), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('admin', 'supervisor', 'operator', name='user_role'), nullable=False)
    )
    
    # Create classification_results table
    op.create_table(
        'classificationresult',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('label', sa.Enum('recyclable', 'non-recyclable', name='waste_type'), nullable=False),
        sa.Column('confidence', sa.Float, nullable=False),
        sa.Column('timestamp', sa.DateTime, nullable=False),
        sa.Column('image_url', sa.String(255)),
        sa.Column('processing_time_ms', sa.Integer)
    )
    
    # Create indexes
    op.create_index('ix_user_email', 'user', ['email'])
    op.create_index('ix_user_username', 'user', ['username'])
    op.create_index('ix_classificationresult_user_id', 'classificationresult', ['user_id'])

def downgrade() -> None:
    # Drop tables
    op.drop_table('classificationresult')
    op.drop_table('user')
    
    # Drop enum types
    op.execute('DROP TYPE waste_type')
    op.execute('DROP TYPE user_role')