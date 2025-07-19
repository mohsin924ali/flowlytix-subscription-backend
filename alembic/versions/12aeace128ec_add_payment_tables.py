"""add_payment_tables

Revision ID: 12aeace128ec
Revises: d165d8168f01
Create Date: 2025-07-09 17:51:26.250553

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '12aeace128ec'
down_revision: Union[str, None] = 'd165d8168f01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Create payments table - SQLAlchemy will auto-create enum types
    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='Unique payment identifier'),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Associated subscription ID'),
        sa.Column('admin_user_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Admin user who processed the payment'),
        sa.Column('amount', sa.Float(), nullable=False, comment='Payment amount'),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD', comment='Payment currency code (ISO 4217)'),
        sa.Column('payment_method', sa.Enum('cash', 'card', 'bank_transfer', 'paypal', 'stripe', 'manual', 'other', name='payment_method'), nullable=False, comment='Payment method used'),
        sa.Column('payment_type', sa.Enum('subscription', 'one_time', 'refund', 'adjustment', 'penalty', 'bonus', name='payment_type'), nullable=False, comment='Type of payment'),
        sa.Column('status', sa.Enum('pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded', name='payment_status'), nullable=False, server_default='pending', comment='Payment status'),
        sa.Column('reference_id', sa.String(length=255), nullable=True, comment='External reference ID'),
        sa.Column('description', sa.Text(), nullable=True, comment='Payment description'),
        sa.Column('notes', sa.Text(), nullable=True, comment='Admin notes and processing history'),
        sa.Column('metadata_json', sa.JSON(), nullable=True, comment='Additional payment metadata'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Payment creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Payment last update timestamp'),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True, comment='Payment processing timestamp'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], name='fk_payments_subscription_id_subscriptions', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_payments'),
        sa.CheckConstraint('amount != 0', name='ck_payments_amount_not_zero'),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name='ck_payments_currency_format'),
        sa.CheckConstraint('processed_at IS NULL OR processed_at >= created_at', name='ck_payments_processed_after_created'),
        sa.CheckConstraint('updated_at >= created_at', name='ck_payments_updated_after_created'),
    )
    
    # Create indexes for payments table
    op.create_index('idx_payments_subscription_id', 'payments', ['subscription_id'], unique=False)
    op.create_index('idx_payments_status', 'payments', ['status'], unique=False)
    op.create_index('idx_payments_payment_method', 'payments', ['payment_method'], unique=False)
    op.create_index('idx_payments_payment_type', 'payments', ['payment_type'], unique=False)
    op.create_index('idx_payments_created_at', 'payments', ['created_at'], unique=False)
    op.create_index('idx_payments_processed_at', 'payments', ['processed_at'], unique=False)
    op.create_index('idx_payments_reference_id', 'payments', ['reference_id'], unique=False)
    op.create_index('idx_payments_admin_user_id', 'payments', ['admin_user_id'], unique=False)
    op.create_index('idx_payments_composite_status_created', 'payments', ['status', 'created_at'], unique=False)
    op.create_index('idx_payments_composite_subscription_status', 'payments', ['subscription_id', 'status'], unique=False)
    
    # Create payment_history table
    op.create_table(
        'payment_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='Unique history entry identifier'),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Associated payment ID'),
        sa.Column('admin_user_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Admin user who made the change'),
        sa.Column('old_status', sa.Enum('pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded', name='payment_status'), nullable=True, comment='Previous payment status'),
        sa.Column('new_status', sa.Enum('pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded', name='payment_status'), nullable=False, comment='New payment status'),
        sa.Column('action', sa.String(length=50), nullable=False, comment='Action performed (created, processed, failed, refunded, etc.)'),
        sa.Column('reason', sa.Text(), nullable=True, comment='Reason for the change'),
        sa.Column('notes', sa.Text(), nullable=True, comment='Additional notes'),
        sa.Column('metadata_json', sa.JSON(), nullable=True, comment='Additional change metadata'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='History entry creation timestamp'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], name='fk_payment_history_payment_id_payments', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_payment_history'),
    )
    
    # Create indexes for payment_history table
    op.create_index('idx_payment_history_payment_id', 'payment_history', ['payment_id'], unique=False)
    op.create_index('idx_payment_history_admin_user_id', 'payment_history', ['admin_user_id'], unique=False)
    op.create_index('idx_payment_history_created_at', 'payment_history', ['created_at'], unique=False)
    op.create_index('idx_payment_history_action', 'payment_history', ['action'], unique=False)
    op.create_index('idx_payment_history_old_status', 'payment_history', ['old_status'], unique=False)
    op.create_index('idx_payment_history_new_status', 'payment_history', ['new_status'], unique=False)


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop payment_history table if it exists
    op.execute("DROP TABLE IF EXISTS payment_history CASCADE")
    
    # Drop payments table if it exists
    op.execute("DROP TABLE IF EXISTS payments CASCADE")
    
    # Drop enums if they exist
    op.execute('DROP TYPE IF EXISTS payment_status CASCADE')
    op.execute('DROP TYPE IF EXISTS payment_type CASCADE')
    op.execute('DROP TYPE IF EXISTS payment_method CASCADE') 