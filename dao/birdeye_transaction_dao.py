"""
BirdeyeWalletTransaction DAO 数据访问对象
提供对 birdeye_wallet_transactions 表的 CRUD 操作
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, func, and_, or_, desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import json

from models.birdeye_transaction import BirdeyeWalletTransaction
from config.database import db_config


class BirdeyeWalletTransactionDAO:
    """BirdeyeWalletTransaction 数据访问对象"""
    
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
    
    def create(self, transaction: BirdeyeWalletTransaction) -> BirdeyeWalletTransaction:
        """
        创建新的交易记录
        :param transaction: BirdeyeWalletTransaction 实体对象
        :return: 创建后的对象（包含生成的 ID）
        """
        try:
            self.session.add(transaction)
            self.session.commit()
            self.session.refresh(transaction)
            return transaction
        except SQLAlchemyError as e:
            self.session.rollback()
            raise Exception(f"创建交易记录失败: {str(e)}")
    
    def create_from_dict(self, data: Dict[str, Any]) -> BirdeyeWalletTransaction:
        """
        从字典创建交易记录（自动处理 JSON 字段）
        :param data: 包含交易信息的字典
        :return: 创建后的对象
        """
        # 处理 JSON 字段
        if 'balance_change' in data and isinstance(data['balance_change'], (list, dict)):
            data['balance_change'] = json.dumps(data['balance_change'], ensure_ascii=False)
        if 'contract_label' in data and isinstance(data['contract_label'], (list, dict)):
            data['contract_label'] = json.dumps(data['contract_label'], ensure_ascii=False)
        if 'token_transfers' in data and isinstance(data['token_transfers'], (list, dict)):
            data['token_transfers'] = json.dumps(data['token_transfers'], ensure_ascii=False)
        
        # 处理 from 字段（因为 from 是 Python 关键字）
        if 'from' in data:
            data['from_address'] = data.pop('from')
        
        transaction = BirdeyeWalletTransaction(**data)
        return self.create(transaction)
    
    def batch_create(self, transactions: List[BirdeyeWalletTransaction]) -> List[BirdeyeWalletTransaction]:
        """
        批量创建交易记录
        :param transactions: BirdeyeWalletTransaction 对象列表
        :return: 创建后的对象列表
        """
        try:
            self.session.add_all(transactions)
            self.session.commit()
            for transaction in transactions:
                self.session.refresh(transaction)
            return transactions
        except SQLAlchemyError as e:
            self.session.rollback()
            raise Exception(f"批量创建交易记录失败: {str(e)}")
    
    def upsert(self, data: Dict[str, Any]) -> BirdeyeWalletTransaction:
        """
        插入或更新交易记录（基于 tx_hash 唯一索引）
        :param data: 包含交易信息的字典
        :return: 创建或更新后的对象
        """
        try:
            # 处理 from 字段
            tx_hash = data.get('tx_hash')
            if not tx_hash:
                raise ValueError("tx_hash 不能为空")
            
            # 检查记录是否存在
            existing = self.get_by_tx_hash(tx_hash)
            
            if existing:
                # 更新现有记录
                return self.update(existing.id, data)
            else:
                # 创建新记录
                return self.create_from_dict(data)
        except SQLAlchemyError as e:
            self.session.rollback()
            raise Exception(f"插入或更新交易记录失败: {str(e)}")
    
    def get_by_id(self, transaction_id: int) -> Optional[BirdeyeWalletTransaction]:
        """
        根据 ID 查询交易
        :param transaction_id: 交易 ID
        :return: BirdeyeWalletTransaction 对象或 None
        """
        try:
            return self.session.get(BirdeyeWalletTransaction, transaction_id)
        except SQLAlchemyError as e:
            raise Exception(f"查询交易失败: {str(e)}")
    
    def get_by_tx_hash(self, tx_hash: str) -> Optional[BirdeyeWalletTransaction]:
        """
        根据交易哈希查询交易
        :param tx_hash: 交易哈希
        :return: BirdeyeWalletTransaction 对象或 None
        """
        try:
            stmt = select(BirdeyeWalletTransaction).where(
                BirdeyeWalletTransaction.tx_hash == tx_hash
            )
            return self.session.execute(stmt).scalar_one_or_none()
        except SQLAlchemyError as e:
            raise Exception(f"根据交易哈希查询交易失败: {str(e)}")
    
    def get_by_wallet(
        self, 
        wallet_address: str, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[BirdeyeWalletTransaction]:
        """
        查询指定钱包的交易历史
        :param wallet_address: 钱包地址
        :param limit: 每页数量
        :param offset: 偏移量
        :return: BirdeyeWalletTransaction 列表
        """
        try:
            stmt = (
                select(BirdeyeWalletTransaction)
                .where(BirdeyeWalletTransaction.from_address == wallet_address)
                .order_by(desc(BirdeyeWalletTransaction.block_time))
                .limit(limit)
                .offset(offset)
            )
            return list(self.session.execute(stmt).scalars())
        except SQLAlchemyError as e:
            raise Exception(f"查询钱包交易历史失败: {str(e)}")
    
    def get_by_wallet_and_time_range(
        self,
        wallet_address: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000,
        offset: int = 0
    ) -> List[BirdeyeWalletTransaction]:
        """
        查询指定钱包在指定时间范围内的交易
        :param wallet_address: 钱包地址
        :param start_time: 开始时间
        :param end_time: 结束时间
        :param limit: 每页数量
        :param offset: 偏移量
        :return: BirdeyeWalletTransaction 列表
        """
        try:
            stmt = (
                select(BirdeyeWalletTransaction)
                .where(
                    and_(
                        BirdeyeWalletTransaction.from_address == wallet_address,
                        BirdeyeWalletTransaction.block_time >= start_time,
                        BirdeyeWalletTransaction.block_time <= end_time
                    )
                )
                .order_by(desc(BirdeyeWalletTransaction.block_time))
                .limit(limit)
                .offset(offset)
            )
            return list(self.session.execute(stmt).scalars())
        except SQLAlchemyError as e:
            raise Exception(f"查询钱包时间范围内交易失败: {str(e)}")
    
    def get_by_action(
        self,
        action: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[BirdeyeWalletTransaction]:
        """
        根据主要动作类型查询交易
        :param action: 动作类型
        :param limit: 每页数量
        :param offset: 偏移量
        :return: BirdeyeWalletTransaction 列表
        """
        try:
            stmt = (
                select(BirdeyeWalletTransaction)
                .where(BirdeyeWalletTransaction.main_action == action)
                .order_by(desc(BirdeyeWalletTransaction.block_time))
                .limit(limit)
                .offset(offset)
            )
            return list(self.session.execute(stmt).scalars())
        except SQLAlchemyError as e:
            raise Exception(f"根据动作类型查询交易失败: {str(e)}")
    
    def get_recent_transactions(
        self,
        days: int = 7,
        limit: int = 100,
        offset: int = 0
    ) -> List[BirdeyeWalletTransaction]:
        """
        查询最近 N 天的交易
        :param days: 天数
        :param limit: 每页数量
        :param offset: 偏移量
        :return: BirdeyeWalletTransaction 列表
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            stmt = (
                select(BirdeyeWalletTransaction)
                .where(BirdeyeWalletTransaction.block_time >= cutoff_time)
                .order_by(desc(BirdeyeWalletTransaction.block_time))
                .limit(limit)
                .offset(offset)
            )
            return list(self.session.execute(stmt).scalars())
        except SQLAlchemyError as e:
            raise Exception(f"查询最近交易失败: {str(e)}")
    
    def update(self, transaction_id: int, data: Dict[str, Any]) -> Optional[BirdeyeWalletTransaction]:
        """
        更新交易信息
        :param transaction_id: 交易 ID
        :param data: 要更新的字段字典
        :return: 更新后的对象或 None
        """
        try:
            # 处理 JSON 字段
            if 'balance_change' in data and isinstance(data['balance_change'], (list, dict)):
                data['balance_change'] = json.dumps(data['balance_change'], ensure_ascii=False)
            if 'contract_label' in data and isinstance(data['contract_label'], (list, dict)):
                data['contract_label'] = json.dumps(data['contract_label'], ensure_ascii=False)
            if 'token_transfers' in data and isinstance(data['token_transfers'], (list, dict)):
                data['token_transfers'] = json.dumps(data['token_transfers'], ensure_ascii=False)
            
            # 处理 from 字段
            if 'from' in data:
                data['from_address'] = data.pop('from')
            
            stmt = (
                update(BirdeyeWalletTransaction)
                .where(BirdeyeWalletTransaction.id == transaction_id)
                .values(**data)
            )
            self.session.execute(stmt)
            self.session.commit()
            return self.get_by_id(transaction_id)
        except SQLAlchemyError as e:
            self.session.rollback()
            raise Exception(f"更新交易信息失败: {str(e)}")
    
    def delete(self, transaction_id: int) -> bool:
        """
        删除交易记录
        :param transaction_id: 交易 ID
        :return: 是否删除成功
        """
        try:
            stmt = delete(BirdeyeWalletTransaction).where(
                BirdeyeWalletTransaction.id == transaction_id
            )
            result = self.session.execute(stmt)
            self.session.commit()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            self.session.rollback()
            raise Exception(f"删除交易记录失败: {str(e)}")
    
    def delete_by_tx_hash(self, tx_hash: str) -> bool:
        """
        根据交易哈希删除交易记录
        :param tx_hash: 交易哈希
        :return: 是否删除成功
        """
        try:
            stmt = delete(BirdeyeWalletTransaction).where(
                BirdeyeWalletTransaction.tx_hash == tx_hash
            )
            result = self.session.execute(stmt)
            self.session.commit()
            return result.rowcount > 0
        except SQLAlchemyError as e:
            self.session.rollback()
            raise Exception(f"根据交易哈希删除交易记录失败: {str(e)}")
    
    # ==================== 统计分析方法 ====================
    
    def count_by_wallet(self, wallet_address: str) -> int:
        """
        统计指定钱包的交易数量
        :param wallet_address: 钱包地址
        :return: 交易数量
        """
        try:
            stmt = (
                select(func.count())
                .select_from(BirdeyeWalletTransaction)
                .where(BirdeyeWalletTransaction.from_address == wallet_address)
            )
            return self.session.execute(stmt).scalar()
        except SQLAlchemyError as e:
            raise Exception(f"统计钱包交易数量失败: {str(e)}")
    
    def count_by_action(self, action: str) -> int:
        """
        统计指定动作类型的交易数量
        :param action: 动作类型
        :return: 交易数量
        """
        try:
            stmt = (
                select(func.count())
                .select_from(BirdeyeWalletTransaction)
                .where(BirdeyeWalletTransaction.main_action == action)
            )
            return self.session.execute(stmt).scalar()
        except SQLAlchemyError as e:
            raise Exception(f"统计动作类型交易数量失败: {str(e)}")
    
    def get_wallet_statistics(
        self, 
        wallet_address: str, 
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取钱包的统计数据
        :param wallet_address: 钱包地址
        :param days: 统计天数
        :return: 包含统计数据的字典
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            # 总交易数
            stmt_count = (
                select(func.count())
                .select_from(BirdeyeWalletTransaction)
                .where(
                    and_(
                        BirdeyeWalletTransaction.from_address == wallet_address,
                        BirdeyeWalletTransaction.block_time >= cutoff_time
                    )
                )
            )
            total_count = self.session.execute(stmt_count).scalar()
            
            # 成功交易数
            stmt_success = (
                select(func.count())
                .select_from(BirdeyeWalletTransaction)
                .where(
                    and_(
                        BirdeyeWalletTransaction.from_address == wallet_address,
                        BirdeyeWalletTransaction.block_time >= cutoff_time,
                        BirdeyeWalletTransaction.status == True
                    )
                )
            )
            success_count = self.session.execute(stmt_success).scalar()
            
            # 总手续费
            stmt_fee = (
                select(func.sum(BirdeyeWalletTransaction.fee))
                .select_from(BirdeyeWalletTransaction)
                .where(
                    and_(
                        BirdeyeWalletTransaction.from_address == wallet_address,
                        BirdeyeWalletTransaction.block_time >= cutoff_time
                    )
                )
            )
            total_fee = self.session.execute(stmt_fee).scalar() or 0
            
            return {
                'wallet_address': wallet_address,
                'days': days,
                'total_transactions': total_count,
                'success_transactions': success_count,
                'failed_transactions': total_count - success_count,
                'success_rate': (success_count / total_count * 100) if total_count > 0 else 0,
                'total_fee': total_fee,
            }
        except SQLAlchemyError as e:
            raise Exception(f"获取钱包统计数据失败: {str(e)}")
    
    def get_action_distribution(self, wallet_address: str, days: int = 7) -> Dict[str, int]:
        """
        获取钱包的交易动作分布
        :param wallet_address: 钱包地址
        :param days: 统计天数
        :return: 动作类型和数量的字典
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            stmt = (
                select(
                    BirdeyeWalletTransaction.main_action,
                    func.count(BirdeyeWalletTransaction.id)
                )
                .where(
                    and_(
                        BirdeyeWalletTransaction.from_address == wallet_address,
                        BirdeyeWalletTransaction.block_time >= cutoff_time
                    )
                )
                .group_by(BirdeyeWalletTransaction.main_action)
            )
            
            results = self.session.execute(stmt).all()
            return {action: count for action, count in results if action}
        except SQLAlchemyError as e:
            raise Exception(f"获取交易动作分布失败: {str(e)}")
    
    def exists_by_tx_hash(self, tx_hash: str) -> bool:
        """
        检查交易哈希是否已存在
        :param tx_hash: 交易哈希
        :return: 是否存在
        """
        try:
            stmt = select(func.count()).select_from(BirdeyeWalletTransaction).where(
                BirdeyeWalletTransaction.tx_hash == tx_hash
            )
            count = self.session.execute(stmt).scalar()
            return count > 0
        except SQLAlchemyError as e:
            raise Exception(f"检查交易哈希是否存在失败: {str(e)}")
