"""
SmartWallet 实体类
对应数据库表: smart_wallets
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    BigInteger, String, DateTime, Numeric, 
    Integer, SmallInteger, TIMESTAMP, text
)
from sqlalchemy.orm import Mapped, mapped_column

from config.database import Base


class SmartWallet(Base):
    """聪明钱数据表实体"""
    
    __tablename__ = 'smart_wallets'
    __table_args__ = {'comment': '聪明钱数据表'}
    
    # 主键
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(BigInteger, "mysql"), 
        primary_key=True, 
        autoincrement=True,
        comment='主键ID'
    )
    
    # 基本信息
    address: Mapped[str] = mapped_column(
        String(44), 
        nullable=False, 
        default='',
        comment='钱包地址 (Solana地址通常44位)'
    )
    
    chain: Mapped[Optional[str]] = mapped_column(
        String(10), 
        default='SOL',
        comment='链类型'
    )
    
    balance: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 4), 
        default=Decimal('0.0000'),
        comment='钱包余额(SOL)'
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
        comment='最后更新时间'
    )
    
    # 标签字段
    is_smart_money: Mapped[Optional[int]] = mapped_column(
        SmallInteger, 
        default=0,
        comment='是否聪明钱: 1=是, 0=否'
    )
    
    is_kol: Mapped[Optional[int]] = mapped_column(
        SmallInteger, 
        default=0,
        comment='是否KOL: 1=是, 0=否'
    )
    
    is_whale: Mapped[Optional[int]] = mapped_column(
        SmallInteger, 
        default=0,
        comment='是否巨鲸: 1=是, 0=否'
    )
    
    is_sniper: Mapped[Optional[int]] = mapped_column(
        SmallInteger, 
        default=0,
        comment='是否狙击手: 1=是, 0=否'
    )
    
    twitter_handle: Mapped[Optional[str]] = mapped_column(
        String(50), 
        nullable=True,
        comment='推特账号(如果是KOL)'
    )
    
    # 工具使用标记
    uses_trojan: Mapped[Optional[int]] = mapped_column(
        SmallInteger, 
        default=0,
        comment='是否使用Trojan'
    )
    
    uses_bullx: Mapped[Optional[int]] = mapped_column(
        SmallInteger, 
        default=0,
        comment='是否使用BullX'
    )
    
    uses_photon: Mapped[Optional[int]] = mapped_column(
        SmallInteger, 
        default=0,
        comment='是否使用Photon'
    )
    
    uses_axiom: Mapped[Optional[int]] = mapped_column(
        SmallInteger, 
        default=0,
        comment='是否使用Axiom'
    )
    
    uses_bot: Mapped[Optional[int]] = mapped_column(
        SmallInteger, 
        default=0,
        comment='是否使用通用Bot脚本'
    )
    
    # 7日数据
    pnl_7d: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 2), 
        default=Decimal('0.00'),
        comment='7日盈利(USD)'
    )
    
    pnl_7d_roi: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), 
        default=Decimal('0.00'),
        comment='7日收益率(%)'
    )
    
    win_rate_7d: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), 
        default=Decimal('0.00'),
        comment='7日胜率(%)'
    )
    
    tx_count_7d: Mapped[Optional[int]] = mapped_column(
        Integer, 
        default=0,
        comment='7日总交易次数'
    )
    
    volume_7d: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 2), 
        default=Decimal('0.00'),
        comment='7日总交易量(USD)'
    )
    
    net_inflow_7d: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 2), 
        default=Decimal('0.00'),
        comment='7日净流入(USD)'
    )
    
    # 30日数据
    pnl_30d: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 2), 
        default=Decimal('0.00'),
        comment='30日盈利(USD)'
    )
    
    pnl_30d_roi: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), 
        default=Decimal('0.00'),
        comment='30日收益率(%)'
    )
    
    win_rate_30d: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), 
        default=Decimal('0.00'),
        comment='30日胜率(%)'
    )
    
    tx_count_30d: Mapped[Optional[int]] = mapped_column(
        Integer, 
        default=0,
        comment='30日总交易次数'
    )
    
    volume_30d: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 2), 
        default=Decimal('0.00'),
        comment='30日总交易量(USD)'
    )
    
    net_inflow_30d: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 2), 
        default=Decimal('0.00'),
        comment='30日净流入(USD)'
    )
    
    # 持仓时长
    avg_hold_time_7d: Mapped[Optional[int]] = mapped_column(
        Integer, 
        default=0,
        comment='7d平均持仓时长(秒)'
    )
    
    avg_hold_time_30d: Mapped[Optional[int]] = mapped_column(
        Integer, 
        nullable=True,
        comment='30D平均持仓时长'
    )
    
    # 社交数据
    followed_count: Mapped[Optional[int]] = mapped_column(
        Integer, 
        default=0,
        comment='被追踪数'
    )
    
    remark_count: Mapped[Optional[int]] = mapped_column(
        Integer, 
        default=0,
        comment='被备注数'
    )
    
    def __repr__(self) -> str:
        return (
            f"<SmartWallet(id={self.id}, address='{self.address}', "
            f"chain='{self.chain}', pnl_7d={self.pnl_7d})>"
        )
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'address': self.address,
            'chain': self.chain,
            'balance': float(self.balance) if self.balance else 0.0,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_smart_money': self.is_smart_money,
            'is_kol': self.is_kol,
            'is_whale': self.is_whale,
            'is_sniper': self.is_sniper,
            'twitter_handle': self.twitter_handle,
            'uses_trojan': self.uses_trojan,
            'uses_bullx': self.uses_bullx,
            'uses_photon': self.uses_photon,
            'uses_axiom': self.uses_axiom,
            'uses_bot': self.uses_bot,
            'pnl_7d': float(self.pnl_7d) if self.pnl_7d else 0.0,
            'pnl_7d_roi': float(self.pnl_7d_roi) if self.pnl_7d_roi else 0.0,
            'win_rate_7d': float(self.win_rate_7d) if self.win_rate_7d else 0.0,
            'tx_count_7d': self.tx_count_7d,
            'volume_7d': float(self.volume_7d) if self.volume_7d else 0.0,
            'net_inflow_7d': float(self.net_inflow_7d) if self.net_inflow_7d else 0.0,
            'pnl_30d': float(self.pnl_30d) if self.pnl_30d else 0.0,
            'pnl_30d_roi': float(self.pnl_30d_roi) if self.pnl_30d_roi else 0.0,
            'win_rate_30d': float(self.win_rate_30d) if self.win_rate_30d else 0.0,
            'tx_count_30d': self.tx_count_30d,
            'volume_30d': float(self.volume_30d) if self.volume_30d else 0.0,
            'net_inflow_30d': float(self.net_inflow_30d) if self.net_inflow_30d else 0.0,
            'avg_hold_time_7d': self.avg_hold_time_7d,
            'avg_hold_time_30d': self.avg_hold_time_30d,
            'followed_count': self.followed_count,
            'remark_count': self.remark_count,
        }
