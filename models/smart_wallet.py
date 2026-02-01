"""
智能钱包表 Model（实时最新数据）
与 smart_wallets_snapshot（历史快照）不同，这个表只保存每个钱包的最新数据
"""
from sqlalchemy import Column, BigInteger, String, Numeric, Integer, DateTime, Index
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class SmartWallet(Base):
    """智能钱包表 - 实时最新数据"""
    
    __tablename__ = 'smart_wallets'
    
    # 主键
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    
    # 基础信息
    address = Column(String(44), nullable=False, unique=True, default='', 
                    comment='钱包地址 (Solana地址通常44位)')
    wallet_address = Column(String(44), nullable=False, default='', 
                           comment='钱包地址（与address冗余，对齐源数据）')
    name = Column(String(100), nullable=True, comment='钱包显示名称')
    last_active = Column(BigInteger, default=0, comment='最后活跃时间戳')
    chain = Column(String(10), default='SOL', comment='链类型')
    balance = Column(Numeric(20, 4), default=0.0000, comment='钱包余额(SOL)')
    sol_balance = Column(Numeric(20, 6), default=0.000000, comment='持有SOL数量')
    updated_at = Column(DateTime, nullable=False, default=datetime.now, 
                       onupdate=datetime.now, comment='最后更新时间')
    
    # 钱包标签
    is_smart_money = Column(TINYINT(unsigned=True), default=0, comment='是否聪明钱: 1=是, 0=否')
    is_kol = Column(TINYINT(unsigned=True), default=0, comment='是否KOL: 1=是, 0=否')
    is_whale = Column(TINYINT(unsigned=True), default=0, comment='是否巨鲸: 1=是, 0=否')
    is_sniper = Column(TINYINT(unsigned=True), default=0, comment='是否狙击手: 1=是, 0=否')
    is_hot_followed = Column(TINYINT(unsigned=True), default=0, comment='是否热门追踪')
    is_hot_remarked = Column(TINYINT(unsigned=True), default=0, comment='是否热门备注')
    twitter_handle = Column(String(50), nullable=True, comment='推特账号(如果是KOL)')
    twitter_name = Column(String(100), nullable=True, comment='推特昵称')
    twitter_description = Column(String(500), nullable=True, comment='推特简介')
    
    # 工具标签
    uses_trojan = Column(TINYINT(unsigned=True), default=0, comment='是否使用Trojan')
    uses_bullx = Column(TINYINT(unsigned=True), default=0, comment='是否使用BullX')
    uses_photon = Column(TINYINT(unsigned=True), default=0, comment='是否使用Photon')
    uses_axiom = Column(TINYINT(unsigned=True), default=0, comment='是否使用Axiom')
    uses_bot = Column(TINYINT(unsigned=True), default=0, comment='是否使用通用Bot脚本')
    
    # 盈利曲线
    daily_profit_7d = Column(String(1000), nullable=True, comment='7日每日盈利曲线(JSON)')
    
    # ===== 1天数据维度 =====
    pnl_1d = Column(Numeric(20, 2), default=0.00, comment='1日盈利(USD)')
    pnl_1d_roi = Column(Numeric(10, 2), default=0.00, comment='1日收益率(%)')
    win_rate_1d = Column(Numeric(5, 2), default=0.00, comment='1日胜率(%)')
    tx_count_1d = Column(Integer, default=0, comment='1日总交易次数')
    buy_count_1d = Column(Integer, default=0, comment='1日买入次数')
    sell_count_1d = Column(Integer, default=0, comment='1日卖出次数')
    volume_1d = Column(Numeric(20, 2), default=0.00, comment='1日总交易量(USD)')
    net_inflow_1d = Column(Numeric(20, 2), default=0.00, comment='1日净流入(USD)')
    avg_hold_time_1d = Column(Integer, default=0, comment='1d平均持仓时长(秒)')
    
    # ===== 7天数据维度 =====
    pnl_7d = Column(Numeric(20, 2), default=0.00, comment='7日盈利(USD)')
    pnl_7d_roi = Column(Numeric(10, 2), default=0.00, comment='7日收益率(%)')
    win_rate_7d = Column(Numeric(5, 2), default=0.00, comment='7日胜率(%)')
    pnl_lt_minus_dot5_num_7d = Column(Integer, default=0, comment='7日亏损超50%次数')
    pnl_minus_dot5_0x_num_7d = Column(Integer, default=0, comment='7日亏损0~50%次数')
    pnl_lt_2x_num_7d = Column(Integer, default=0, comment='7日盈利0~100%次数')
    pnl_2x_5x_num_7d = Column(Integer, default=0, comment='7日盈利2~5倍次数')
    pnl_gt_5x_num_7d = Column(Integer, default=0, comment='7日盈利超5倍次数')
    tx_count_7d = Column(Integer, default=0, comment='7日总交易次数')
    buy_count_7d = Column(Integer, default=0, comment='7日买入次数')
    sell_count_7d = Column(Integer, default=0, comment='7日卖出次数')
    volume_7d = Column(Numeric(20, 2), default=0.00, comment='7日总交易量(USD)')
    net_inflow_7d = Column(Numeric(20, 2), default=0.00, comment='7日净流入(USD)')
    avg_hold_time_7d = Column(Integer, default=0, comment='7d平均持仓时长(秒)')
    
    # ===== 30天数据维度 =====
    pnl_30d = Column(Numeric(20, 2), default=0.00, comment='30日盈利(USD)')
    realized_profit_30d = Column(Numeric(20, 4), default=0.0000, comment='30日已实现利润(USD)')
    pnl_30d_roi = Column(Numeric(10, 2), default=0.00, comment='30日收益率(%)')
    win_rate_30d = Column(Numeric(5, 2), default=0.00, comment='30日胜率(%)')
    tx_count_30d = Column(Integer, default=0, comment='30日总交易次数')
    buy_count_30d = Column(Integer, default=0, comment='30日买入次数')
    sell_count_30d = Column(Integer, default=0, comment='30日卖出次数')
    tx_count_total = Column(Integer, default=0, comment='总交易次数')
    volume_30d = Column(Numeric(20, 2), default=0.00, comment='30日总交易量(USD)')
    net_inflow_30d = Column(Numeric(20, 2), default=0.00, comment='30日净流入(USD)')
    avg_hold_time_30d = Column(Integer, nullable=True, comment='30D平均持仓时长')
    
    # 社交指标
    followed_count = Column(Integer, default=0, comment='被追踪数')
    remark_count = Column(Integer, default=0, comment='被备注数')
    
    # 索引定义
    __table_args__ = (
        Index('idx_hot_followed', 'is_hot_followed'),
        Index('idx_hot_remarked', 'is_hot_remarked'),
        {'comment': '聪明钱数据表'}
    )
    
    def __repr__(self):
        return f"<SmartWallet(address={self.address}, pnl_7d={self.pnl_7d}, is_smart_money={self.is_smart_money})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'address': self.address,
            'wallet_address': self.wallet_address,
            'name': self.name,
            'last_active': self.last_active,
            'chain': self.chain,
            'balance': float(self.balance) if self.balance else 0.0,
            'sol_balance': float(self.sol_balance) if self.sol_balance else 0.0,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            
            # 标签
            'is_smart_money': self.is_smart_money,
            'is_kol': self.is_kol,
            'is_whale': self.is_whale,
            'is_sniper': self.is_sniper,
            'is_hot_followed': self.is_hot_followed,
            'is_hot_remarked': self.is_hot_remarked,
            'twitter_handle': self.twitter_handle,
            'twitter_name': self.twitter_name,
            'twitter_description': self.twitter_description,
            
            # 工具
            'uses_trojan': self.uses_trojan,
            'uses_bullx': self.uses_bullx,
            'uses_photon': self.uses_photon,
            'uses_axiom': self.uses_axiom,
            'uses_bot': self.uses_bot,
            
            # 盈利曲线
            'daily_profit_7d': self.daily_profit_7d,
            
            # 1天数据
            'pnl_1d': float(self.pnl_1d) if self.pnl_1d else 0.0,
            'pnl_1d_roi': float(self.pnl_1d_roi) if self.pnl_1d_roi else 0.0,
            'win_rate_1d': float(self.win_rate_1d) if self.win_rate_1d else 0.0,
            'tx_count_1d': self.tx_count_1d,
            'buy_count_1d': self.buy_count_1d,
            'sell_count_1d': self.sell_count_1d,
            'volume_1d': float(self.volume_1d) if self.volume_1d else 0.0,
            'net_inflow_1d': float(self.net_inflow_1d) if self.net_inflow_1d else 0.0,
            'avg_hold_time_1d': self.avg_hold_time_1d,
            
            # 7天数据
            'pnl_7d': float(self.pnl_7d) if self.pnl_7d else 0.0,
            'pnl_7d_roi': float(self.pnl_7d_roi) if self.pnl_7d_roi else 0.0,
            'win_rate_7d': float(self.win_rate_7d) if self.win_rate_7d else 0.0,
            'pnl_lt_minus_dot5_num_7d': self.pnl_lt_minus_dot5_num_7d,
            'pnl_minus_dot5_0x_num_7d': self.pnl_minus_dot5_0x_num_7d,
            'pnl_lt_2x_num_7d': self.pnl_lt_2x_num_7d,
            'pnl_2x_5x_num_7d': self.pnl_2x_5x_num_7d,
            'pnl_gt_5x_num_7d': self.pnl_gt_5x_num_7d,
            'tx_count_7d': self.tx_count_7d,
            'buy_count_7d': self.buy_count_7d,
            'sell_count_7d': self.sell_count_7d,
            'volume_7d': float(self.volume_7d) if self.volume_7d else 0.0,
            'net_inflow_7d': float(self.net_inflow_7d) if self.net_inflow_7d else 0.0,
            'avg_hold_time_7d': self.avg_hold_time_7d,
            
            # 30天数据
            'pnl_30d': float(self.pnl_30d) if self.pnl_30d else 0.0,
            'realized_profit_30d': float(self.realized_profit_30d) if self.realized_profit_30d else 0.0,
            'pnl_30d_roi': float(self.pnl_30d_roi) if self.pnl_30d_roi else 0.0,
            'win_rate_30d': float(self.win_rate_30d) if self.win_rate_30d else 0.0,
            'tx_count_30d': self.tx_count_30d,
            'buy_count_30d': self.buy_count_30d,
            'sell_count_30d': self.sell_count_30d,
            'tx_count_total': self.tx_count_total,
            'volume_30d': float(self.volume_30d) if self.volume_30d else 0.0,
            'net_inflow_30d': float(self.net_inflow_30d) if self.net_inflow_30d else 0.0,
            'avg_hold_time_30d': self.avg_hold_time_30d,
            
            # 社交
            'followed_count': self.followed_count,
            'remark_count': self.remark_count
        }
