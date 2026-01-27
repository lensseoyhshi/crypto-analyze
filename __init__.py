"""
Crypto Analyze - 加密货币钱包分析系统
提供基于 SQLAlchemy 的钱包和交易数据管理
"""

__version__ = "1.0.0"
__author__ = "Crypto Analyze Team"

# 导出主要的类和函数供外部使用
from config.database import Base, DatabaseConfig, db_config, get_db_session
from models.smart_wallet import SmartWallet
from models.birdeye_transaction import BirdeyeWalletTransaction
from dao.smart_wallet_dao import SmartWalletDAO
from dao.birdeye_transaction_dao import BirdeyeWalletTransactionDAO

__all__ = [
    # 配置
    'Base',
    'DatabaseConfig',
    'db_config',
    'get_db_session',
    
    # 实体模型
    'SmartWallet',
    'BirdeyeWalletTransaction',
    
    # DAO
    'SmartWalletDAO',
    'BirdeyeWalletTransactionDAO',
]
