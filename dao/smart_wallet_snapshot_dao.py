"""
智能钱包快照表 DAO
提供插入、更新、查询功能
"""
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.dialects.mysql import insert
from models.smart_wallet_snapshot import SmartWalletSnapshot


class SmartWalletSnapshotDAO:
    """智能钱包快照数据访问对象"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def upsert_snapshot(self, wallet_data: Dict[str, Any], snapshot_date: date = None) -> Optional[SmartWalletSnapshot]:
        """
        插入快照数据
        如果 (address, snapshot_date) 已存在则跳过不操作，否则插入
        
        Args:
            wallet_data: 钱包数据字典
            snapshot_date: 快照日期，默认今天
        
        Returns:
            SmartWalletSnapshot 对象（如果是新插入的），None（如果已存在跳过）
        """
        if snapshot_date is None:
            snapshot_date = date.today()
        
        address = wallet_data.get('address')
        if not address:
            return None
        
        # 先检查是否存在
        existing = self.session.query(SmartWalletSnapshot).filter(
            SmartWalletSnapshot.address == address,
            SmartWalletSnapshot.snapshot_date == snapshot_date
        ).first()
        
        # 如果已存在，跳过不操作
        if existing:
            return None
        
        # 不存在则插入
        data = {
            'address': address,
            'wallet_address': wallet_data.get('wallet_address', address),
            'name': wallet_data.get('name'),
            'last_active': wallet_data.get('last_active', 0),
            'snapshot_date': snapshot_date,
            'chain': wallet_data.get('chain', 'SOL'),
            'balance': wallet_data.get('balance', 0),
            'sol_balance': wallet_data.get('sol_balance', 0),
            
            # 标签
            'is_smart_money': wallet_data.get('is_smart_money', 0),
            'is_kol': wallet_data.get('is_kol', 0),
            'is_whale': wallet_data.get('is_whale', 0),
            'is_sniper': wallet_data.get('is_sniper', 0),
            'is_hot_followed': wallet_data.get('is_hot_followed', 0),
            'is_hot_remarked': wallet_data.get('is_hot_remarked', 0),
            'twitter_handle': wallet_data.get('twitter_handle'),
            'twitter_name': wallet_data.get('twitter_name'),
            'twitter_description': wallet_data.get('twitter_description'),
            
            # 工具
            'uses_trojan': wallet_data.get('uses_trojan', 0),
            'uses_bullx': wallet_data.get('uses_bullx', 0),
            'uses_photon': wallet_data.get('uses_photon', 0),
            'uses_axiom': wallet_data.get('uses_axiom', 0),
            'uses_bot': wallet_data.get('uses_bot', 0),
            
            # 盈利曲线
            'daily_profit_7d': wallet_data.get('daily_profit_7d'),
            
            # 1天数据
            'pnl_1d': wallet_data.get('pnl_1d', 0),
            'pnl_1d_roi': wallet_data.get('pnl_1d_roi', 0),
            'win_rate_1d': wallet_data.get('win_rate_1d', 0),
            'tx_count_1d': wallet_data.get('tx_count_1d', 0),
            'buy_count_1d': wallet_data.get('buy_count_1d', 0),
            'sell_count_1d': wallet_data.get('sell_count_1d', 0),
            'volume_1d': wallet_data.get('volume_1d', 0),
            'net_inflow_1d': wallet_data.get('net_inflow_1d', 0),
            'avg_hold_time_1d': wallet_data.get('avg_hold_time_1d', 0),
            
            # 7天数据
            'pnl_7d': wallet_data.get('pnl_7d', 0),
            'pnl_7d_roi': wallet_data.get('pnl_7d_roi', 0),
            'win_rate_7d': wallet_data.get('win_rate_7d', 0),
            'pnl_lt_minus_dot5_num_7d': wallet_data.get('pnl_lt_minus_dot5_num_7d', 0),
            'pnl_minus_dot5_0x_num_7d': wallet_data.get('pnl_minus_dot5_0x_num_7d', 0),
            'pnl_lt_2x_num_7d': wallet_data.get('pnl_lt_2x_num_7d', 0),
            'pnl_2x_5x_num_7d': wallet_data.get('pnl_2x_5x_num_7d', 0),
            'pnl_gt_5x_num_7d': wallet_data.get('pnl_gt_5x_num_7d', 0),
            'tx_count_7d': wallet_data.get('tx_count_7d', 0),
            'buy_count_7d': wallet_data.get('buy_count_7d', 0),
            'sell_count_7d': wallet_data.get('sell_count_7d', 0),
            'volume_7d': wallet_data.get('volume_7d', 0),
            'net_inflow_7d': wallet_data.get('net_inflow_7d', 0),
            'avg_hold_time_7d': wallet_data.get('avg_hold_time_7d', 0),
            
            # 30天数据
            'pnl_30d': wallet_data.get('pnl_30d', 0),
            'realized_profit_30d': wallet_data.get('realized_profit_30d', 0),
            'pnl_30d_roi': wallet_data.get('pnl_30d_roi', 0),
            'win_rate_30d': wallet_data.get('win_rate_30d', 0),
            'tx_count_30d': wallet_data.get('tx_count_30d', 0),
            'buy_count_30d': wallet_data.get('buy_count_30d', 0),
            'sell_count_30d': wallet_data.get('sell_count_30d', 0),
            'tx_count_total': wallet_data.get('tx_count_total', 0),
            'volume_30d': wallet_data.get('volume_30d', 0),
            'net_inflow_30d': wallet_data.get('net_inflow_30d', 0),
            'avg_hold_time_30d': wallet_data.get('avg_hold_time_30d'),
            
            # 其他
            'followed_count': wallet_data.get('followed_count', 0),
            'remark_count': wallet_data.get('remark_count', 0),
            'updated_at': datetime.now()
        }
        
        # 插入新记录
        new_snapshot = SmartWalletSnapshot(**data)
        self.session.add(new_snapshot)
        self.session.flush()  # 确保获取到ID
        
        return new_snapshot
    
    def batch_upsert(self, wallets: List[Dict[str, Any]], snapshot_date: date = None) -> int:
        """
        批量插入或更新快照数据
        
        Args:
            wallets: 钱包数据列表
            snapshot_date: 快照日期，默认今天
        
        Returns:
            插入/更新的记录数
        """
        if snapshot_date is None:
            snapshot_date = date.today()
        
        count = 0
        for wallet in wallets:
            try:
                self.upsert_snapshot(wallet, snapshot_date)
                count += 1
            except Exception as e:
                print(f"⚠️ 插入钱包 {wallet.get('address')} 失败: {e}")
                continue
        
        return count
    
    def get_by_address_and_date(self, address: str, snapshot_date: date) -> Optional[SmartWalletSnapshot]:
        """根据地址和日期查询快照"""
        return self.session.query(SmartWalletSnapshot).filter(
            SmartWalletSnapshot.address == address,
            SmartWalletSnapshot.snapshot_date == snapshot_date
        ).first()
    
    def get_latest_by_address(self, address: str) -> Optional[SmartWalletSnapshot]:
        """获取某个钱包的最新快照"""
        return self.session.query(SmartWalletSnapshot).filter(
            SmartWalletSnapshot.address == address
        ).order_by(desc(SmartWalletSnapshot.snapshot_date)).first()
    
    def get_history_by_address(self, address: str, days: int = 30) -> List[SmartWalletSnapshot]:
        """
        获取某个钱包的历史快照
        
        Args:
            address: 钱包地址
            days: 查询最近N天，默认30天
        
        Returns:
            快照列表，按日期倒序
        """
        start_date = date.today() - timedelta(days=days)
        return self.session.query(SmartWalletSnapshot).filter(
            SmartWalletSnapshot.address == address,
            SmartWalletSnapshot.snapshot_date >= start_date
        ).order_by(desc(SmartWalletSnapshot.snapshot_date)).all()
    
    def get_top_wallets_by_date(self, snapshot_date: date, 
                                limit: int = 100, 
                                order_by: str = 'pnl_7d') -> List[SmartWalletSnapshot]:
        """
        获取某天的TOP钱包
        
        Args:
            snapshot_date: 快照日期
            limit: 返回数量
            order_by: 排序字段，默认 pnl_7d
        
        Returns:
            钱包列表
        """
        order_column = getattr(SmartWalletSnapshot, order_by, SmartWalletSnapshot.pnl_7d)
        
        return self.session.query(SmartWalletSnapshot).filter(
            SmartWalletSnapshot.snapshot_date == snapshot_date
        ).order_by(desc(order_column)).limit(limit).all()
    
    def get_smart_money_by_date(self, snapshot_date: date, limit: int = 100) -> List[SmartWalletSnapshot]:
        """获取某天的聪明钱钱包"""
        return self.session.query(SmartWalletSnapshot).filter(
            SmartWalletSnapshot.snapshot_date == snapshot_date,
            SmartWalletSnapshot.is_smart_money == 1
        ).order_by(desc(SmartWalletSnapshot.pnl_7d)).limit(limit).all()
    
    def get_kol_wallets_by_date(self, snapshot_date: date, limit: int = 50) -> List[SmartWalletSnapshot]:
        """获取某天的KOL钱包"""
        return self.session.query(SmartWalletSnapshot).filter(
            SmartWalletSnapshot.snapshot_date == snapshot_date,
            SmartWalletSnapshot.is_kol == 1
        ).order_by(desc(SmartWalletSnapshot.pnl_7d)).limit(limit).all()
    
    def delete_by_date(self, snapshot_date: date) -> int:
        """删除某天的所有快照（谨慎使用）"""
        count = self.session.query(SmartWalletSnapshot).filter(
            SmartWalletSnapshot.snapshot_date == snapshot_date
        ).delete()
        return count
    
    def get_date_range(self) -> tuple:
        """获取快照的日期范围 (最早日期, 最晚日期)"""
        result = self.session.query(
            func.min(SmartWalletSnapshot.snapshot_date),
            func.max(SmartWalletSnapshot.snapshot_date)
        ).first()
        return result if result else (None, None)
    
    def count_by_date(self, snapshot_date: date) -> int:
        """统计某天的快照数量"""
        return self.session.query(SmartWalletSnapshot).filter(
            SmartWalletSnapshot.snapshot_date == snapshot_date
        ).count()
