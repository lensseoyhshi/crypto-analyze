#!/usr/bin/env python3
"""
测试数据库操作
验证 smart_wallets 和 smart_wallets_snapshot 表
"""
from config.database import get_session
from dao.smart_wallet_dao import SmartWalletDAO
from dao.smart_wallet_snapshot_dao import SmartWalletSnapshotDAO
from datetime import date

def test_dao():
    print("=" * 70)
    print("🧪 测试数据库DAO")
    print("=" * 70)
    
    session = get_session()
    
    try:
        wallet_dao = SmartWalletDAO(session)
        snapshot_dao = SmartWalletSnapshotDAO(session)
        
        # 1. 测试统计
        print("\n📊 当前数据统计：")
        print("-" * 70)
        
        total = wallet_dao.count_total()
        smart_money = wallet_dao.count_smart_money()
        kol = wallet_dao.count_kol()
        
        print(f"总钱包数: {total}")
        print(f"聪明钱数: {smart_money}")
        print(f"KOL数量: {kol}")
        
        # 2. 测试查询TOP钱包
        if total > 0:
            print("\n🏆 TOP 5 钱包（7日盈利）：")
            print("-" * 70)
            
            top_wallets = wallet_dao.get_top_pnl_7d(limit=5)
            for idx, w in enumerate(top_wallets, 1):
                print(f"\n{idx}. {w.address}")
                print(f"   💰 7日盈利: ${float(w.pnl_7d):,.2f}")
                print(f"   📈 7日胜率: {float(w.win_rate_7d):.1f}%")
                print(f"   🏷️  聪明钱: {'是' if w.is_smart_money else '否'}")
                print(f"   📅 更新时间: {w.updated_at}")
        
        # 3. 测试快照表
        today = date.today()
        snapshot_count = snapshot_dao.count_by_date(today)
        print(f"\n📅 今日快照数量: {snapshot_count}")
        
        if snapshot_count > 0:
            date_range = snapshot_dao.get_date_range()
            print(f"📊 快照日期范围: {date_range[0]} ~ {date_range[1]}")
        
        # 4. 测试单个钱包查询
        if total > 0:
            first_wallet = wallet_dao.get_top_pnl_7d(limit=1)[0]
            address = first_wallet.address
            
            print(f"\n🔍 查询钱包: {address}")
            print("-" * 70)
            
            # 实时数据
            wallet = wallet_dao.get_by_address(address)
            if wallet:
                print(f"✅ 实时数据: PNL_7D=${float(wallet.pnl_7d):,.2f}")
            
            # 历史快照（最近7天）
            history = snapshot_dao.get_history_by_address(address, days=7)
            if history:
                print(f"📈 历史快照（最近{len(history)}天）:")
                for snap in history:
                    print(f"   {snap.snapshot_date}: ${float(snap.pnl_7d):,.2f}")
        
        print("\n" + "=" * 70)
        print("✅ 测试完成")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    test_dao()
