"""
智能钱包每日快照表 Model
用于存储 GMGN 抓取的钱包数据快照
"""
from sqlalchemy import Column, BigInteger, String, Numeric, Integer, Date, DateTime, Index
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class SmartWalletSnapshot(Base):
    """智能钱包快照表 - 每日记录一次"""
    
    __tablename__ = 'smart_wallets_snapshot'
    
    # 主键
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID')
    
    # 基础信息
    address = Column(String(44), nullable=False, default='', comment='钱包地址')
    wallet_address = Column(String(44), nullable=False, default='', 
                           comment='钱包地址（与address冗余，对齐源数据）')
    name = Column(String(100), nullable=True, comment='钱包显示名称')
    last_active = Column(BigInteger, default=0, comment='最后活跃时间戳')
    chain = Column(String(10), default='SOL', comment='链类型')
    snapshot_date = Column(Date, nullable=False, comment='快照日期 (YYYY-MM-DD)')
    
    # 钱包余额和标签
    balance = Column(Numeric(20, 4), default=0.0000, comment='钱包余额(SOL)')
    sol_balance = Column(Numeric(20, 6), default=0.000000, comment='持有SOL数量')
    is_smart_money = Column(TINYINT(unsigned=True), default=0, comment='是否聪明钱: 1=是, 0=否')
    is_kol = Column(TINYINT(unsigned=True), default=0, comment='是否KOL')
    is_whale = Column(TINYINT(unsigned=True), default=0, comment='是否巨鲸')
    is_sniper = Column(TINYINT(unsigned=True), default=0, comment='是否狙击手')
    is_hot_followed = Column(TINYINT(unsigned=True), default=0, comment='是否热门追踪')
    is_hot_remarked = Column(TINYINT(unsigned=True), default=0, comment='是否热门备注')
    twitter_handle = Column(String(50), nullable=True, comment='推特账号')
    twitter_name = Column(String(100), nullable=True, comment='推特昵称')
    twitter_description = Column(String(500), nullable=True, comment='推特简介')
    
    # 工具标签
    uses_trojan = Column(TINYINT(unsigned=True), default=0, comment='使用Trojan')
    uses_bullx = Column(TINYINT(unsigned=True), default=0, comment='使用BullX')
    uses_photon = Column(TINYINT(unsigned=True), default=0, comment='使用Photon')
    uses_axiom = Column(TINYINT(unsigned=True), default=0, comment='使用Axiom')
    uses_bot = Column(TINYINT(unsigned=True), default=0, comment='使用Bot')
    
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
    avg_hold_time_30d = Column(Integer, nullable=True, comment='30d平均持仓时长(秒)')
    
    # 其他指标
    followed_count = Column(Integer, default=0, comment='被追踪数')
    remark_count = Column(Integer, default=0, comment='被备注数')
    updated_at = Column(DateTime, nullable=False, default=datetime.now, 
                       onupdate=datetime.now, comment='记录插入/更新时间')
    
    # 索引定义
    __table_args__ = (
        Index('uk_address_date', 'address', 'snapshot_date', unique=True),  # 联合唯一索引
        Index('idx_snapshot_date', 'snapshot_date'),  # 日期索引
        Index('idx_address', 'address'),  # 钱包索引
        {'comment': '聪明钱每日快照表'}
    )
    
    def __repr__(self):
        return f"<SmartWalletSnapshot(address={self.address}, date={self.snapshot_date}, pnl_7d={self.pnl_7d})>"
