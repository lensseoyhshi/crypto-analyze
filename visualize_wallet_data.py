#!/usr/bin/env python3
"""
智能钱包数据可视化分析（带图表）
需要安装: pip install matplotlib seaborn
"""
import pandas as pd
from datetime import datetime, timedelta, date
from config.database import get_session
from models.smart_wallet_snapshot import SmartWalletSnapshot
from sqlalchemy import and_

try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # 使用非交互式后端
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    HAS_PLOT = True
except ImportError:
    HAS_PLOT = False
    print("⚠️  matplotlib 未安装，将跳过图表生成")
    print("   安装命令: pip install matplotlib seaborn")


def get_snapshot_data(days=7):
    """获取快照数据"""
    session = get_session()
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days-1)
    
    print(f"📅 查询日期范围: {start_date} 到 {end_date}")
    
    snapshots = session.query(SmartWalletSnapshot).filter(
        and_(
            SmartWalletSnapshot.snapshot_date >= start_date,
            SmartWalletSnapshot.snapshot_date <= end_date
        )
    ).all()
    
    session.close()
    
    if not snapshots:
        return pd.DataFrame()
    
    # 转换为DataFrame
    data = []
    for snap in snapshots:
        # 确定主要标签
        main_tag = '其他'
        if snap.is_smart_money:
            main_tag = '聪明钱'
        elif snap.is_kol:
            main_tag = 'KOL'
        elif snap.is_hot_followed:
            main_tag = '热门追踪'
        elif snap.is_hot_remarked:
            main_tag = '热门备注'
        
        # 确定使用的工具
        tool = '无'
        if snap.uses_trojan:
            tool = 'Trojan'
        elif snap.uses_bullx:
            tool = 'BullX'
        elif snap.uses_photon:
            tool = 'Photon'
        elif snap.uses_axiom:
            tool = 'Axiom'
        elif snap.uses_bot:
            tool = 'Bot'
        
        data.append({
            'address': snap.address,
            'date': snap.snapshot_date,
            'tag': main_tag,
            'tool': tool,
            'pnl_1d': float(snap.pnl_1d or 0),
            'pnl_7d': float(snap.pnl_7d or 0),
            'pnl_30d': float(snap.pnl_30d or 0),
            'win_rate_7d': float(snap.win_rate_7d or 0),
            'tx_count_7d': snap.tx_count_7d or 0,
            'avg_hold_time_7d': (snap.avg_hold_time_7d or 0) / 3600,  # 转换为小时
        })
    
    df = pd.DataFrame(data)
    print(f"✅ 获取 {len(df)} 条记录，{len(df['address'].unique())} 个钱包")
    return df


def plot_daily_trend(df, output_file='analysis_daily_trend.png'):
    """绘制每日趋势图"""
    if not HAS_PLOT or df.empty:
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Daily Wallet Metrics Trend', fontsize=16, fontweight='bold')
    
    # 按日期分组
    daily_stats = df.groupby('date').agg({
        'address': 'count',
        'pnl_7d': ['mean', 'median'],
        'win_rate_7d': 'mean',
        'tx_count_7d': 'mean'
    }).reset_index()
    
    daily_stats.columns = ['date', 'wallet_count', 'avg_pnl', 'median_pnl', 'avg_winrate', 'avg_tx']
    
    # 1. 钱包数量趋势
    axes[0, 0].plot(daily_stats['date'], daily_stats['wallet_count'], marker='o', linewidth=2, color='#2E86AB')
    axes[0, 0].set_title('Wallet Count', fontsize=12, fontweight='bold')
    axes[0, 0].set_ylabel('Count')
    axes[0, 0].grid(True, alpha=0.3)
    
    # 2. 平均7D盈利
    axes[0, 1].plot(daily_stats['date'], daily_stats['avg_pnl'], marker='o', linewidth=2, color='#06A77D', label='Average')
    axes[0, 1].plot(daily_stats['date'], daily_stats['median_pnl'], marker='s', linewidth=2, color='#F77F00', label='Median')
    axes[0, 1].set_title('7D PNL Trend', fontsize=12, fontweight='bold')
    axes[0, 1].set_ylabel('PNL (USD)')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].axhline(y=0, color='red', linestyle='--', alpha=0.5)
    
    # 3. 平均胜率
    axes[1, 0].plot(daily_stats['date'], daily_stats['avg_winrate'], marker='o', linewidth=2, color='#D62828')
    axes[1, 0].set_title('Average Win Rate', fontsize=12, fontweight='bold')
    axes[1, 0].set_ylabel('Win Rate (%)')
    axes[1, 0].grid(True, alpha=0.3)
    
    # 4. 平均交易次数
    axes[1, 1].bar(daily_stats['date'].astype(str), daily_stats['avg_tx'], color='#8338EC', alpha=0.7)
    axes[1, 1].set_title('Average Transaction Count', fontsize=12, fontweight='bold')
    axes[1, 1].set_ylabel('Count')
    axes[1, 1].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ 图表已保存: {output_file}")


def plot_tag_comparison(df, output_file='analysis_tag_comparison.png'):
    """绘制标签对比图"""
    if not HAS_PLOT or df.empty:
        return
    
    # 使用最新日期的数据
    latest_date = df['date'].max()
    latest_df = df[df['date'] == latest_date]
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle(f'Tag Performance Comparison ({latest_date})', fontsize=16, fontweight='bold')
    
    # 按标签分组统计
    tag_stats = latest_df.groupby('tag').agg({
        'address': 'count',
        'pnl_7d': 'mean',
        'win_rate_7d': 'mean',
        'tx_count_7d': 'mean',
        'avg_hold_time_7d': 'mean'
    }).reset_index()
    
    tag_stats.columns = ['tag', 'count', 'avg_pnl', 'avg_winrate', 'avg_tx', 'avg_hold_time']
    tag_stats = tag_stats.sort_values('avg_pnl', ascending=False)
    
    colors = ['#2E86AB', '#06A77D', '#F77F00', '#D62828', '#8338EC']
    
    # 1. 钱包数量
    axes[0, 0].bar(tag_stats['tag'], tag_stats['count'], color=colors[:len(tag_stats)], alpha=0.7)
    axes[0, 0].set_title('Wallet Count by Tag', fontsize=12, fontweight='bold')
    axes[0, 0].set_ylabel('Count')
    axes[0, 0].tick_params(axis='x', rotation=45)
    axes[0, 0].grid(True, alpha=0.3, axis='y')
    
    # 2. 平均7D盈利
    axes[0, 1].barh(tag_stats['tag'], tag_stats['avg_pnl'], color=colors[:len(tag_stats)], alpha=0.7)
    axes[0, 1].set_title('Average 7D PNL by Tag', fontsize=12, fontweight='bold')
    axes[0, 1].set_xlabel('PNL (USD)')
    axes[0, 1].axvline(x=0, color='red', linestyle='--', alpha=0.5)
    axes[0, 1].grid(True, alpha=0.3, axis='x')
    
    # 3. 平均胜率
    axes[1, 0].barh(tag_stats['tag'], tag_stats['avg_winrate'], color=colors[:len(tag_stats)], alpha=0.7)
    axes[1, 0].set_title('Average Win Rate by Tag', fontsize=12, fontweight='bold')
    axes[1, 0].set_xlabel('Win Rate (%)')
    axes[1, 0].grid(True, alpha=0.3, axis='x')
    
    # 4. 平均持仓时长
    axes[1, 1].barh(tag_stats['tag'], tag_stats['avg_hold_time'], color=colors[:len(tag_stats)], alpha=0.7)
    axes[1, 1].set_title('Average Hold Time by Tag', fontsize=12, fontweight='bold')
    axes[1, 1].set_xlabel('Hours')
    axes[1, 1].grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ 图表已保存: {output_file}")


def plot_tool_comparison(df, output_file='analysis_tool_comparison.png'):
    """绘制工具对比图"""
    if not HAS_PLOT or df.empty:
        return
    
    latest_date = df['date'].max()
    latest_df = df[df['date'] == latest_date]
    
    # 过滤掉"无"工具的数据
    tool_df = latest_df[latest_df['tool'] != '无']
    
    if tool_df.empty:
        print("⚠️  没有工具数据，跳过工具对比图")
        return
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle(f'Tool Performance Comparison ({latest_date})', fontsize=16, fontweight='bold')
    
    # 按工具分组
    tool_stats = tool_df.groupby('tool').agg({
        'address': 'count',
        'pnl_7d': ['mean', 'median'],
        'win_rate_7d': 'mean',
        'tx_count_7d': 'mean'
    }).reset_index()
    
    tool_stats.columns = ['tool', 'count', 'avg_pnl', 'median_pnl', 'avg_winrate', 'avg_tx']
    tool_stats = tool_stats.sort_values('avg_pnl', ascending=False)
    
    colors = ['#2E86AB', '#06A77D', '#F77F00', '#D62828', '#8338EC']
    
    # 1. 钱包数量
    axes[0, 0].bar(tool_stats['tool'], tool_stats['count'], color=colors[:len(tool_stats)], alpha=0.7)
    axes[0, 0].set_title('Wallet Count by Tool', fontsize=12, fontweight='bold')
    axes[0, 0].set_ylabel('Count')
    axes[0, 0].tick_params(axis='x', rotation=45)
    
    # 2. 平均vs中位盈利
    x = range(len(tool_stats))
    width = 0.35
    axes[0, 1].bar([i - width/2 for i in x], tool_stats['avg_pnl'], width, label='Average', alpha=0.7, color='#06A77D')
    axes[0, 1].bar([i + width/2 for i in x], tool_stats['median_pnl'], width, label='Median', alpha=0.7, color='#F77F00')
    axes[0, 1].set_xticks(x)
    axes[0, 1].set_xticklabels(tool_stats['tool'], rotation=45)
    axes[0, 1].set_title('7D PNL by Tool', fontsize=12, fontweight='bold')
    axes[0, 1].set_ylabel('PNL (USD)')
    axes[0, 1].legend()
    axes[0, 1].axhline(y=0, color='red', linestyle='--', alpha=0.5)
    
    # 3. 胜率
    axes[1, 0].bar(tool_stats['tool'], tool_stats['avg_winrate'], color=colors[:len(tool_stats)], alpha=0.7)
    axes[1, 0].set_title('Win Rate by Tool', fontsize=12, fontweight='bold')
    axes[1, 0].set_ylabel('Win Rate (%)')
    axes[1, 0].tick_params(axis='x', rotation=45)
    
    # 4. 交易频次
    axes[1, 1].bar(tool_stats['tool'], tool_stats['avg_tx'], color=colors[:len(tool_stats)], alpha=0.7)
    axes[1, 1].set_title('Transaction Count by Tool', fontsize=12, fontweight='bold')
    axes[1, 1].set_ylabel('Count')
    axes[1, 1].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ 图表已保存: {output_file}")


def plot_pnl_distribution(df, output_file='analysis_pnl_distribution.png'):
    """绘制盈亏分布图"""
    if not HAS_PLOT or df.empty:
        return
    
    latest_date = df['date'].max()
    latest_df = df[df['date'] == latest_date]
    
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    fig.suptitle(f'PNL Distribution ({latest_date})', fontsize=16, fontweight='bold')
    
    # 1. 7D盈利分布（直方图）
    axes[0].hist(latest_df['pnl_7d'], bins=50, alpha=0.7, color='#2E86AB', edgecolor='black')
    axes[0].axvline(x=0, color='red', linestyle='--', linewidth=2, label='Break Even')
    axes[0].axvline(x=latest_df['pnl_7d'].mean(), color='green', linestyle='--', linewidth=2, label='Mean')
    axes[0].axvline(x=latest_df['pnl_7d'].median(), color='orange', linestyle='--', linewidth=2, label='Median')
    axes[0].set_title('7D PNL Distribution', fontsize=12, fontweight='bold')
    axes[0].set_xlabel('PNL (USD)')
    axes[0].set_ylabel('Frequency')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # 2. 盈利vs亏损占比（饼图）
    profit_count = len(latest_df[latest_df['pnl_7d'] > 0])
    loss_count = len(latest_df[latest_df['pnl_7d'] < 0])
    break_even = len(latest_df[latest_df['pnl_7d'] == 0])
    
    sizes = [profit_count, loss_count, break_even]
    labels = [f'Profit ({profit_count})', f'Loss ({loss_count})', f'Break Even ({break_even})']
    colors_pie = ['#06A77D', '#D62828', '#8B8B8B']
    explode = (0.1, 0.1, 0)
    
    axes[1].pie(sizes, explode=explode, labels=labels, colors=colors_pie, autopct='%1.1f%%',
                shadow=True, startangle=90)
    axes[1].set_title('Profit/Loss Ratio', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ 图表已保存: {output_file}")


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("📊 智能钱包数据可视化分析")
    print("=" * 80 + "\n")
    
    # 获取数据
    df = get_snapshot_data(days=7)
    
    if df.empty:
        print("❌ 没有数据，请先运行数据采集")
        return
    
    print(f"\n📈 开始生成图表...\n")
    
    # 生成图表
    if HAS_PLOT:
        plot_daily_trend(df)
        plot_tag_comparison(df)
        plot_tool_comparison(df)
        plot_pnl_distribution(df)
        
        print("\n" + "=" * 80)
        print("✅ 所有图表生成完成！")
        print("=" * 80)
        print("\n生成的文件:")
        print("  1. analysis_daily_trend.png - 每日趋势图")
        print("  2. analysis_tag_comparison.png - 标签对比图")
        print("  3. analysis_tool_comparison.png - 工具对比图")
        print("  4. analysis_pnl_distribution.png - 盈亏分布图")
        print()
    else:
        print("\n⚠️  matplotlib 未安装，无法生成图表")
        print("   安装命令: pip install matplotlib")


if __name__ == '__main__':
    main()
