"""
BirdeyeWalletTransaction 实体类
对应数据库表: birdeye_wallet_transactions
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    BigInteger, String, DateTime, Boolean,
    Text, TIMESTAMP, text, Index
)
from sqlalchemy.orm import Mapped, mapped_column

from config.database import Base


class BirdeyeWalletTransaction(Base):
    """Birdeye钱包历史交易记录表实体"""
    
    __tablename__ = 'birdeye_wallet_transactions'
    __table_args__ = (
        Index('uk_tx_hash', 'tx_hash', unique=True, comment='防止重复存储同一笔交易'),
        Index('idx_from', 'from_address', comment='用于查询指定钱包的历史'),
        Index('idx_block_time', 'block_time', comment='用于按时间排序查询'),
        Index('idx_block_number', 'block_number'),
        {'comment': 'Birdeye钱包历史交易记录表'}
    )
    
    # 主键
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(BigInteger, "mysql"),
        primary_key=True,
        autoincrement=True,
        comment='主键ID'
    )
    
    # 交易基本信息
    tx_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment='交易哈希 (txHash), 唯一索引'
    )
    
    block_number: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment='区块高度 (blockNumber)'
    )
    
    block_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        comment='交易时间 (blockTime ISO格式转换)'
    )
    
    status: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        default=True,
        comment='交易状态 (status): 1=成功, 0=失败'
    )
    
    # 钱包地址 (注意: from 是 Python 关键字，这里使用 from_address)
    from_address: Mapped[str] = mapped_column(
        'from',  # 数据库中的列名
        String(255),
        nullable=False,
        comment='发起交易的钱包地址 (from)'
    )
    
    to: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment='交互目标地址 (to)'
    )
    
    # 手续费
    fee: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment='交易手续费 (fee), 单位: Lamports'
    )
    
    # 主要动作类型
    main_action: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment='主要动作类型 (mainAction)'
    )
    
    # JSON 字段
    balance_change: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment='余额变动数组 (balanceChange)，json字符串'
    )
    
    contract_label: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment='合约标签信息 (contractLabel)，json字符串'
    )
    
    token_transfers: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment='代币流转明细 (tokenTransfers)，json字符串'
    )
    
    # 时间戳
    block_time_unix: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
        comment='交易时间戳，秒级'
    )
    
    # 系统字段
    create_time: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP'),
        comment='数据入库时间'
    )
    
    update_time: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'),
        comment='最后更新时间'
    )
    
    def __repr__(self) -> str:
        return (
            f"<BirdeyeWalletTransaction(id={self.id}, tx_hash='{self.tx_hash}', "
            f"from='{self.from_address}', main_action='{self.main_action}')>"
        )
    
    def to_dict(self) -> dict:
        """转换为字典"""
        import json
        
        return {
            'id': self.id,
            'tx_hash': self.tx_hash,
            'block_number': self.block_number,
            'block_time': self.block_time.isoformat() if self.block_time else None,
            'status': self.status,
            'from': self.from_address,
            'to': self.to,
            'fee': self.fee,
            'main_action': self.main_action,
            'balance_change': json.loads(self.balance_change) if self.balance_change else None,
            'contract_label': json.loads(self.contract_label) if self.contract_label else None,
            'token_transfers': json.loads(self.token_transfers) if self.token_transfers else None,
            'block_time_unix': self.block_time_unix,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'update_time': self.update_time.isoformat() if self.update_time else None,
        }
