"""update token overview schema

Revision ID: 0005
Revises: 0004
Create Date: 2026-01-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade birdeye_token_overview table to match new schema."""
    
    # Drop the old table if exists
    op.execute("DROP TABLE IF EXISTS `birdeye_token_overview`")
    
    # Create new table with updated schema
    op.create_table(
        'birdeye_token_overview',
        sa.Column('id', mysql.BIGINT(unsigned=True), nullable=False, autoincrement=True),
        sa.Column('address', sa.String(64), nullable=False, default='', comment='代币合约地址 (address)'),
        sa.Column('symbol', sa.String(32), nullable=True, comment='代币符号 (需关联其他表获取，此接口未直接返回Symbol)'),
        sa.Column('decimals', sa.Integer(), nullable=True, comment='精度'),
        
        # Supply and holders
        sa.Column('total_supply', sa.String(50), nullable=True, comment='总供应量 (totalSupply)'),
        sa.Column('circulating_supply', sa.String(50), nullable=True, comment='流通供应量 (circulatingSupply)'),
        sa.Column('holder_count', sa.Integer(), nullable=True, comment='持有人数 (holder)'),
        sa.Column('number_markets', sa.Integer(), nullable=True, comment='上线市场数量 (numberMarkets)'),
        
        # Price and market metrics
        sa.Column('price', sa.String(40), nullable=True, comment='当前价格 (price)'),
        sa.Column('market_cap', sa.String(40), nullable=True, comment='市值 (marketCap)'),
        sa.Column('fdv', sa.String(40), nullable=True, comment='完全稀释估值 (fdv)'),
        sa.Column('liquidity', sa.String(40), nullable=True, comment='流动性池USD (liquidity)'),
        
        # Extensions and metadata
        sa.Column('extensions', sa.JSON(), nullable=True, comment='扩展数据 (extensions)'),
        sa.Column('last_trade_unix_time', sa.BigInteger(), nullable=True, comment='最后交易时间戳'),
        sa.Column('last_trade_human_time', sa.DateTime(), nullable=True, comment='最后交易时间 (ISO格式)'),
        
        # 30m metrics
        sa.Column('price_change_30m_percent', sa.String(20), nullable=True, comment='30m 价格涨跌幅'),
        sa.Column('trade_30m', sa.Integer(), nullable=True, comment='30m 交易笔数'),
        sa.Column('buy_30m', sa.Integer(), nullable=True, comment='30m 买入笔数'),
        sa.Column('sell_30m', sa.Integer(), nullable=True, comment='30m 卖出笔数'),
        sa.Column('volume_30m_usd', sa.String(40), nullable=True, comment='30m 交易额USD (v30mUSD)'),
        sa.Column('unique_wallet_30m', sa.Integer(), nullable=True, comment='30m 独立钱包数'),
        
        # 1h metrics
        sa.Column('price_change_1h_percent', sa.String(20), nullable=True, comment='1h 价格涨跌幅'),
        sa.Column('trade_1h', sa.Integer(), nullable=True, comment='1h 交易笔数'),
        sa.Column('buy_1h', sa.Integer(), nullable=True, comment='1h 买入笔数'),
        sa.Column('sell_1h', sa.Integer(), nullable=True, comment='1h 卖出笔数'),
        sa.Column('volume_1h_usd', sa.String(40), nullable=True, comment='1h 交易额USD (v1hUSD)'),
        sa.Column('unique_wallet_1h', sa.Integer(), nullable=True, comment='1h 独立钱包数'),
        
        # 4h metrics
        sa.Column('price_change_4h_percent', sa.String(20), nullable=True, comment='4h 价格涨跌幅'),
        sa.Column('trade_4h', sa.Integer(), nullable=True, comment='4h 交易笔数'),
        sa.Column('buy_4h', sa.Integer(), nullable=True, comment='4h 买入笔数'),
        sa.Column('sell_4h', sa.Integer(), nullable=True, comment='4h 卖出笔数'),
        sa.Column('volume_4h_usd', sa.String(40), nullable=True, comment='4h 交易额USD (v4hUSD)'),
        sa.Column('unique_wallet_4h', sa.Integer(), nullable=True, comment='4h 独立钱包数'),
        
        # 24h metrics
        sa.Column('price_change_24h_percent', sa.String(20), nullable=True, comment='24h 价格涨跌幅'),
        sa.Column('trade_24h', sa.Integer(), nullable=True, comment='24h 交易笔数'),
        sa.Column('buy_24h', sa.Integer(), nullable=True, comment='24h 买入笔数'),
        sa.Column('sell_24h', sa.Integer(), nullable=True, comment='24h 卖出笔数'),
        sa.Column('volume_24h_usd', sa.String(40), nullable=True, comment='24h 交易额USD (v24hUSD)'),
        sa.Column('volume_buy_24h_usd', sa.String(40), nullable=True, comment='24h 买入额USD (vBuy24hUSD)'),
        sa.Column('volume_sell_24h_usd', sa.String(40), nullable=True, comment='24h 卖出额USD (vSell24hUSD)'),
        sa.Column('unique_wallet_24h', sa.Integer(), nullable=True, comment='24h 独立钱包数'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='数据入库时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='最后更新时间'),
        
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        mysql_comment='Birdeye代币行情概览快照'
    )
    
    # Create indexes
    op.create_index('idx_address', 'birdeye_token_overview', ['address'])
    op.create_index('idx_liquidity', 'birdeye_token_overview', ['liquidity'])
    op.create_index('idx_market_cap', 'birdeye_token_overview', ['market_cap'])
    op.create_index('idx_change_24h', 'birdeye_token_overview', ['price_change_24h_percent'])
    op.create_index('idx_volume_24h', 'birdeye_token_overview', ['volume_24h_usd'])


def downgrade() -> None:
    """Downgrade to previous schema."""
    op.drop_table('birdeye_token_overview')
    
    # Recreate old table structure (simplified version)
    op.create_table(
        'birdeye_token_overview',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('token_address', sa.String(128), nullable=False, comment='Token address'),
        sa.Column('price', sa.Float(), nullable=True, comment='Current price'),
        sa.Column('market_cap', sa.Float(), nullable=True, comment='Market cap'),
        sa.Column('fdv', sa.Float(), nullable=True, comment='Fully diluted valuation'),
        sa.Column('liquidity', sa.Float(), nullable=True, comment='Total liquidity'),
        sa.Column('total_supply', sa.Float(), nullable=True),
        sa.Column('circulating_supply', sa.Float(), nullable=True),
        sa.Column('holder', sa.Integer(), nullable=True, comment='Number of holders'),
        sa.Column('number_markets', sa.Integer(), nullable=True, comment='Number of markets'),
        sa.Column('price_change_24h_percent', sa.Float(), nullable=True, comment='24h price change %'),
        sa.Column('v24h', sa.Float(), nullable=True, comment='24h volume'),
        sa.Column('v24h_usd', sa.Float(), nullable=True, comment='24h volume USD'),
        sa.Column('trade_24h', sa.Integer(), nullable=True, comment='24h trades'),
        sa.Column('buy_24h', sa.Integer(), nullable=True),
        sa.Column('sell_24h', sa.Integer(), nullable=True),
        sa.Column('unique_wallet_24h', sa.Integer(), nullable=True, comment='24h unique wallets'),
        sa.Column('price_change_1h_percent', sa.Float(), nullable=True),
        sa.Column('v1h', sa.Float(), nullable=True),
        sa.Column('v1h_usd', sa.Float(), nullable=True),
        sa.Column('v30m', sa.Float(), nullable=True),
        sa.Column('v30m_usd', sa.Float(), nullable=True),
        sa.Column('last_trade_unix_time', sa.BigInteger(), nullable=True, comment='Last trade timestamp'),
        sa.Column('last_trade_human_time', sa.DateTime(), nullable=True, comment='Last trade time'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_token_overview_created', 'birdeye_token_overview', ['token_address', 'created_at'])
    op.create_index('idx_market_cap_liquidity', 'birdeye_token_overview', ['market_cap', 'liquidity'])

