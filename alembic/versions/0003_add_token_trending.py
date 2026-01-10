"""Add birdeye_token_trending table

Revision ID: 0003
Revises: 0002
Create Date: 2026-01-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create birdeye_token_trending table."""
    op.create_table(
        'birdeye_token_trending',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False, comment='自增主键'),
        sa.Column('address', sa.String(length=64), nullable=False, comment='代币合约地址(唯一标识)'),
        sa.Column('symbol', sa.String(length=32), nullable=False, comment='代币符号'),
        sa.Column('name', sa.String(length=128), nullable=True, comment='代币全称'),
        sa.Column('decimals', sa.Integer(), nullable=True, comment='代币精度'),
        sa.Column('rank', sa.Integer(), nullable=True, comment='Birdeye热度排名'),
        sa.Column('price', sa.Float(), nullable=True, comment='当前价格(USD)'),
        sa.Column('marketcap', sa.Float(), nullable=True, comment='流通市值'),
        sa.Column('fdv', sa.Float(), nullable=True, comment='完全稀释估值'),
        sa.Column('liquidity', sa.Float(), nullable=True, comment='池子流动性'),
        sa.Column('volume_24h_usd', sa.Float(), nullable=True, comment='24小时交易量(USD)'),
        sa.Column('price_24h_change_percent', sa.Float(), nullable=True, comment='24H价格涨跌幅(%)'),
        sa.Column('volume_24h_change_percent', sa.Float(), nullable=True, comment='24H交易量涨跌幅(%)'),
        sa.Column('logo_uri', sa.String(length=512), nullable=True, comment='Logo图片链接'),
        sa.Column('data_source', sa.String(length=20), nullable=False, server_default='birdeye', comment='数据来源标记'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), comment='抓取入库时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_address', 'address'),
        sa.Index('idx_rank', 'rank'),
        sa.Index('idx_created_at', 'created_at'),
        sa.Index('idx_address_created', 'address', 'created_at'),
        comment='Birdeye热门代币趋势表'
    )


def downgrade() -> None:
    """Drop birdeye_token_trending table."""
    op.drop_table('birdeye_token_trending')

