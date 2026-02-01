#!/usr/bin/env python3
"""
测试快照逻辑
验证：
1. smart_wallets_snapshot: 当日&钱包地址存在则跳过，不存在则插入
2. smart_wallets: 钱包地址存在则更新，不存在则插入
"""
from datetime import date
from config.database import get_session
from dao.smart_wallet_dao import SmartWalletDAO
from dao.smart_wallet_snapshot_dao import SmartWalletSnapshotDAO


def test_snapshot_insert_logic():
    """测试快照表的插入逻辑"""
    session = get_session()
    
    try:
        snapshot_dao = SmartWalletSnapshotDAO(session)
        wallet_dao = SmartWalletDAO(session)
        
        # 测试钱包数据
        test_wallet = {
            'address': 'TestWallet123456789012345678901234567890',
            'chain': 'SOL',
            'balance': 100.5,
            'is_smart_money': 1,
            'pnl_7d': 1000.50,
            'win_rate_7d': 75.5,
            'tx_count_7d': 20,
        }
        
        today = date.today()
        
        print("\n" + "="*70)
        print("测试 1: 第一次插入快照（应该成功插入）")
        print("="*70)
        
        # 先清理可能存在的测试数据
        session.query(snapshot_dao.session.query(type(snapshot_dao.session.query(
            __import__('models.smart_wallet_snapshot', fromlist=['SmartWalletSnapshot']).SmartWalletSnapshot
        ).filter_by(address=test_wallet['address'], snapshot_date=today).first().__class__).filter_by(
            address=test_wallet['address'], snapshot_date=today
        ).delete(synchronize_session=False))
        session.commit()
        
        result1 = snapshot_dao.upsert_snapshot(test_wallet, today)
        session.commit()
        
        if result1 is not None:
            print("✅ 第一次插入成功")
            print(f"   - 钱包地址: {result1.address}")
            print(f"   - 快照日期: {result1.snapshot_date}")
            print(f"   - PNL 7D: {result1.pnl_7d}")
        else:
            print("❌ 第一次插入失败（不应该发生）")
            return
        
        print("\n" + "="*70)
        print("测试 2: 第二次插入相同快照（应该跳过，不更新）")
        print("="*70)
        
        # 修改数据再次插入
        test_wallet['pnl_7d'] = 2000.00  # 修改盈利
        test_wallet['win_rate_7d'] = 85.0  # 修改胜率
        
        result2 = snapshot_dao.upsert_snapshot(test_wallet, today)
        session.commit()
        
        if result2 is None:
            print("✅ 第二次插入被正确跳过（已存在）")
            
            # 验证数据没有被更新
            from models.smart_wallet_snapshot import SmartWalletSnapshot
            verify = session.query(SmartWalletSnapshot).filter_by(
                address=test_wallet['address'],
                snapshot_date=today
            ).first()
            
            print(f"   - 数据库中的 PNL 7D: {verify.pnl_7d} (应该还是 1000.50)")
            if float(verify.pnl_7d) == 1000.50:
                print("   ✅ 数据未被更新，符合预期")
            else:
                print(f"   ❌ 数据被更新了，不符合预期（原值: 1000.50, 现值: {verify.pnl_7d}）")
        else:
            print("❌ 第二次插入没有被跳过（不符合预期）")
        
        print("\n" + "="*70)
        print("测试 3: 测试 smart_wallets 的 upsert 逻辑")
        print("="*70)
        
        # 第一次插入
        print("\n3.1 第一次插入钱包（应该插入）")
        result3 = wallet_dao.upsert_wallet(test_wallet)
        session.commit()
        print(f"✅ 插入成功，PNL 7D = {result3.pnl_7d}")
        
        # 第二次更新
        print("\n3.2 第二次更新钱包（应该更新）")
        test_wallet['pnl_7d'] = 3000.00
        result4 = wallet_dao.upsert_wallet(test_wallet)
        session.commit()
        print(f"✅ 更新成功，PNL 7D = {result4.pnl_7d} (应该是 3000.00)")
        
        if float(result4.pnl_7d) == 3000.00:
            print("   ✅ 数据被正确更新")
        else:
            print(f"   ❌ 数据更新失败（期望: 3000.00, 实际: {result4.pnl_7d}）")
        
        print("\n" + "="*70)
        print("测试完成！清理测试数据...")
        print("="*70)
        
        # 清理测试数据
        from models.smart_wallet_snapshot import SmartWalletSnapshot
        from models.smart_wallet import SmartWallet
        
        session.query(SmartWalletSnapshot).filter_by(
            address=test_wallet['address']
        ).delete(synchronize_session=False)
        
        session.query(SmartWallet).filter_by(
            address=test_wallet['address']
        ).delete(synchronize_session=False)
        
        session.commit()
        print("✅ 测试数据已清理\n")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == '__main__':
    test_snapshot_insert_logic()
