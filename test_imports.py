#!/usr/bin/env python
"""
快速测试脚本 - 验证所有模块是否能正常导入
"""
import sys

def test_imports():
    """测试所有模块导入"""
    print("=" * 60)
    print("测试模块导入")
    print("=" * 60)
    
    tests = [
        ("config.database", "数据库配置"),
        ("models.smart_wallet", "SmartWallet 实体"),
        ("models.birdeye_transaction", "BirdeyeWalletTransaction 实体"),
        ("dao.smart_wallet_dao", "SmartWallet DAO"),
        ("dao.birdeye_transaction_dao", "BirdeyeWalletTransaction DAO"),
        ("update_hold_time", "持仓时间计算工具"),
    ]
    
    failed = []
    for module_name, description in tests:
        try:
            __import__(module_name)
            print(f"✓ {description:40} [{module_name}]")
        except Exception as e:
            print(f"✗ {description:40} [{module_name}]")
            print(f"  错误: {str(e)}")
            failed.append((module_name, str(e)))
    
    print("\n" + "=" * 60)
    if not failed:
        print("✓ 所有模块导入成功！")
        print("=" * 60)
        return True
    else:
        print(f"✗ {len(failed)} 个模块导入失败")
        print("=" * 60)
        for module_name, error in failed:
            print(f"\n{module_name}:")
            print(f"  {error}")
        return False


def test_database_config():
    """测试数据库配置"""
    print("\n" + "=" * 60)
    print("测试数据库配置")
    print("=" * 60)
    
    try:
        from config.database import db_config
        print(f"✓ 数据库主机: {db_config.host}")
        print(f"✓ 数据库端口: {db_config.port}")
        print(f"✓ 数据库名称: {db_config.database}")
        print(f"✓ 数据库用户: {db_config.user}")
        return True
    except Exception as e:
        print(f"✗ 数据库配置读取失败: {str(e)}")
        return False


def main():
    """主函数"""
    print("\n🚀 Crypto Analyze - 快速测试\n")
    
    # 测试导入
    imports_ok = test_imports()
    
    # 测试配置
    config_ok = test_database_config()
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    if imports_ok and config_ok:
        print("✓ 所有测试通过！")
        print("\n下一步：")
        print("  1. 确保数据库已创建: mysql -u root -p crypto_db < database_schema.sql")
        print("  2. 测试数据库连接: python test_connection.py")
        print("  3. 运行示例: python examples.py")
        print("  4. 测试持仓时间计算: python update_hold_time.py test")
        return 0
    else:
        print("✗ 部分测试失败，请检查配置")
        return 1


if __name__ == "__main__":
    sys.exit(main())
