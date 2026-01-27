"""
使用示例文件
演示如何使用 SmartWallet 和 BirdeyeWalletTransaction 的实体类和 DAO
"""
from datetime import datetime, timedelta
from decimal import Decimal

from dao.smart_wallet_dao import SmartWalletDAO
from dao.birdeye_transaction_dao import BirdeyeWalletTransactionDAO
from models.smart_wallet import SmartWallet
from models.birdeye_transaction import BirdeyeWalletTransaction


def example_smart_wallet_crud():
    """SmartWallet CRUD 操作示例"""
    print("=" * 50)
    print("SmartWallet CRUD 操作示例")
    print("=" * 50)
    
    # 使用上下文管理器自动管理 Session
    with SmartWalletDAO() as dao:
        # 1. 创建钱包
        print("\n1. 创建新钱包...")
        wallet = SmartWallet(
            address="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
            chain="SOL",
            balance=Decimal("10.5000"),
            is_smart_money=1,
            is_sniper=1,
            pnl_7d=Decimal("1500.50"),
            pnl_7d_roi=Decimal("25.30"),
            win_rate_7d=Decimal("75.50"),
            tx_count_7d=150,
            volume_7d=Decimal("50000.00")
        )
        created_wallet = dao.create(wallet)
        print(f"创建成功: {created_wallet}")
        
        # 2. 根据 ID 查询
        print(f"\n2. 根据 ID 查询钱包 (ID={created_wallet.id})...")
        found_wallet = dao.get_by_id(created_wallet.id)
        print(f"查询结果: {found_wallet}")
        
        # 3. 根据地址查询
        print(f"\n3. 根据地址查询钱包...")
        wallet_by_address = dao.get_by_address("7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU")
        print(f"查询结果: {wallet_by_address}")
        
        # 4. 更新钱包信息
        print(f"\n4. 更新钱包信息...")
        update_data = {
            "balance": Decimal("15.0000"),
            "pnl_7d": Decimal("2000.00"),
            "is_kol": 1,
            "twitter_handle": "@crypto_trader"
        }
        updated_wallet = dao.update(created_wallet.id, update_data)
        print(f"更新后: {updated_wallet}")
        print(f"新余额: {updated_wallet.balance}, 新PNL: {updated_wallet.pnl_7d}")
        
        # 5. 删除钱包
        print(f"\n5. 删除钱包...")
        success = dao.delete(created_wallet.id)
        print(f"删除{'成功' if success else '失败'}")


def example_smart_wallet_advanced_queries():
    """SmartWallet 高级查询示例"""
    print("\n" + "=" * 50)
    print("SmartWallet 高级查询示例")
    print("=" * 50)
    
    with SmartWalletDAO() as dao:
        # 1. 查询所有聪明钱
        print("\n1. 查询前 5 个聪明钱钱包...")
        smart_wallets = dao.get_smart_money_wallets(limit=5)
        for wallet in smart_wallets:
            print(f"  - {wallet.address}: PNL 7D = {wallet.pnl_7d}")
        
        # 2. 查询 7 日表现最好的钱包
        print("\n2. 查询 7 日 PNL 最高的前 10 个钱包...")
        top_performers = dao.get_top_performers_7d(limit=10, order_by='pnl_7d')
        for i, wallet in enumerate(top_performers, 1):
            print(f"  {i}. {wallet.address}: PNL={wallet.pnl_7d}, ROI={wallet.pnl_7d_roi}%")
        
        # 3. 条件筛选
        print("\n3. 筛选: 聪明钱 + 狙击手 + 7日PNL>1000...")
        filtered = dao.filter_wallets(
            is_smart_money=True,
            is_sniper=True,
            min_pnl_7d=Decimal("1000.00"),
            limit=10
        )
        print(f"找到 {len(filtered)} 个符合条件的钱包")
        for wallet in filtered:
            print(f"  - {wallet.address}: PNL={wallet.pnl_7d}")
        
        # 4. 统计各类型钱包数量
        print("\n4. 统计各类型钱包数量...")
        counts = dao.count_by_type()
        print(f"  聪明钱: {counts['smart_money']}")
        print(f"  KOL: {counts['kol']}")
        print(f"  巨鲸: {counts['whale']}")
        print(f"  狙击手: {counts['sniper']}")


def example_birdeye_transaction_crud():
    """BirdeyeWalletTransaction CRUD 操作示例"""
    print("\n" + "=" * 50)
    print("BirdeyeWalletTransaction CRUD 操作示例")
    print("=" * 50)
    
    with BirdeyeWalletTransactionDAO() as dao:
        # 1. 从字典创建交易记录
        print("\n1. 创建交易记录...")
        tx_data = {
            "tx_hash": "5YNmS1R9nNSCDzb1a7Q3vwmU7Z8aKPPj2nXN9dNKZxQEbZ8aKPPj2nXN9dNKZxQE",
            "block_number": 150000000,
            "block_time": datetime.now(),
            "status": True,
            "from": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
            "to": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            "fee": 5000,
            "main_action": "SWAP",
            "balance_change": [
                {"token": "SOL", "amount": -0.5},
                {"token": "USDC", "amount": 100}
            ],
            "token_transfers": [
                {
                    "from": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
                    "to": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                    "token": "USDC",
                    "amount": 100
                }
            ],
            "block_time_unix": int(datetime.now().timestamp())
        }
        
        created_tx = dao.create_from_dict(tx_data)
        print(f"创建成功: ID={created_tx.id}, Hash={created_tx.tx_hash}")
        
        # 2. 根据交易哈希查询
        print(f"\n2. 根据交易哈希查询...")
        found_tx = dao.get_by_tx_hash(tx_data["tx_hash"])
        print(f"查询结果: {found_tx}")
        
        # 3. 更新交易
        print(f"\n3. 更新交易状态...")
        updated_tx = dao.update(created_tx.id, {"status": False})
        print(f"更新后状态: {updated_tx.status}")
        
        # 4. Upsert 操作（如果存在则更新，不存在则创建）
        print(f"\n4. Upsert 操作...")
        tx_data["status"] = True  # 改回 True
        tx_data["fee"] = 6000  # 修改手续费
        upserted_tx = dao.upsert(tx_data)
        print(f"Upsert 后: ID={upserted_tx.id}, Fee={upserted_tx.fee}")
        
        # 5. 删除交易
        print(f"\n5. 删除交易...")
        success = dao.delete(created_tx.id)
        print(f"删除{'成功' if success else '失败'}")


def example_birdeye_transaction_queries():
    """BirdeyeWalletTransaction 高级查询示例"""
    print("\n" + "=" * 50)
    print("BirdeyeWalletTransaction 高级查询示例")
    print("=" * 50)
    
    wallet_address = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
    
    with BirdeyeWalletTransactionDAO() as dao:
        # 1. 查询钱包交易历史
        print(f"\n1. 查询钱包 {wallet_address[:10]}... 的最近 10 笔交易...")
        transactions = dao.get_by_wallet(wallet_address, limit=10)
        print(f"找到 {len(transactions)} 笔交易")
        for tx in transactions:
            print(f"  - {tx.tx_hash[:20]}... | {tx.main_action} | {tx.block_time}")
        
        # 2. 查询最近 7 天的交易
        print(f"\n2. 查询钱包最近 7 天的交易...")
        start_time = datetime.now() - timedelta(days=7)
        end_time = datetime.now()
        recent_txs = dao.get_by_wallet_and_time_range(
            wallet_address, 
            start_time, 
            end_time, 
            limit=100
        )
        print(f"最近 7 天共 {len(recent_txs)} 笔交易")
        
        # 3. 按动作类型查询
        print(f"\n3. 查询 SWAP 类型的交易...")
        swap_txs = dao.get_by_action("SWAP", limit=10)
        print(f"找到 {len(swap_txs)} 笔 SWAP 交易")
        
        # 4. 统计钱包交易数据
        print(f"\n4. 统计钱包 7 日交易数据...")
        stats = dao.get_wallet_statistics(wallet_address, days=7)
        print(f"  总交易数: {stats['total_transactions']}")
        print(f"  成功交易: {stats['success_transactions']}")
        print(f"  失败交易: {stats['failed_transactions']}")
        print(f"  成功率: {stats['success_rate']:.2f}%")
        print(f"  总手续费: {stats['total_fee']} Lamports")
        
        # 5. 获取交易动作分布
        print(f"\n5. 获取钱包交易动作分布...")
        distribution = dao.get_action_distribution(wallet_address, days=7)
        for action, count in distribution.items():
            print(f"  {action}: {count} 笔")


def example_batch_operations():
    """批量操作示例"""
    print("\n" + "=" * 50)
    print("批量操作示例")
    print("=" * 50)
    
    # 批量创建钱包
    print("\n1. 批量创建钱包...")
    wallets = [
        SmartWallet(
            address=f"Wallet{i}{'x' * 37}",
            chain="SOL",
            balance=Decimal(str(10 + i)),
            is_smart_money=1 if i % 2 == 0 else 0,
            pnl_7d=Decimal(str(1000 + i * 100)),
            win_rate_7d=Decimal(str(60 + i))
        )
        for i in range(1, 6)
    ]
    
    with SmartWalletDAO() as dao:
        created = dao.batch_create(wallets)
        print(f"批量创建了 {len(created)} 个钱包")
        for wallet in created:
            print(f"  - ID={wallet.id}, Address={wallet.address[:15]}..., PNL={wallet.pnl_7d}")
        
        # 清理测试数据
        print("\n2. 清理测试数据...")
        for wallet in created:
            dao.delete(wallet.id)
        print("清理完成")


def example_to_dict():
    """实体转字典示例"""
    print("\n" + "=" * 50)
    print("实体转字典示例")
    print("=" * 50)
    
    with SmartWalletDAO() as wallet_dao:
        print("\n1. 获取钱包并转为字典...")
        wallets = wallet_dao.get_smart_money_wallets(limit=1)
        if wallets:
            wallet_dict = wallets[0].to_dict()
            print("钱包字典:")
            for key, value in wallet_dict.items():
                print(f"  {key}: {value}")
    
    with BirdeyeWalletTransactionDAO() as tx_dao:
        print("\n2. 获取交易并转为字典...")
        transactions = tx_dao.get_recent_transactions(days=1, limit=1)
        if transactions:
            tx_dict = transactions[0].to_dict()
            print("交易字典:")
            for key, value in tx_dict.items():
                if key not in ['balance_change', 'contract_label', 'token_transfers']:
                    print(f"  {key}: {value}")


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("开始运行示例...")
    print("=" * 70)
    
    try:
        # SmartWallet 示例
        example_smart_wallet_crud()
        example_smart_wallet_advanced_queries()
        
        # BirdeyeWalletTransaction 示例
        example_birdeye_transaction_crud()
        example_birdeye_transaction_queries()
        
        # 其他示例
        example_batch_operations()
        example_to_dict()
        
        print("\n" + "=" * 70)
        print("所有示例运行完成！")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 提示：在运行前请确保：
    # 1. 已安装所有依赖: pip install -r requirements.txt
    # 2. 已配置 .env 文件（参考 .env.example）
    # 3. 数据库表已创建
    
    print("\n⚠️  注意：运行此示例前请确保：")
    print("   1. 已安装依赖: pip install -r requirements.txt")
    print("   2. 已创建 .env 文件并配置数据库连接")
    print("   3. 数据库表已创建（使用提供的 SQL 语句）")
    print("\n按 Enter 继续运行示例，Ctrl+C 退出...")
    
    try:
        input()
        main()
    except KeyboardInterrupt:
        print("\n\n已取消运行")
