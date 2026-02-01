"""
数据库配置模块
"""
import os
from typing import Optional
from dotenv import load_dotenv
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.pool import QueuePool

# 加载环境变量
load_dotenv()


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass


class DatabaseConfig:
    """数据库配置类"""
    
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = int(os.getenv('DB_PORT', 3306))
        self.user = os.getenv('DB_USER', 'root')
        self.password = os.getenv('DB_PASSWORD', '12345678')
        self.database = os.getenv('DB_NAME', 'crypto-analyze')
        self.charset = os.getenv('DB_CHARSET', 'utf8mb4')
        
        # 构建数据库连接 URL
        self.database_url = (
            f"mysql+pymysql://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}?"
            f"charset={self.charset}"
        )
        
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
    
    def get_engine(self) -> Engine:
        """获取数据库引擎（单例模式）"""
        if self._engine is None:
            self._engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=5,
                pool_recycle=3600,
                pool_pre_ping=True,
                echo=False  # 设置为 True 可以打印 SQL 语句
            )
        return self._engine
    
    def get_session_factory(self) -> sessionmaker:
        """获取 Session 工厂"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.get_engine(),
                autocommit=False,
                autoflush=False
            )
        return self._session_factory
    
    def get_session(self) -> Session:
        """获取数据库 Session"""
        return self.get_session_factory()()
    
    def close_engine(self):
        """关闭数据库引擎"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None


# 全局数据库配置实例
db_config = DatabaseConfig()


def get_db_session() -> Session:
    """
    获取数据库 Session 的便捷函数
    使用上下文管理器:
    
    with get_db_session() as session:
        # 执行数据库操作
        pass
    """
    session = db_config.get_session()
    try:
        yield session
    finally:
        session.close()


def get_session() -> Session:
    """
    获取数据库 Session（直接返回，不使用上下文管理器）
    用于需要手动管理 session 生命周期的场景
    
    注意：使用完毕后需要手动调用 session.close()
    """
    return db_config.get_session()
