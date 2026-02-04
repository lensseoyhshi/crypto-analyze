#!/usr/bin/env python3
"""
智能钱包快照数据分析脚本
分析 smart_wallets_snapshot 表的数据
"""
import pandas as pd
from datetime import datetime, timedelta, date
from sqlalchemy import func, and_
from config.database import get_session
from models.smart_wallet_snapshot import SmartWalletSnapshot
import numpy as np
import os


def get_recent_snapshots(days=3, start_date_str=None):
    """获取最近N天的快照数据，或指定起始日期到今日的数据
    
    Args:
        days: 最近N天的数据（如果不指定start_date_str）
        start_date_str: 起始日期字符串，格式'YYYY-MM-DD'（如果指定则忽略days参数）
    """
    session = get_session()
    
    # 计算日期范围
    end_date = date.today()
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    else:
        start_date = end_date - timedelta(days=days-1)
    
    print(f"📅 查询日期范围: {start_date} 到 {end_date}")
    
    # 查询数据
    snapshots = session.query(SmartWalletSnapshot).filter(
        and_(
            SmartWalletSnapshot.snapshot_date >= start_date,
            SmartWalletSnapshot.snapshot_date <= end_date
        )
    ).all()
    
    session.close()
    
    print(f"✅ 查询到 {len(snapshots)} 条记录")
    
    # 转换为DataFrame
    data = []
    for snap in snapshots:
        data.append({
            'address': snap.address,
            'snapshot_date': snap.snapshot_date,
            'name': snap.name,
            
            # 标签
            'is_smart_money': snap.is_smart_money,
            'is_kol': snap.is_kol,
            'is_whale': snap.is_whale,
            'is_sniper': snap.is_sniper,
            'is_hot_followed': snap.is_hot_followed,
            'is_hot_remarked': snap.is_hot_remarked,
            
            # 工具
            'uses_trojan': snap.uses_trojan,
            'uses_bullx': snap.uses_bullx,
            'uses_photon': snap.uses_photon,
            'uses_axiom': snap.uses_axiom,
            'uses_bot': snap.uses_bot,
            
            # 1天数据
            'pnl_1d': float(snap.pnl_1d or 0),
            'win_rate_1d': float(snap.win_rate_1d or 0),
            'tx_count_1d': snap.tx_count_1d or 0,
            'buy_count_1d': snap.buy_count_1d or 0,
            'sell_count_1d': snap.sell_count_1d or 0,
            'avg_hold_time_1d': snap.avg_hold_time_1d or 0,
            
            # 7天数据
            'pnl_7d': float(snap.pnl_7d or 0),
            'win_rate_7d': float(snap.win_rate_7d or 0),
            'tx_count_7d': snap.tx_count_7d or 0,
            'buy_count_7d': snap.buy_count_7d or 0,
            'sell_count_7d': snap.sell_count_7d or 0,
            'avg_hold_time_7d': snap.avg_hold_time_7d or 0,
            
            # 30天数据
            'pnl_30d': float(snap.pnl_30d or 0),
            'win_rate_30d': float(snap.win_rate_30d or 0),
            'tx_count_30d': snap.tx_count_30d or 0,
            'buy_count_30d': snap.buy_count_30d or 0,
            'sell_count_30d': snap.sell_count_30d or 0,
            'avg_hold_time_30d': snap.avg_hold_time_30d or 0,
            
            # 盈亏分布
            'pnl_lt_minus_dot5_num_7d': snap.pnl_lt_minus_dot5_num_7d or 0,
            'pnl_minus_dot5_0x_num_7d': snap.pnl_minus_dot5_0x_num_7d or 0,
            'pnl_lt_2x_num_7d': snap.pnl_lt_2x_num_7d or 0,
            'pnl_2x_5x_num_7d': snap.pnl_2x_5x_num_7d or 0,
            'pnl_gt_5x_num_7d': snap.pnl_gt_5x_num_7d or 0,
        })
    
    df = pd.DataFrame(data)
    return df


def analyze_daily_changes(df):
    """分析每日变化"""
    print("\n" + "=" * 80)
    print("📊 1. 近期钱包指标变动性分析")
    print("=" * 80)
    
    if df.empty:
        print("❌ 没有数据可分析")
        return {}
    
    # 按日期分组统计
    dates = sorted(df['snapshot_date'].unique())
    
    print(f"\n📅 数据日期: {', '.join([str(d) for d in dates])}\n")
    
    # 1D/7D/30D维度的变化
    dimensions = [
        ('1D', 'pnl_1d', 'win_rate_1d', 'tx_count_1d', 'avg_hold_time_1d'),
        ('7D', 'pnl_7d', 'win_rate_7d', 'tx_count_7d', 'avg_hold_time_7d'),
        ('30D', 'pnl_30d', 'win_rate_30d', 'tx_count_30d', 'avg_hold_time_30d'),
    ]
    
    result_dfs = {}
    
    for dim_name, pnl_col, wr_col, tx_col, hold_col in dimensions:
        print(f"\n{'─' * 80}")
        print(f"📈 {dim_name} 维度分析")
        print(f"{'─' * 80}")
        
        daily_stats = []
        for snapshot_date in dates:
            day_data = df[df['snapshot_date'] == snapshot_date]
            
            stats = {
                '日期': snapshot_date,
                '钱包数': len(day_data),
                '平均盈利': day_data[pnl_col].mean(),
                '中位盈利': day_data[pnl_col].median(),
                '平均胜率': day_data[wr_col].mean(),
                '平均交易次数': day_data[tx_col].mean(),
                '平均持仓时长(小时)': day_data[hold_col].mean() / 3600,
                '盈利钱包数': len(day_data[day_data[pnl_col] > 0]),
                '亏损钱包数': len(day_data[day_data[pnl_col] < 0]),
            }
            daily_stats.append(stats)
        
        stats_df = pd.DataFrame(daily_stats)
        result_dfs[f'每日变化_{dim_name}'] = stats_df
        print(stats_df.to_string(index=False))
        
        # 计算变化率
        if len(dates) >= 2:
            print(f"\n📊 变化趋势（相比前一天）:")
            for i in range(1, len(daily_stats)):
                prev = daily_stats[i-1]
                curr = daily_stats[i]
                
                pnl_change = ((curr['平均盈利'] - prev['平均盈利']) / abs(prev['平均盈利']) * 100) if prev['平均盈利'] != 0 else 0
                wr_change = curr['平均胜率'] - prev['平均胜率']
                wallet_change = curr['钱包数'] - prev['钱包数']
                
                print(f"  {curr['日期']}: ", end="")
                print(f"钱包数 {wallet_change:+d} | ", end="")
                print(f"平均盈利 {pnl_change:+.1f}% | ", end="")
                print(f"平均胜率 {wr_change:+.1f}%")
    
    return result_dfs


def analyze_by_tags(df):
    """按标签分析"""
    print("\n" + "=" * 80)
    print("🏷️  2. 不同标签钱包的表现分析")
    print("=" * 80)
    
    if df.empty:
        print("❌ 没有数据可分析")
        return None
    
    # 定义标签
    tags = {
        '聪明钱': 'is_smart_money',
        'KOL': 'is_kol',
        '巨鲸': 'is_whale',
        '狙击手': 'is_sniper',
        '热门追踪': 'is_hot_followed',
        '热门备注': 'is_hot_remarked',
    }
    
    tag_stats = []
    
    for tag_name, tag_col in tags.items():
        tag_data = df[df[tag_col] == 1]
        
        if len(tag_data) == 0:
            continue
        
        stats = {
            '标签': tag_name,
            '钱包数': len(tag_data['address'].unique()),
            '快照记录数': len(tag_data),
            
            # 7天维度（主要）
            '平均7D盈利': tag_data['pnl_7d'].mean(),
            '中位7D盈利': tag_data['pnl_7d'].median(),
            '7D胜率': tag_data['win_rate_7d'].mean(),
            '7D平均交易次数': tag_data['tx_count_7d'].mean(),
            '7D平均持仓时长(小时)': tag_data['avg_hold_time_7d'].mean() / 3600,
            
            # 盈利分布
            '盈利钱包占比': len(tag_data[tag_data['pnl_7d'] > 0]) / len(tag_data) * 100,
            '大亏(>50%)占比': len(tag_data[tag_data['pnl_7d'] < -5000]) / len(tag_data) * 100,
            '大赚(>10000)占比': len(tag_data[tag_data['pnl_7d'] > 10000]) / len(tag_data) * 100,
        }
        tag_stats.append(stats)
    
    if tag_stats:
        stats_df = pd.DataFrame(tag_stats)
        print("\n" + stats_df.to_string(index=False))
        return stats_df
    else:
        print("\n❌ 没有标签数据")
        return None


def analyze_by_tools(df):
    """按交易工具/平台分析"""
    print("\n" + "=" * 80)
    print("🛠️  3. 不同交易工具/平台的表现分析")
    print("=" * 80)
    
    if df.empty:
        print("❌ 没有数据可分析")
        return None
    
    # 定义工具
    tools = {
        'Trojan': 'uses_trojan',
        'BullX': 'uses_bullx',
        'Photon': 'uses_photon',
        'Axiom': 'uses_axiom',
        'Bot': 'uses_bot',
    }
    
    tool_stats = []
    
    for tool_name, tool_col in tools.items():
        tool_data = df[df[tool_col] == 1]
        
        if len(tool_data) == 0:
            continue
        
        # 数据验证和调试信息
        print(f"\n🔍 [{tool_name}] 数据样本检查:")
        print(f"   钱包数: {len(tool_data['address'].unique())}")
        print(f"   win_rate_7d 样本: {tool_data['win_rate_7d'].head(3).tolist()}")
        print(f"   avg_hold_time_7d 样本: {tool_data['avg_hold_time_7d'].head(3).tolist()}")
        
        stats = {
            '工具': tool_name,
            '钱包数': len(tool_data['address'].unique()),
            '快照记录数': len(tool_data),
            
            # 7天维度 - 保存数值类型用于Excel
            '平均7D盈利': tool_data['pnl_7d'].mean(),
            '中位7D盈利': tool_data['pnl_7d'].median(),
            '7D胜率': tool_data['win_rate_7d'].mean(),
            '7D平均交易次数': tool_data['tx_count_7d'].mean(),
            '7D买入次数': tool_data['buy_count_7d'].mean(),
            '7D卖出次数': tool_data['sell_count_7d'].mean(),
            '7D平均持仓时长(小时)': tool_data['avg_hold_time_7d'].mean() / 3600,
            
            '盈利钱包占比': len(tool_data[tool_data['pnl_7d'] > 0]) / len(tool_data) * 100,
        }
        tool_stats.append(stats)
    
    if tool_stats:
        stats_df = pd.DataFrame(tool_stats)
        print("\n" + "=" * 80)
        print("📊 工具表现汇总:")
        print("=" * 80)
        # 格式化打印
        print_df = stats_df.copy()
        print_df['平均7D盈利'] = print_df['平均7D盈利'].apply(lambda x: f"${x:,.2f}")
        print_df['中位7D盈利'] = print_df['中位7D盈利'].apply(lambda x: f"${x:,.2f}")
        print_df['7D胜率'] = print_df['7D胜率'].apply(lambda x: f"{x:.2f}%")
        print_df['7D平均交易次数'] = print_df['7D平均交易次数'].apply(lambda x: f"{x:.1f}")
        print_df['7D买入次数'] = print_df['7D买入次数'].apply(lambda x: f"{x:.1f}")
        print_df['7D卖出次数'] = print_df['7D卖出次数'].apply(lambda x: f"{x:.1f}")
        print_df['7D平均持仓时长(小时)'] = print_df['7D平均持仓时长(小时)'].apply(lambda x: f"{x:.1f}")
        print_df['盈利钱包占比'] = print_df['盈利钱包占比'].apply(lambda x: f"{x:.1f}%")
        print(print_df.to_string(index=False))
        return stats_df
    else:
        print("\n❌ 没有工具数据")
        return None


def analyze_pnl_distribution(df):
    """分析盈亏分布"""
    print("\n" + "=" * 80)
    print("📊 4. 7日盈亏分布分析")
    print("=" * 80)
    
    if df.empty:
        print("❌ 没有数据可分析")
        return None
    
    # 获取最新日期的数据
    latest_date = df['snapshot_date'].max()
    latest_data = df[df['snapshot_date'] == latest_date]
    
    print(f"\n📅 分析日期: {latest_date}")
    print(f"📊 总钱包数: {len(latest_data)}\n")
    
    # 统计盈亏分布
    distribution = {
        '亏损>50%': latest_data['pnl_lt_minus_dot5_num_7d'].sum(),
        '亏损0~50%': latest_data['pnl_minus_dot5_0x_num_7d'].sum(),
        '盈利0~100%': latest_data['pnl_lt_2x_num_7d'].sum(),
        '盈利2~5倍': latest_data['pnl_2x_5x_num_7d'].sum(),
        '盈利>5倍': latest_data['pnl_gt_5x_num_7d'].sum(),
    }
    
    total_trades = sum(distribution.values())
    
    print("交易盈亏分布:")
    print("-" * 60)
    dist_data = []
    for category, count in distribution.items():
        percentage = (count / total_trades * 100) if total_trades > 0 else 0
        bar = '█' * int(percentage / 2)
        print(f"{category:15s} | {count:6.0f} 次 ({percentage:5.1f}%) {bar}")
        dist_data.append({
            '分类': category,
            '交易次数': count,
            '占比(%)': percentage
        })
    
    print("-" * 60)
    print(f"{'总交易次数':15s} | {total_trades:6.0f} 次")
    
    # 计算盈亏比
    profit_trades = distribution['盈利0~100%'] + distribution['盈利2~5倍'] + distribution['盈利>5倍']
    loss_trades = distribution['亏损>50%'] + distribution['亏损0~50%']
    
    if loss_trades > 0:
        profit_loss_ratio = profit_trades / loss_trades
        print(f"\n盈亏笔数比: {profit_loss_ratio:.2f} (盈利 {profit_trades:.0f} 笔 / 亏损 {loss_trades:.0f} 笔)")
        dist_data.append({
            '分类': '总计',
            '交易次数': total_trades,
            '占比(%)': 100.0
        })
        dist_data.append({
            '分类': '盈亏笔数比',
            '交易次数': profit_loss_ratio,
            '占比(%)': ''
        })
    
    return pd.DataFrame(dist_data)


def analyze_top_performers(df):
    """分析TOP表现者"""
    print("\n" + "=" * 80)
    print("🏆 5. TOP表现钱包分析")
    print("=" * 80)
    
    if df.empty:
        print("❌ 没有数据可分析")
        return {}
    
    # 获取最新日期的数据
    latest_date = df['snapshot_date'].max()
    latest_data = df[df['snapshot_date'] == latest_date].copy()
    
    print(f"\n📅 分析日期: {latest_date}\n")
    
    result_dfs = {}
    
    # TOP 10 盈利钱包
    print("🥇 TOP 10 盈利钱包 (7D):")
    print("-" * 80)
    top_profit = latest_data.nlargest(10, 'pnl_7d')[
        ['address', 'name', 'pnl_7d', 'win_rate_7d', 'tx_count_7d', 'avg_hold_time_7d']
    ].copy()
    top_profit['avg_hold_time_7d_hours'] = top_profit['avg_hold_time_7d'] / 3600  # 转换为小时
    top_profit = top_profit.drop('avg_hold_time_7d', axis=1)
    top_profit.rename(columns={'avg_hold_time_7d_hours': '持仓时长(小时)'}, inplace=True)
    print(top_profit.to_string(index=False))
    result_dfs['TOP10盈利钱包'] = top_profit
    
    # TOP 10 胜率钱包（交易次数>5）
    print("\n\n🎯 TOP 10 胜率钱包 (7D交易>5次):")
    print("-" * 80)
    active_wallets = latest_data[latest_data['tx_count_7d'] > 5]
    if len(active_wallets) > 0:
        top_winrate = active_wallets.nlargest(10, 'win_rate_7d')[
            ['address', 'name', 'win_rate_7d', 'pnl_7d', 'tx_count_7d']
        ].copy()
        print(top_winrate.to_string(index=False))
        result_dfs['TOP10胜率钱包'] = top_winrate
    else:
        print("❌ 没有交易次数>5的钱包")
    
    return result_dfs


def generate_summary_report(df):
    """生成总结报告"""
    print("\n" + "=" * 80)
    print("📋 6. 数据总结报告")
    print("=" * 80)
    
    if df.empty:
        print("❌ 没有数据可分析")
        return None
    
    # 总体统计
    total_wallets = len(df['address'].unique())
    total_snapshots = len(df)
    date_range = f"{df['snapshot_date'].min()} 至 {df['snapshot_date'].max()}"
    
    print(f"\n📊 数据概览:")
    print(f"  • 日期范围: {date_range}")
    print(f"  • 唯一钱包数: {total_wallets}")
    print(f"  • 快照记录数: {total_snapshots}")
    
    # 标签分布
    tag_dist = []
    print(f"\n🏷️  标签分布:")
    smart_money = len(df[df['is_smart_money'] == 1]['address'].unique())
    kol = len(df[df['is_kol'] == 1]['address'].unique())
    hot_followed = len(df[df['is_hot_followed'] == 1]['address'].unique())
    hot_remarked = len(df[df['is_hot_remarked'] == 1]['address'].unique())
    print(f"  • 聪明钱: {smart_money} 个")
    print(f"  • KOL: {kol} 个")
    print(f"  • 热门追踪: {hot_followed} 个")
    print(f"  • 热门备注: {hot_remarked} 个")
    
    # 工具使用
    print(f"\n🛠️  工具使用:")
    trojan = len(df[df['uses_trojan'] == 1]['address'].unique())
    bullx = len(df[df['uses_bullx'] == 1]['address'].unique())
    photon = len(df[df['uses_photon'] == 1]['address'].unique())
    print(f"  • Trojan: {trojan} 个")
    print(f"  • BullX: {bullx} 个")
    print(f"  • Photon: {photon} 个")
    
    # 整体表现
    latest = df[df['snapshot_date'] == df['snapshot_date'].max()]
    print(f"\n📈 整体表现 (最新数据):")
    avg_pnl = latest['pnl_7d'].mean()
    median_pnl = latest['pnl_7d'].median()
    avg_winrate = latest['win_rate_7d'].mean()
    avg_tx = latest['tx_count_7d'].mean()
    profit_ratio = len(latest[latest['pnl_7d'] > 0]) / len(latest) * 100
    print(f"  • 平均7D盈利: ${avg_pnl:,.2f}")
    print(f"  • 中位7D盈利: ${median_pnl:,.2f}")
    print(f"  • 平均7D胜率: {avg_winrate:.1f}%")
    print(f"  • 平均7D交易次数: {avg_tx:.1f} 次")
    print(f"  • 盈利钱包占比: {profit_ratio:.1f}%")
    
    # 创建总结DataFrame
    summary_data = [
        {'指标': '日期范围', '数值': date_range},
        {'指标': '唯一钱包数', '数值': total_wallets},
        {'指标': '快照记录数', '数值': total_snapshots},
        {'指标': '聪明钱钱包数', '数值': smart_money},
        {'指标': 'KOL钱包数', '数值': kol},
        {'指标': '热门追踪钱包数', '数值': hot_followed},
        {'指标': '热门备注钱包数', '数值': hot_remarked},
        {'指标': 'Trojan用户数', '数值': trojan},
        {'指标': 'BullX用户数', '数值': bullx},
        {'指标': 'Photon用户数', '数值': photon},
        {'指标': '平均7D盈利($)', '数值': avg_pnl},
        {'指标': '中位7D盈利($)', '数值': median_pnl},
        {'指标': '平均7D胜率(%)', '数值': avg_winrate},
        {'指标': '平均7D交易次数', '数值': avg_tx},
        {'指标': '盈利钱包占比(%)', '数值': profit_ratio},
    ]
    
    return pd.DataFrame(summary_data)


def save_to_excel(all_results, filename=None):
    """将所有分析结果保存到Excel文件"""
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'wallet_analysis_{timestamp}.xlsx'
    
    print("\n" + "=" * 80)
    print(f"💾 正在保存分析结果到 Excel: {filename}")
    print("=" * 80)
    
    # 创建Excel写入器
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        sheet_num = 1
        
        # 1. 保存每日变化数据（多个维度）
        if 'daily_changes' in all_results and all_results['daily_changes']:
            for sheet_name, df in all_results['daily_changes'].items():
                if df is not None and not df.empty:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    print(f"  ✅ 工作表 '{sheet_name}' 已保存 ({len(df)} 行)")
                    sheet_num += 1
        
        # 2. 保存标签分析
        if 'tags' in all_results and all_results['tags'] is not None:
            all_results['tags'].to_excel(writer, sheet_name='标签分析', index=False)
            print(f"  ✅ 工作表 '标签分析' 已保存 ({len(all_results['tags'])} 行)")
            sheet_num += 1
        
        # 3. 保存工具分析
        if 'tools' in all_results and all_results['tools'] is not None:
            all_results['tools'].to_excel(writer, sheet_name='工具分析', index=False)
            print(f"  ✅ 工作表 '工具分析' 已保存 ({len(all_results['tools'])} 行)")
            sheet_num += 1
        
        # 4. 保存盈亏分布
        if 'pnl_dist' in all_results and all_results['pnl_dist'] is not None:
            all_results['pnl_dist'].to_excel(writer, sheet_name='盈亏分布', index=False)
            print(f"  ✅ 工作表 '盈亏分布' 已保存 ({len(all_results['pnl_dist'])} 行)")
            sheet_num += 1
        
        # 5. 保存TOP表现者（多个表）
        if 'top_performers' in all_results and all_results['top_performers']:
            for sheet_name, df in all_results['top_performers'].items():
                if df is not None and not df.empty:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    print(f"  ✅ 工作表 '{sheet_name}' 已保存 ({len(df)} 行)")
                    sheet_num += 1
        
        # 6. 保存总结报告
        if 'summary' in all_results and all_results['summary'] is not None:
            all_results['summary'].to_excel(writer, sheet_name='总结报告', index=False)
            print(f"  ✅ 工作表 '总结报告' 已保存 ({len(all_results['summary'])} 行)")
            sheet_num += 1
    
    print("=" * 80)
    print(f"✅ Excel 文件已保存: {os.path.abspath(filename)}")
    print(f"📊 共 {sheet_num - 1} 个工作表")
    print("=" * 80)
    
    return filename


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("🚀 智能钱包快照数据分析系统")
    print("=" * 80)
    
    # 获取数据 - 从2026-02-03到今日
    df = get_recent_snapshots(start_date_str='2026-02-03')
    
    if df.empty:
        print("\n❌ 没有数据，请先运行数据采集系统")
        return
    
    # 执行分析并收集结果
    all_results = {}
    
    all_results['daily_changes'] = analyze_daily_changes(df)
    all_results['tags'] = analyze_by_tags(df)
    all_results['tools'] = analyze_by_tools(df)
    all_results['pnl_dist'] = analyze_pnl_distribution(df)
    all_results['top_performers'] = analyze_top_performers(df)
    all_results['summary'] = generate_summary_report(df)
    
    print("\n" + "=" * 80)
    print("✅ 分析完成！")
    print("=" * 80 + "\n")
    
    # 保存到Excel
    save_to_excel(all_results)


if __name__ == '__main__':
    main()
