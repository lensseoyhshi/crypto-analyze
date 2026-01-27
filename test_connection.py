"""
测试数据库连接
用于验证配置是否正确
"""
import sys
from config.database import db_config


def test_connection():
    """测试数据库连接"""
    print("=" * 50)
    print("测试数据库连接")
    print("=" * 50)
    
    try:
        print("\n1. 读取配置...")
        print(f"   数据库主机: {db_config.host}")
        print(f"   端口: {db_config.port}")
        print(f"   用户名: {db_config.user}")
        print(f"   数据库名: {db_config.database}")
        
        print("\n2. 创建数据库引擎...")
        engine = db_config.get_engine()
        print("   ✓ 引擎创建成功")
        
        print("\n3. 测试连接...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("   ✓ 数据库连接成功")
        
        print("\n4. 检查表是否存在...")
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        required_tables = ['smart_wallets', 'birdeye_wallet_transactions']
        for table in required_tables:
            if table in tables:
                print(f"   ✓ 表 '{table}' 存在")
            else:
                print(f"   ✗ 表 '{table}' 不存在（需要创建）")
        
        print("\n" + "=" * 50)
        print("✓ 测试完成")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"\n✗ 错误: {str(e)}")
        print("\n请检查：")
        print("  1. .env 文件是否存在且配置正确")
        print("  2. MySQL 服务是否运行")
        print("  3. 数据库用户名和密码是否正确")
        print("  4. 数据库是否已创建")
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
