#!/usr/bin/env python3
"""
调试快照数据 - 检查数据质量
"""
from datetime import date, timedelta
from sqlalchemy import and_
from config.database import get_session
from models.smart_wallet_snapshot import SmartWalletSnapshot


def check_data_quality():
    """检查数据质量"""
    session = get_session()
    
    print("=" * 80)
    print("🔍 智能钱包快照数据质量检查")
    print("=" * 80)
    
    # 1. 检查数据总量
    total_count = session.query(SmartWalletSnapshot).count()
    print(f"\n📊 总快照记录数: {total_count}")
    
    if total_count == 0:
        print("\n❌ 数据库中没有快照数据！")
        print("   请先运行 gmgn_server.py 和 Chrome 扩展来采集数据")
        session.close()
        return
    
    # 2. 检查日期分布
    print("\n📅 日期分布:")
    from sqlalchemy import func
    date_stats = session.query(
        SmartWalletSnapshot.snapshot_date,
        func.count(SmartWalletSnapshot.id).label('count')
    ).group_by(SmartWalletSnapshot.snapshot_date).order_by(
        SmartWalletSnapshot.snapshot_date.desc()
    ).limit(10).all()
    
    for date_val, count in date_stats:
        print(f"   {date_val}: {count} 条记录")
    
    # 3. 获取最新数据样本
    latest_date = session.query(func.max(SmartWalletSnapshot.snapshot_date)).scalar()
    print(f"\n📌 最新数据日期: {latest_date}")
    
    # 获取最新日期的前5条数据
    latest_samples = session.query(SmartWalletSnapshot).filter(
        SmartWalletSnapshot.snapshot_date == latest_date
    ).limit(5).all()
    
    print(f"\n🔬 最新数据样本分析 ({latest_date}):")
    print("=" * 80)
    
    for i, snap in enumerate(latest_samples, 1):
        print(f"\n样本 {i}: {snap.address[:16]}...")
        print(f"  名称: {snap.name or 'N/A'}")
        print(f"  标签: 聪明钱={snap.is_smart_money}, KOL={snap.is_kol}, "
              f"热门追踪={snap.is_hot_followed}, 热门备注={snap.is_hot_remarked}")
        print(f"  工具: Trojan={snap.uses_trojan}, BullX={snap.uses_bullx}, "
              f"Photon={snap.uses_photon}, Axiom={snap.uses_axiom}")
        
        print(f"\n  7天数据:")
        print(f"    盈利: ${snap.pnl_7d or 0:,.2f}")
        print(f"    胜率: {snap.win_rate_7d or 0:.2f}%")
        print(f"    交易次数: {snap.tx_count_7d or 0}")
        print(f"    买入次数: {snap.buy_count_7d or 0}")
        print(f"    卖出次数: {snap.sell_count_7d or 0}")
        print(f"    持仓时长: {snap.avg_hold_time_7d or 0} 秒 ({(snap.avg_hold_time_7d or 0)/3600:.2f} 小时)")
    
    # 4. 统计数据完整性
    print("\n" + "=" * 80)
    print("📊 数据完整性统计 (最新日期):")
    print("=" * 80)
    
    latest_all = session.query(SmartWalletSnapshot).filter(
        SmartWalletSnapshot.snapshot_date == latest_date
    ).all()
    
    total = len(latest_all)
    
    # 统计各字段的非零数量
    stats = {
        'pnl_7d 非0': sum(1 for s in latest_all if s.pnl_7d != 0),
        'win_rate_7d 非0': sum(1 for s in latest_all if s.win_rate_7d != 0),
        'tx_count_7d 非0': sum(1 for s in latest_all if s.tx_count_7d != 0),
        'avg_hold_time_7d 非0': sum(1 for s in latest_all if s.avg_hold_time_7d != 0),
        '有名称': sum(1 for s in latest_all if s.name),
        '使用工具': sum(1 for s in latest_all if any([
            s.uses_trojan, s.uses_bullx, s.uses_photon, s.uses_axiom, s.uses_bot
        ])),
    }
    
    print(f"\n总记录数: {total}")
    for key, count in stats.items():
        percentage = (count / total * 100) if total > 0 else 0
        print(f"  {key}: {count} ({percentage:.1f}%)")
    
    # 5. 检查字段值范围
    print("\n" + "=" * 80)
    print("📈 字段值范围:")
    print("=" * 80)
    
    print(f"\n7D盈利:")
    print(f"  最小值: ${min(s.pnl_7d or 0 for s in latest_all):,.2f}")
    print(f"  最大值: ${max(s.pnl_7d or 0 for s in latest_all):,.2f}")
    print(f"  平均值: ${sum(s.pnl_7d or 0 for s in latest_all) / total:,.2f}")
    
    print(f"\n7D胜率:")
    print(f"  最小值: {min(s.win_rate_7d or 0 for s in latest_all):.2f}%")
    print(f"  最大值: {max(s.win_rate_7d or 0 for s in latest_all):.2f}%")
    print(f"  平均值: {sum(s.win_rate_7d or 0 for s in latest_all) / total:.2f}%")
    
    print(f"\n7D交易次数:")
    print(f"  最小值: {min(s.tx_count_7d or 0 for s in latest_all)}")
    print(f"  最大值: {max(s.tx_count_7d or 0 for s in latest_all)}")
    print(f"  平均值: {sum(s.tx_count_7d or 0 for s in latest_all) / total:.1f}")
    
    print(f"\n7D持仓时长:")
    hold_times = [s.avg_hold_time_7d or 0 for s in latest_all]
    print(f"  最小值: {min(hold_times)} 秒 ({min(hold_times)/3600:.2f} 小时)")
    print(f"  最大值: {max(hold_times)} 秒 ({max(hold_times)/3600:.2f} 小时)")
    print(f"  平均值: {sum(hold_times) / total:.1f} 秒 ({sum(hold_times) / total / 3600:.2f} 小时)")
    
    session.close()
    
    # 6. 诊断建议
    print("\n" + "=" * 80)
    print("💡 诊断建议:")
    print("=" * 80)
    
    if stats['win_rate_7d 非0'] == 0:
        print("\n⚠️  所有钱包的7D胜率都是0！")
        print("   可能原因:")
        print("   1. GMGN API 返回的 win_rate_7d 字段就是0")
        print("   2. 数据映射有误，字段名不匹配")
        print("   3. 需要检查 gmgn_server.py 中的字段映射")
    
    if stats['avg_hold_time_7d 非0'] == 0:
        print("\n⚠️  所有钱包的7D持仓时长都是0！")
        print("   可能原因:")
        print("   1. GMGN API 返回的 avg_hold_time_7d 字段就是0")
        print("   2. 字段映射有误")
        print("   3. 需要检查源数据")
    
    if stats['使用工具'] == 0:
        print("\n⚠️  没有钱包使用工具标签！")
        print("   可能原因:")
        print("   1. GMGN API 的 tags 字段中没有工具相关标签")
        print("   2. 标签名称映射不正确")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    check_data_quality()
