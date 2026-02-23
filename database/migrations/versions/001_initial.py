"""initial schema

Revision ID: 818e8287f63d
Revises: 
Create Date: 2026-02-22 13:08:03.766442

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '818e8287f63d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('idx_market_data_ticker_date', 'market_data', ['ticker', sa.text('date DESC')], unique=False)
    op.create_index('idx_market_data_date', 'market_data', [sa.text('date DESC')], unique=False)
    op.create_index('idx_crypto_prices_symbol_date', 'crypto_prices', ['symbol', sa.text('date DESC')], unique=False)


def downgrade() -> None:
    op.drop_index('idx_crypto_prices_symbol_date', table_name='crypto_prices')
    op.drop_index('idx_market_data_date', table_name='market_data')
    op.drop_index('idx_market_data_ticker_date', table_name='market_data')
