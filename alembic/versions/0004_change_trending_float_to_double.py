"""Change float columns to double for large values

Revision ID: 0004
Revises: 0003
Create Date: 2026-01-10

Fix: Out of range value error for marketcap, fdv, liquidity, volume fields
MySQL FLOAT 范围: ±3.402823466E+38
MySQL DOUBLE 范围: ±1.7976931348623157E+308

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
    
    # 1. birdeye_token_transactions 表
    print("Upgrading birdeye_token_transactions...")
    op.alter_column('birdeye_token_transactions', 'basePrice',
                    existing_type=sa.Float(),
                    type_=sa.Double(),
                    existing_nullable=True,
                    comment="目标币 (Poppy) 的单价 (USD)")
    
    op.alter_column('birdeye_token_transactions', 'quotePrice',
                    existing_type=sa.Float(),
                    type_=sa.Double(),
                    existing_nullable=True,
                    comment="计价币 (SOL) 的单价 (USD)")
    
    op.alter_column('birdeye_token_transactions', 'pricePair',
                    existing_type=sa.Float(),
                    type_=sa.Double(),
                    existing_nullable=True,
                    comment="兑换比率")
    
    op.alter_column('birdeye_token_transactions', 'tokenPrice',
                    existing_type=sa.Float(),
                    type_=sa.Double(),
                    existing_nullable=True,
                    comment="Quote Token 的价格")
    
    # 2. birdeye_token_trending 表
    print("Upgrading birdeye_token_trending...")
    op.alter_column('birdeye_token_trending', 'marketcap',
                    existing_type=sa.Float(),
                    type_=sa.Double(),
                    existing_nullable=True,
                    comment="流通市值")
    
    op.alter_column('birdeye_token_trending', 'fdv',
                    existing_type=sa.Float(),
                    type_=sa.Double(),
                    existing_nullable=True,
                    comment="完全稀释估值")
    
    op.alter_column('birdeye_token_trending', 'liquidity',
                    existing_type=sa.Float(),
                    type_=sa.Double(),
                    existing_nullable=True,
                    comment="池子流动性")
    
    op.alter_column('birdeye_token_trending', 'volume_24h_usd',
                    existing_type=sa.Float(),
                    type_=sa.Double(),
                    existing_nullable=True,
                    comment="24小时交易量(USD)")
    
    # 2. birdeye_new_listings 表
    print("Upgrading birdeye_new_listings...")
    op.alter_column('birdeye_new_listings', 'liquidity',
                    existing_type=sa.Float(),
                    type_=sa.Double(),
                    existing_nullable=True,
                    comment="初始流动性USD (liquidity)")
    
    # 3. birdeye_token_overview 表
    print("Upgrading birdeye_token_overview...")
    op.alter_column('birdeye_token_overview', 'market_cap',
                    existing_type=sa.Float(),
                    type_=sa.Double(),
                    existing_nullable=True,
                    comment="Market cap")
    
    op.alter_column('birdeye_token_overview', 'fdv',
                    existing_type=sa.Float(),
                    type_=sa.Double(),
                    existing_nullable=True,
                    comment="Fully diluted valuation")
    
    op.alter_column('birdeye_token_overview', 'liquidity',
                    existing_type=sa.Float(),
                    type_=sa.Double(),
                    existing_nullable=True,
                    comment="Total liquidity")
    
    op.alter_column('birdeye_token_overview', 'v24h',
                    existing_type=sa.Float(),
                    type_=sa.Double(),
                    existing_nullable=True,
                    comment="24h volume")
    
    op.alter_column('birdeye_token_overview', 'v24h_usd',
                    existing_type=sa.Float(),
                    type_=sa.Double(),
                    existing_nullable=True,
                    comment="24h volume USD")
    
    print("Upgrade completed!")


def downgrade() -> None:
    """Downgrade database schema."""
    
    # 回滚：从 DOUBLE 改回 FLOAT
    
    # 3. birdeye_token_overview 表
    print("Downgrading birdeye_token_overview...")
    op.alter_column('birdeye_token_overview', 'v24h_usd',
                    existing_type=sa.Double(),
                    type_=sa.Float(),
                    existing_nullable=True,
                    comment="24h volume USD")
    
    op.alter_column('birdeye_token_overview', 'v24h',
                    existing_type=sa.Double(),
                    type_=sa.Float(),
                    existing_nullable=True,
                    comment="24h volume")
    
    op.alter_column('birdeye_token_overview', 'liquidity',
                    existing_type=sa.Double(),
                    type_=sa.Float(),
                    existing_nullable=True,
                    comment="Total liquidity")
    
    op.alter_column('birdeye_token_overview', 'fdv',
                    existing_type=sa.Double(),
                    type_=sa.Float(),
                    existing_nullable=True,
                    comment="Fully diluted valuation")
    
    op.alter_column('birdeye_token_overview', 'market_cap',
                    existing_type=sa.Double(),
                    type_=sa.Float(),
                    existing_nullable=True,
                    comment="Market cap")
    
    # 2. birdeye_new_listings 表
    print("Downgrading birdeye_new_listings...")
    op.alter_column('birdeye_new_listings', 'liquidity',
                    existing_type=sa.Double(),
                    type_=sa.Float(),
                    existing_nullable=True,
                    comment="初始流动性USD (liquidity)")
    
    # 1. birdeye_token_trending 表
    print("Downgrading birdeye_token_trending...")
    op.alter_column('birdeye_token_trending', 'volume_24h_usd',
                    existing_type=sa.Double(),
                    type_=sa.Float(),
                    existing_nullable=True,
                    comment="24小时交易量(USD)")
    
    op.alter_column('birdeye_token_trending', 'liquidity',
                    existing_type=sa.Double(),
                    type_=sa.Float(),
                    existing_nullable=True,
                    comment="池子流动性")
    
    op.alter_column('birdeye_token_trending', 'fdv',
                    existing_type=sa.Double(),
                    type_=sa.Float(),
                    existing_nullable=True,
                    comment="完全稀释估值")
    
    op.alter_column('birdeye_token_trending', 'marketcap',
                    existing_type=sa.Double(),
                    type_=sa.Float(),
                    existing_nullable=True,
                    comment="流通市值")
    
    # 0. birdeye_token_transactions 表
    print("Downgrading birdeye_token_transactions...")
    op.alter_column('birdeye_token_transactions', 'tokenPrice',
                    existing_type=sa.Double(),
                    type_=sa.Float(),
                    existing_nullable=True,
                    comment="Quote Token 的价格")
    
    op.alter_column('birdeye_token_transactions', 'pricePair',
                    existing_type=sa.Double(),
                    type_=sa.Float(),
                    existing_nullable=True,
                    comment="兑换比率")
    
    op.alter_column('birdeye_token_transactions', 'quotePrice',
                    existing_type=sa.Double(),
                    type_=sa.Float(),
                    existing_nullable=True,
                    comment="计价币 (SOL) 的单价 (USD)")
    
    op.alter_column('birdeye_token_transactions', 'basePrice',
                    existing_type=sa.Double(),
                    type_=sa.Float(),
                    existing_nullable=True,
                    comment="目标币 (Poppy) 的单价 (USD)")
    
    print("Downgrade completed!")

