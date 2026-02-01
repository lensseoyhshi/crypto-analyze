"""
智能钱包表 DAO（实时最新数据）
用于操作 smart_wallets 表
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from sqlalchemy.dialects.mysql import insert
from models.smart_wallet import SmartWallet
from datetime import datetime


class SmartWalletDAO:
    """智能钱包数据访问对象"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def upsert_wallet(self, wallet_data: Dict[str, Any]) -> SmartWallet:
        """
        插入或更新钱包数据
        如果 address 已存在则更新，否则插入
        
        Args:
            wallet_data: 钱包数据字典
        
        Returns:
            SmartWallet 对象
        """
        # 准备数据
        data = {
            'address': wallet_data.get('address'),
            'wallet_address': wallet_data.get('wallet_address', wallet_data.get('address')),
            'name': wallet_data.get('name'),
            'last_active': wallet_data.get('last_active', 0),
            'chain': wallet_data.get('chain', 'SOL'),
            'balance': wallet_data.get('balance', 0),
            'sol_balance': wallet_data.get('sol_balance', 0),
            'updated_at': datetime.now(),
            
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
            
            # 社交
            'followed_count': wallet_data.get('followed_count', 0),
            'remark_count': wallet_data.get('remark_count', 0)
        }
        
        # 使用 MySQL 的 INSERT ... ON DUPLICATE KEY UPDATE
        stmt = insert(SmartWallet).values(**data)
        
        # 更新时排除主键和唯一键
        update_dict = {k: v for k, v in data.items() if k not in ['id', 'address']}
        stmt = stmt.on_duplicate_key_update(**update_dict)
        
        self.session.execute(stmt)
        
        # 查询返回
        return self.session.query(SmartWallet).filter(
            SmartWallet.address == data['address']
        ).first()
    
    def batch_upsert(self, wallets: List[Dict[str, Any]]) -> int:
        """批量插入或更新钱包"""
        count = 0
        for wallet in wallets:
            try:
                self.upsert_wallet(wallet)
                count += 1
            except Exception as e:
                print(f"⚠️ 插入钱包 {wallet.get('address')} 失败: {e}")
        return count
    
    def get_by_address(self, address: str) -> Optional[SmartWallet]:
        """根据地址查询钱包"""
        return self.session.query(SmartWallet).filter(
            SmartWallet.address == address
        ).first()
    
    def get_all_smart_money(self, limit: int = 100) -> List[SmartWallet]:
        """获取所有聪明钱钱包"""
        return self.session.query(SmartWallet).filter(
            SmartWallet.is_smart_money == 1
        ).order_by(desc(SmartWallet.pnl_7d)).limit(limit).all()
    
    def get_all_kol(self, limit: int = 50) -> List[SmartWallet]:
        """获取所有KOL钱包"""
        return self.session.query(SmartWallet).filter(
            SmartWallet.is_kol == 1
        ).order_by(desc(SmartWallet.pnl_7d)).limit(limit).all()
    
    def get_hot_followed(self, limit: int = 50) -> List[SmartWallet]:
        """获取热门追踪钱包"""
        return self.session.query(SmartWallet).filter(
            SmartWallet.is_hot_followed == 1
        ).order_by(desc(SmartWallet.followed_count)).limit(limit).all()
    
    def get_hot_remarked(self, limit: int = 50) -> List[SmartWallet]:
        """获取热门备注钱包"""
        return self.session.query(SmartWallet).filter(
            SmartWallet.is_hot_remarked == 1
        ).order_by(desc(SmartWallet.remark_count)).limit(limit).all()
    
    def get_top_pnl_7d(self, limit: int = 100) -> List[SmartWallet]:
        """获取7日盈利TOP钱包"""
        return self.session.query(SmartWallet).order_by(
            desc(SmartWallet.pnl_7d)
        ).limit(limit).all()
    
    def get_top_win_rate_7d(self, limit: int = 100, min_tx: int = 10) -> List[SmartWallet]:
        """获取7日胜率TOP钱包（需要最小交易次数）"""
        return self.session.query(SmartWallet).filter(
            SmartWallet.tx_count_7d >= min_tx
        ).order_by(desc(SmartWallet.win_rate_7d)).limit(limit).all()
    
    def search_by_keyword(self, keyword: str, limit: int = 20) -> List[SmartWallet]:
        """搜索钱包（地址或推特）"""
        return self.session.query(SmartWallet).filter(
            or_(
                SmartWallet.address.like(f'%{keyword}%'),
                SmartWallet.twitter_handle.like(f'%{keyword}%')
            )
        ).limit(limit).all()
    
    def count_total(self) -> int:
        """统计总钱包数"""
        return self.session.query(SmartWallet).count()
    
    def count_smart_money(self) -> int:
        """统计聪明钱数量"""
        return self.session.query(SmartWallet).filter(
            SmartWallet.is_smart_money == 1
        ).count()
    
    def count_kol(self) -> int:
        """统计KOL数量"""
        return self.session.query(SmartWallet).filter(
            SmartWallet.is_kol == 1
        ).count()
    
    def delete_by_address(self, address: str) -> bool:
        """删除钱包（谨慎使用）"""
        wallet = self.get_by_address(address)
        if wallet:
            self.session.delete(wallet)
            return True
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_wallets': self.count_total(),
            'smart_money_count': self.count_smart_money(),
            'kol_count': self.count_kol(),
            'avg_pnl_7d': self.session.query(func.avg(SmartWallet.pnl_7d)).scalar() or 0,
            'avg_win_rate_7d': self.session.query(func.avg(SmartWallet.win_rate_7d)).scalar() or 0,
            'max_pnl_7d': self.session.query(func.max(SmartWallet.pnl_7d)).scalar() or 0,
            'min_pnl_7d': self.session.query(func.min(SmartWallet.pnl_7d)).scalar() or 0
        }
