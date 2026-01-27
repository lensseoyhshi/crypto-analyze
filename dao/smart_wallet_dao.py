"""
SmartWallet DAO 数据访问对象
提供对 smart_wallets 表的 CRUD 操作
"""
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from models.smart_wallet import SmartWallet
from config.database import db_config


class SmartWalletDAO:
    """SmartWallet 数据访问对象"""
    
    def __init__(self, session: Optional[Session] = None):
        """
        初始化 DAO
        :param session: 数据库 Session，如果不提供则自动创建
        """
        self.session = session or db_config.get_session()
        self._auto_close = session is None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._auto_close:
            self.session.close()
    
    def create(self, wallet: SmartWallet) -> SmartWallet:
        """
        创建新的钱包记录
        :param wallet: SmartWallet 实体对象
        :return: 创建后的对象（包含生成的 ID）
        """
        try:
            self.session.add(wallet)
            self.session.commit()
            self.session.refresh(wallet)
            return wallet
        except SQLAlchemyError as e:
            self.session.rollback()
            raise Exception(f"创建钱包记录失败: {str(e)}")
    
    def create_from_dict(self, data: Dict[str, Any]) -> SmartWallet:
        """
        从字典创建钱包记录
        :param data: 包含钱包信息的字典
        :return: 创建后的对象
        """
        wallet = SmartWallet(**data)
        return self.create(wallet)
    
    def batch_create(self, wallets: List[SmartWallet]) -> List[SmartWallet]:
        """
        批量创建钱包记录
        :param wallets: SmartWallet 对象列表
        :return: 创建后的对象列表
        """
        try:
            self.session.add_all(wallets)
            self.session.commit()
            for wallet in wallets:
                self.session.refresh(wallet)
            return wallets
        except SQLAlchemyError as e:
            self.session.rollback()
            raise Exception(f"批量创建钱包记录失败: {str(e)}")
    
    def get_by_id(self, wallet_id: int) -> Optional[SmartWallet]:
        """
        根据 ID 查询钱包
        :param wallet_id: 钱包 ID
        :return: SmartWallet 对象或 None
        """
        try:
            return self.session.get(SmartWallet, wallet_id)
        except SQLAlchemyError as e:
            raise Exception(f"查询钱包失败: {str(e)}")
    
    def get_by_address(self, address: str) -> Optional[SmartWallet]:
        """
        根据地址查询钱包
        :param address: 钱包地址
        :return: SmartWallet 对象或 None
        """
        try:
            stmt = select(SmartWallet).where(SmartWallet.address == address)
            return self.session.execute(stmt).scalar_one_or_none()
        except SQLAlchemyError as e:
            raise Exception(f"根据地址查询钱包失败: {str(e)}")
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[SmartWallet]:
        """
        查询所有钱包（分页）
        :param limit: 每页数量
        :param offset: 偏移量
        :return: SmartWallet 列表
        """
        try:
            stmt = select(SmartWallet).limit(limit).offset(offset)
            return list(self.session.execute(stmt).scalars())
        except SQLAlchemyError as e:
            raise Exception(f"查询所有钱包失败: {str(e)}")
    
    def update(self, wallet_id: int, data: Dict[str, Any]) -> Optional[SmartWallet]:
        """
        更新钱包信息
        :param wallet_id: 钱包 ID
        :param data: 要更新的字段字典
        :return: 更新后的对象或 None
        """
        try:
            stmt = (
                update(SmartWallet)
                .where(SmartWallet.id == wallet_id)
                .values(**data)
            )
            self.session.execute(stmt)
            self.session.commit()
            return self.get_by_id(wallet_id)
        except SQLAlchemyError as e:
            self.session.rollback()
            raise Exception(f"更新钱包信息失败: {str(e)}")
    
    def update_by_address(self, address: str, data: Dict[str, Any]) -> Optional[SmartWallet]:
        """
        根据地址更新钱包信息
        :param address: 钱包地址
        :param data: 要更新的字段字典
        :return: 更新后的对象或 None
        """
        try:
            stmt = (
                update(SmartWallet)
                .where(SmartWallet.address == address)
                .values(**data)
            )
            self.session.execute(stmt)
            self.session.commit()
            return self.get_by_address(address)
        except SQLAlchemyError as e:
            self.session.rollback()
            raise Exception(f"根据地址更新钱包信息失败: {str(e)}")
    
    def delete(self, wallet_id: int) -> bool:
        """
        删除钱包记录
        :param wallet_id: 钱包 ID
        :return: 是否删除成功
        """
        try:
            stmt = delete(SmartWallet).where(SmartWallet.id == wallet_id)
            result = self.session.execute(stmt)
            self.session.commit()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            self.session.rollback()
            raise Exception(f"删除钱包记录失败: {str(e)}")
    
    def delete_by_address(self, address: str) -> bool:
        """
        根据地址删除钱包记录
        :param address: 钱包地址
        :return: 是否删除成功
        """
        try:
            stmt = delete(SmartWallet).where(SmartWallet.address == address)
            result = self.session.execute(stmt)
            self.session.commit()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            self.session.rollback()
            raise Exception(f"根据地址删除钱包记录失败: {str(e)}")
    
    # ==================== 高级查询方法 ====================
    
    def get_smart_money_wallets(self, limit: int = 100, offset: int = 0) -> List[SmartWallet]:
        """
        查询所有聪明钱钱包
        :param limit: 每页数量
        :param offset: 偏移量
        :return: SmartWallet 列表
        """
        try:
            stmt = (
                select(SmartWallet)
                .where(SmartWallet.is_smart_money == 1)
                .limit(limit)
                .offset(offset)
            )
            return list(self.session.execute(stmt).scalars())
        except SQLAlchemyError as e:
            raise Exception(f"查询聪明钱钱包失败: {str(e)}")
    
    def get_kol_wallets(self, limit: int = 100, offset: int = 0) -> List[SmartWallet]:
        """
        查询所有 KOL 钱包
        :param limit: 每页数量
        :param offset: 偏移量
        :return: SmartWallet 列表
        """
        try:
            stmt = (
                select(SmartWallet)
                .where(SmartWallet.is_kol == 1)
                .limit(limit)
                .offset(offset)
            )
            return list(self.session.execute(stmt).scalars())
        except SQLAlchemyError as e:
            raise Exception(f"查询 KOL 钱包失败: {str(e)}")
    
    def get_top_performers_7d(
        self, 
        limit: int = 10, 
        order_by: str = 'pnl_7d'
    ) -> List[SmartWallet]:
        """
        查询 7 日表现最好的钱包
        :param limit: 返回数量
        :param order_by: 排序字段 (pnl_7d, pnl_7d_roi, win_rate_7d)
        :return: SmartWallet 列表
        """
        try:
            order_field = getattr(SmartWallet, order_by, SmartWallet.pnl_7d)
            stmt = (
                select(SmartWallet)
                .order_by(order_field.desc())
                .limit(limit)
            )
            return list(self.session.execute(stmt).scalars())
        except SQLAlchemyError as e:
            raise Exception(f"查询 7 日表现最好的钱包失败: {str(e)}")
    
    def get_top_performers_30d(
        self, 
        limit: int = 10, 
        order_by: str = 'pnl_30d'
    ) -> List[SmartWallet]:
        """
        查询 30 日表现最好的钱包
        :param limit: 返回数量
        :param order_by: 排序字段 (pnl_30d, pnl_30d_roi, win_rate_30d)
        :return: SmartWallet 列表
        """
        try:
            order_field = getattr(SmartWallet, order_by, SmartWallet.pnl_30d)
            stmt = (
                select(SmartWallet)
                .order_by(order_field.desc())
                .limit(limit)
            )
            return list(self.session.execute(stmt).scalars())
        except SQLAlchemyError as e:
            raise Exception(f"查询 30 日表现最好的钱包失败: {str(e)}")
    
    def filter_wallets(
        self,
        is_smart_money: Optional[bool] = None,
        is_kol: Optional[bool] = None,
        is_whale: Optional[bool] = None,
        is_sniper: Optional[bool] = None,
        min_pnl_7d: Optional[Decimal] = None,
        min_win_rate_7d: Optional[Decimal] = None,
        uses_trojan: Optional[bool] = None,
        uses_bullx: Optional[bool] = None,
        uses_photon: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[SmartWallet]:
        """
        根据多个条件筛选钱包
        :return: SmartWallet 列表
        """
        try:
            conditions = []
            
            if is_smart_money is not None:
                conditions.append(SmartWallet.is_smart_money == (1 if is_smart_money else 0))
            if is_kol is not None:
                conditions.append(SmartWallet.is_kol == (1 if is_kol else 0))
            if is_whale is not None:
                conditions.append(SmartWallet.is_whale == (1 if is_whale else 0))
            if is_sniper is not None:
                conditions.append(SmartWallet.is_sniper == (1 if is_sniper else 0))
            if min_pnl_7d is not None:
                conditions.append(SmartWallet.pnl_7d >= min_pnl_7d)
            if min_win_rate_7d is not None:
                conditions.append(SmartWallet.win_rate_7d >= min_win_rate_7d)
            if uses_trojan is not None:
                conditions.append(SmartWallet.uses_trojan == (1 if uses_trojan else 0))
            if uses_bullx is not None:
                conditions.append(SmartWallet.uses_bullx == (1 if uses_bullx else 0))
            if uses_photon is not None:
                conditions.append(SmartWallet.uses_photon == (1 if uses_photon else 0))
            
            stmt = select(SmartWallet)
            if conditions:
                stmt = stmt.where(and_(*conditions))
            
            stmt = stmt.limit(limit).offset(offset)
            return list(self.session.execute(stmt).scalars())
        except SQLAlchemyError as e:
            raise Exception(f"筛选钱包失败: {str(e)}")
    
    def count_all(self) -> int:
        """
        统计总钱包数
        :return: 钱包总数
        """
        try:
            stmt = select(func.count()).select_from(SmartWallet)
            return self.session.execute(stmt).scalar()
        except SQLAlchemyError as e:
            raise Exception(f"统计钱包总数失败: {str(e)}")
    
    def count_by_type(self) -> Dict[str, int]:
        """
        统计各类型钱包数量
        :return: 包含各类型数量的字典
        """
        try:
            result = {
                'smart_money': 0,
                'kol': 0,
                'whale': 0,
                'sniper': 0,
            }
            
            stmt_smart = select(func.count()).select_from(SmartWallet).where(SmartWallet.is_smart_money == 1)
            result['smart_money'] = self.session.execute(stmt_smart).scalar()
            
            stmt_kol = select(func.count()).select_from(SmartWallet).where(SmartWallet.is_kol == 1)
            result['kol'] = self.session.execute(stmt_kol).scalar()
            
            stmt_whale = select(func.count()).select_from(SmartWallet).where(SmartWallet.is_whale == 1)
            result['whale'] = self.session.execute(stmt_whale).scalar()
            
            stmt_sniper = select(func.count()).select_from(SmartWallet).where(SmartWallet.is_sniper == 1)
            result['sniper'] = self.session.execute(stmt_sniper).scalar()
            
            return result
        except SQLAlchemyError as e:
            raise Exception(f"统计各类型钱包数量失败: {str(e)}")
