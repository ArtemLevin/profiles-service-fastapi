from alembic import op
import sqlalchemy as sa
import uuid

revision = '0001_init_profiles'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'profiles',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', sa.Integer(), nullable=False, unique=True),
        sa.Column('full_name', sa.Text(), nullable=False),
        sa.Column('phone_e164_enc', sa.LargeBinary(), nullable=False),
        sa.Column('phone_hash', sa.LargeBinary(), nullable=False, unique=True),
        sa.Column('marketing_opt_in', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('twofa_phone_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.create_index('ix_profiles_user_id', 'profiles', ['user_id'], unique=True)
    op.create_index('ix_profiles_phone_hash', 'profiles', ['phone_hash'], unique=True)

def downgrade():
    op.drop_index('ix_profiles_user_id', table_name='profiles')
    op.drop_index('ix_profiles_phone_hash', table_name='profiles')
    op.drop_table('profiles')
