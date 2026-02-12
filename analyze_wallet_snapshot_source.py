#!/usr/bin/env python3
"""
智能钱包分析报表

1. 查询非高频钱包（is_high_frequency=0）及关联快照数据
2. 分析每天钱包的流动性
3. 各平台下钱包稳定性分析（1D/7D/30D 变动性），识别稳定钱包
4. 分析不同渠道（Trojan/BullX/Photon/Axiom）的收益、交易频次、持仓时长（分位数汇总）
5. 计算每个钱包每个币种的收益率
6. 输出 Excel 报表
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta, date
from sqlalchemy import text
from config.database import get_session, db_config

# Quote Tokens（用于判断成本/收入币种）
SOL_TOKENS = {'SOL', 'Wrapped SOL', 'WSOL'}
STABLECOINS = {'USDC', 'USDT', 'USD Coin'}
QUOTE_TOKENS = SOL_TOKENS | STABLECOINS

# SOL → USD 参考价格（用于将 SOL 计价的交易统一为 USD）
# 请根据实际时段调整此值
SOL_PRICE_USD = 200


# ============================================================
# 1. 数据查询
# ============================================================

def get_non_hf_wallets():
    """
    查询 smart_wallets 中 is_high_frequency = 0 的钱包
    返回 DataFrame，包含地址、名称、平台标签、指标等
    """
    session = get_session()
    try:
        sql = text("""
            SELECT address, name,
                   uses_trojan, uses_bullx, uses_photon, uses_axiom, uses_bot,
                   is_smart_money, is_kol, is_whale, is_sniper,
                   is_hot_followed, is_hot_remarked,
                   pnl_1d, pnl_7d, pnl_30d,
                   win_rate_1d, win_rate_7d, win_rate_30d,
                   tx_count_1d, tx_count_7d, tx_count_30d,
                   avg_hold_time_1d, avg_hold_time_7d, avg_hold_time_30d,
                   balance, sol_balance
            FROM smart_wallets
            WHERE is_high_frequency = 0
        """)
        result = session.execute(sql)
        columns = list(result.keys())
        rows = result.fetchall()
        df = pd.DataFrame(rows, columns=columns)

        # 数值类型转换
        float_cols = ['pnl_1d', 'pnl_7d', 'pnl_30d',
                      'win_rate_1d', 'win_rate_7d', 'win_rate_30d',
                      'balance', 'sol_balance']
        for col in float_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        int_cols = ['tx_count_1d', 'tx_count_7d', 'tx_count_30d',
                    'avg_hold_time_1d', 'avg_hold_time_7d', 'avg_hold_time_30d',
                    'uses_trojan', 'uses_bullx', 'uses_photon', 'uses_axiom', 'uses_bot',
                    'is_smart_money', 'is_kol', 'is_whale', 'is_sniper',
                    'is_hot_followed', 'is_hot_remarked']
        for col in int_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        print(f"  查询到 {len(df)} 个非高频钱包")
        return df

    except Exception as e:
        print(f"  查询失败: {e}")
        print(f"  尝试不带 is_high_frequency 条件查询...")
        try:
            sql = text("""
                SELECT address, name,
                       uses_trojan, uses_bullx, uses_photon, uses_axiom, uses_bot,
                       is_smart_money, is_kol, is_whale, is_sniper,
                       is_hot_followed, is_hot_remarked,
                       pnl_1d, pnl_7d, pnl_30d,
                       win_rate_1d, win_rate_7d, win_rate_30d,
                       tx_count_1d, tx_count_7d, tx_count_30d,
                       avg_hold_time_1d, avg_hold_time_7d, avg_hold_time_30d,
                       balance, sol_balance
                FROM smart_wallets
            """)
            result = session.execute(sql)
            columns = list(result.keys())
            rows = result.fetchall()
            df = pd.DataFrame(rows, columns=columns)
            print(f"  (is_high_frequency 列可能不存在) 查询到 {len(df)} 个钱包")
            return df
        except Exception as e2:
            print(f"  查询全部钱包失败: {e2}")
            return pd.DataFrame()
    finally:
        session.close()


def get_snapshot_data(addresses):
    """
    获取关联的 smart_wallets_snapshot 快照数据
    按 address 批量查询，返回 DataFrame
    """
    if not addresses:
        return pd.DataFrame()

    session = get_session()
    try:
        all_dfs = []
        batch_size = 100
        addr_list = list(addresses)

        for i in range(0, len(addr_list), batch_size):
            batch = addr_list[i:i + batch_size]
            params = {f'a{j}': addr for j, addr in enumerate(batch)}
            in_clause = ', '.join([f':a{j}' for j in range(len(batch))])

            sql = text(f"""
                SELECT address, snapshot_date, name,
                       balance, sol_balance,
                       uses_trojan, uses_bullx, uses_photon, uses_axiom,
                       pnl_1d, volume_1d, net_inflow_1d,
                       tx_count_1d, buy_count_1d, sell_count_1d,
                       avg_hold_time_1d, win_rate_1d,
                       pnl_7d, volume_7d, net_inflow_7d,
                       tx_count_7d, buy_count_7d, sell_count_7d,
                       avg_hold_time_7d, win_rate_7d,
                       pnl_30d, volume_30d, net_inflow_30d,
                       tx_count_30d, buy_count_30d, sell_count_30d,
                       avg_hold_time_30d, win_rate_30d
                FROM smart_wallets_snapshot
                WHERE address IN ({in_clause})
                  AND snapshot_date >= '2026-02-03'
                ORDER BY snapshot_date ASC
            """)
            result = session.execute(sql, params)
            cols = list(result.keys())
            rows = result.fetchall()
            if rows:
                all_dfs.append(pd.DataFrame(rows, columns=cols))

        if not all_dfs:
            print("  没有找到快照数据")
            return pd.DataFrame()

        df = pd.concat(all_dfs, ignore_index=True)

        # 浮点列
        float_cols = [
            'balance', 'sol_balance',
            'pnl_1d', 'volume_1d', 'net_inflow_1d', 'win_rate_1d',
            'pnl_7d', 'volume_7d', 'net_inflow_7d', 'win_rate_7d',
            'pnl_30d', 'volume_30d', 'net_inflow_30d', 'win_rate_30d',
        ]
        for col in float_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 整数列
        int_cols = [
            'tx_count_1d', 'buy_count_1d', 'sell_count_1d', 'avg_hold_time_1d',
            'tx_count_7d', 'buy_count_7d', 'sell_count_7d', 'avg_hold_time_7d',
            'tx_count_30d', 'buy_count_30d', 'sell_count_30d', 'avg_hold_time_30d',
            'uses_trojan', 'uses_bullx', 'uses_photon', 'uses_axiom',
        ]
        for col in int_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        print(f"  获取 {len(df)} 条快照记录，"
              f"涵盖 {df['snapshot_date'].nunique()} 天、"
              f"{df['address'].nunique()} 个钱包")
        return df
    finally:
        session.close()


# ============================================================
# 2. 分析每天钱包的流动性
# ============================================================

def analyze_daily_liquidity(snapshot_df):
    """
    按日期分析钱包流动性指标：
    - 活跃钱包数、SOL/USD 余额
    - 交易量、净流入、交易次数
    - 买卖频次、日 PnL
    """
    if snapshot_df.empty:
        print("  无快照数据")
        return None

    dates = sorted(snapshot_df['snapshot_date'].unique())
    print(f"  日期范围: {dates[0]} ~ {dates[-1]}，共 {len(dates)} 天")

    rows = []
    for d in dates:
        day = snapshot_df[snapshot_df['snapshot_date'] == d]
        n = day['address'].nunique()

        rows.append({
            '日期': d,
            '活跃钱包数': n,
            # --- 余额 ---
            '平均SOL余额': round(day['sol_balance'].mean(), 4),
            '总SOL余额': round(day['sol_balance'].sum(), 4),
            '平均余额(USD)': round(day['balance'].mean(), 2),
            '总余额(USD)': round(day['balance'].sum(), 2),
            # --- 1D 流动性 ---
            '平均日交易量(USD)': round(day['volume_1d'].mean(), 2),
            '总日交易量(USD)': round(day['volume_1d'].sum(), 2),
            '平均日净流入(USD)': round(day['net_inflow_1d'].mean(), 2),
            '总日净流入(USD)': round(day['net_inflow_1d'].sum(), 2),
            '平均日交易次数': round(day['tx_count_1d'].mean(), 1),
            '总日交易次数': int(day['tx_count_1d'].sum()),
            '平均日买入次数': round(day['buy_count_1d'].mean(), 1),
            '平均日卖出次数': round(day['sell_count_1d'].mean(), 1),
            '平均1D_PnL(USD)': round(day['pnl_1d'].mean(), 2),
            '总1D_PnL(USD)': round(day['pnl_1d'].sum(), 2),
        })

    result = pd.DataFrame(rows)
    print(f"  生成 {len(result)} 天流动性数据")
    return result


# ============================================================
# 2.5 钱包稳定性分析
# ============================================================

def analyze_wallet_stability(snapshot_df, wallets_df):
    """
    分析各平台下钱包在 1D/7D/30D 维度的稳定性

    稳定性指标：
      - 出现率：钱包在所有快照日期中出现的比例
      - 变异系数(CV = std/mean)：指标波动程度，越小越稳定

    稳定钱包标准：
      - 出现率 >= 80%
      - 1D/7D/30D 胜率的变异系数均 < 30%

    返回:
      - stability_df: 所有钱包的稳定性分析明细
      - stable_df: 筛选出的稳定钱包清单
    """
    if snapshot_df.empty:
        print("  无快照数据")
        return None, None

    platforms = {
        'Trojan': 'uses_trojan',
        'BullX': 'uses_bullx',
        'Photon': 'uses_photon',
        'Axiom': 'uses_axiom',
    }

    total_dates = snapshot_df['snapshot_date'].nunique()
    print(f"  总快照天数: {total_dates}")

    dimensions = {
        '1D': {'pnl': 'pnl_1d', 'win_rate': 'win_rate_1d', 'tx_count': 'tx_count_1d'},
        '7D': {'pnl': 'pnl_7d', 'win_rate': 'win_rate_7d', 'tx_count': 'tx_count_7d'},
        '30D': {'pnl': 'pnl_30d', 'win_rate': 'win_rate_30d', 'tx_count': 'tx_count_30d'},
    }

    all_rows = []
    stable_rows = []

    for pname, pcol in platforms.items():
        platform_addrs = wallets_df[wallets_df[pcol] == 1]['address'].unique()
        pdata = snapshot_df[snapshot_df['address'].isin(platform_addrs)]

        if pdata.empty:
            print(f"    {pname}: 无快照数据")
            continue

        stable_count = 0
        for addr in platform_addrs:
            wdata = pdata[pdata['address'] == addr]
            if wdata.empty:
                continue

            appear_count = wdata['snapshot_date'].nunique()
            appear_rate = appear_count / total_dates * 100

            name_row = wallets_df[wallets_df['address'] == addr]
            wallet_name = ''
            if not name_row.empty and pd.notna(name_row.iloc[0]['name']):
                wallet_name = name_row.iloc[0]['name']

            row = {
                '平台': pname,
                '钱包地址': addr,
                '钱包名称': wallet_name,
                '快照出现次数': appear_count,
                '总快照天数': total_dates,
                '出现率(%)': round(appear_rate, 1),
            }

            is_stable = appear_rate >= 80

            for dim, cols in dimensions.items():
                for metric_label, col_name in cols.items():
                    series = wdata[col_name]
                    mean_val = series.mean()
                    std_val = series.std() if len(series) > 1 else 0

                    if abs(mean_val) > 1e-9:
                        cv = abs(std_val / mean_val) * 100
                    else:
                        cv = 0.0 if abs(std_val) < 1e-9 else 999.9

                    row[f'{dim}_{metric_label}_均值'] = round(mean_val, 2)
                    row[f'{dim}_{metric_label}_标准差'] = round(std_val, 2)
                    row[f'{dim}_{metric_label}_CV(%)'] = round(cv, 1)

                # 胜率稳定性检查
                wr_cv = row[f'{dim}_win_rate_CV(%)']
                if wr_cv > 30:
                    is_stable = False

            row['是否稳定'] = '是' if is_stable else '否'
            all_rows.append(row)

            if is_stable:
                stable_count += 1
                stable_rows.append({
                    '平台': pname,
                    '钱包地址': addr,
                    '钱包名称': wallet_name,
                    '出现率(%)': round(appear_rate, 1),
                    '1D_PnL均值': round(wdata['pnl_1d'].mean(), 2),
                    '7D_PnL均值': round(wdata['pnl_7d'].mean(), 2),
                    '30D_PnL均值': round(wdata['pnl_30d'].mean(), 2),
                    '1D_胜率均值(%)': round(wdata['win_rate_1d'].mean(), 2),
                    '7D_胜率均值(%)': round(wdata['win_rate_7d'].mean(), 2),
                    '30D_胜率均值(%)': round(wdata['win_rate_30d'].mean(), 2),
                    '1D_胜率CV(%)': row['1D_win_rate_CV(%)'],
                    '7D_胜率CV(%)': row['7D_win_rate_CV(%)'],
                    '30D_胜率CV(%)': row['30D_win_rate_CV(%)'],
                    '1D_交易次数均值': round(wdata['tx_count_1d'].mean(), 1),
                    '7D_交易次数均值': round(wdata['tx_count_7d'].mean(), 1),
                    '30D_交易次数均值': round(wdata['tx_count_30d'].mean(), 1),
                })

        print(f"    {pname}: {len(platform_addrs)} 个钱包，{stable_count} 个稳定")

    stability_df = pd.DataFrame(all_rows) if all_rows else None
    stable_df = pd.DataFrame(stable_rows) if stable_rows else None

    if stable_df is not None:
        print(f"  共 {len(stable_df)} 个稳定钱包")
    else:
        print("  未找到稳定钱包")

    return stability_df, stable_df


# ============================================================
# 3. 分析不同渠道平台
# ============================================================

def analyze_by_platform(snapshot_df):
    """
    按平台 (Trojan / BullX / Photon / Axiom) 分析：
      - 收益 (PnL)
      - 交易频次
      - 持仓时长
    分 1D / 7D / 30D 三个维度，同时输出每个平台的每日趋势
    """
    if snapshot_df.empty:
        print("  无快照数据")
        return {}

    platforms = {
        'Trojan': 'uses_trojan',
        'BullX': 'uses_bullx',
        'Photon': 'uses_photon',
        'Axiom': 'uses_axiom',
    }

    result_dfs = {}

    # ---- 汇总表（使用最新日期的快照） ----
    latest_date = snapshot_df['snapshot_date'].max()
    latest_df = snapshot_df[snapshot_df['snapshot_date'] == latest_date]
    print(f"  平台汇总分析日期: {latest_date}")

    summary_rows = []
    for pname, pcol in platforms.items():
        pdata = latest_df[latest_df[pcol] == 1]
        if pdata.empty:
            print(f"    {pname}: 无数据")
            continue

        n = len(pdata)
        print(f"    {pname}: {n} 个钱包")

        for dim, sfx in [('1D', '_1d'), ('7D', '_7d'), ('30D', '_30d')]:
            profit_n = len(pdata[pdata[f'pnl{sfx}'] > 0])
            loss_n = len(pdata[pdata[f'pnl{sfx}'] < 0])

            summary_rows.append({
                '平台': pname,
                '时间维度': dim,
                '钱包数': n,
                # PnL 分位数
                'PnL_P10': round(pdata[f'pnl{sfx}'].quantile(0.10), 2),
                'PnL_P25': round(pdata[f'pnl{sfx}'].quantile(0.25), 2),
                'PnL_P50(中位数)': round(pdata[f'pnl{sfx}'].median(), 2),
                'PnL_P75': round(pdata[f'pnl{sfx}'].quantile(0.75), 2),
                'PnL_P90': round(pdata[f'pnl{sfx}'].quantile(0.90), 2),
                '总PnL(USD)': round(pdata[f'pnl{sfx}'].sum(), 2),
                # 胜率 分位数
                '胜率_P25(%)': round(pdata[f'win_rate{sfx}'].quantile(0.25), 2),
                '胜率_P50(%)': round(pdata[f'win_rate{sfx}'].median(), 2),
                '胜率_P75(%)': round(pdata[f'win_rate{sfx}'].quantile(0.75), 2),
                # 交易次数 分位数
                '交易次数_P25': round(pdata[f'tx_count{sfx}'].quantile(0.25), 1),
                '交易次数_P50': round(pdata[f'tx_count{sfx}'].median(), 1),
                '交易次数_P75': round(pdata[f'tx_count{sfx}'].quantile(0.75), 1),
                # 买卖次数 中位数
                '买入次数_P50': round(pdata[f'buy_count{sfx}'].median(), 1),
                '卖出次数_P50': round(pdata[f'sell_count{sfx}'].median(), 1),
                # 持仓时长 分位数
                '持仓时长_P50(小时)': round(pdata[f'avg_hold_time{sfx}'].median() / 3600, 2) if pdata[f'avg_hold_time{sfx}'].median() > 0 else 0,
                # 交易量 分位数
                '交易量_P25(USD)': round(pdata[f'volume{sfx}'].quantile(0.25), 2),
                '交易量_P50(USD)': round(pdata[f'volume{sfx}'].median(), 2),
                '交易量_P75(USD)': round(pdata[f'volume{sfx}'].quantile(0.75), 2),
                # 盈亏钱包分布
                '盈利钱包数': profit_n,
                '亏损钱包数': loss_n,
                '盈利占比(%)': round(profit_n / n * 100, 1),
            })

    if summary_rows:
        result_dfs['平台汇总'] = pd.DataFrame(summary_rows)

    # ---- 每个平台的每日 7D 趋势 ----
    for pname, pcol in platforms.items():
        pdata = snapshot_df[snapshot_df[pcol] == 1]
        if pdata.empty:
            continue

        dates = sorted(pdata['snapshot_date'].unique())
        daily = []
        for d in dates:
            day = pdata[pdata['snapshot_date'] == d]
            n = day['address'].nunique()
            hold_mean = day['avg_hold_time_7d'].mean()

            daily.append({
                '日期': d,
                '钱包数': n,
                '平均7D_PnL(USD)': round(day['pnl_7d'].mean(), 2),
                '中位7D_PnL(USD)': round(day['pnl_7d'].median(), 2),
                '总7D_PnL(USD)': round(day['pnl_7d'].sum(), 2),
                '平均7D胜率(%)': round(day['win_rate_7d'].mean(), 2),
                '平均7D交易次数': round(day['tx_count_7d'].mean(), 1),
                '平均7D持仓时长(小时)': round(hold_mean / 3600, 2) if hold_mean > 0 else 0,
                '平均SOL余额': round(day['sol_balance'].mean(), 4),
            })

        if daily:
            result_dfs[f'{pname}每日趋势'] = pd.DataFrame(daily)

    return result_dfs


# ============================================================
# 4. 计算持仓收益率
# ============================================================

def parse_balance_change(bc_str):
    """
    解析 balance_change JSON

    返回 dict:
      - sol_amount:         SOL 数量变化（人类可读单位，买入为负、卖出为正）
      - stablecoin_amount:  稳定币(USDC/USDT)数量变化（等于 USD）
      - usd_amount:         统一 USD 等值 = sol_amount * SOL_PRICE_USD + stablecoin_amount
      - is_token_swap:      是否为代币互换（成本/收入主要是非 Quote 代币）
      - token_symbol, token_name, token_address, token_amount
    """
    if not bc_str:
        return None

    try:
        bc = json.loads(bc_str)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(bc, list) or len(bc) < 2:
        return None

    sol_total = 0.0
    stable_total = 0.0
    token_info = None
    other_tokens = []  # 非 Quote、非目标代币

    for item in bc:
        symbol = item.get('symbol', '')
        name = item.get('name', '')
        raw_amount = item.get('amount', 0)
        decimals = item.get('decimals', 0)
        address = item.get('address', '')

        # 转换为人类可读金额
        if decimals and decimals > 0:
            amount = raw_amount / (10 ** decimals)
        else:
            amount = raw_amount

        is_sol = (symbol in SOL_TOKENS or name in SOL_TOKENS)
        is_stable = (symbol in STABLECOINS or name in STABLECOINS)

        if is_sol:
            sol_total += amount
        elif is_stable:
            stable_total += amount
        else:
            # 非 Quote 代币：保留绝对值最大的作为目标代币
            if token_info is None or abs(amount) > abs(token_info['amount']):
                if token_info is not None:
                    other_tokens.append(token_info)
                token_info = {
                    'symbol': symbol or name or 'UNKNOWN',
                    'name': name,
                    'address': address,
                    'amount': amount,
                }
            else:
                other_tokens.append({
                    'symbol': symbol or name or 'UNKNOWN',
                    'address': address,
                    'amount': amount,
                })

    if token_info is None:
        return None

    # 统一 USD 等值
    usd_amount = sol_total * SOL_PRICE_USD + stable_total

    # 检测代币互换：如果 SOL 变化极小（仅 gas）且没有稳定币参与，
    # 但有其他非目标代币参与（如用 Buttcoin 买 x1xhlol），则为代币互换
    sol_is_gas_only = abs(sol_total) < 0.01  # < 0.01 SOL ≈ $2
    no_stablecoin = abs(stable_total) < 0.01
    has_other = any(abs(t['amount']) > 0 for t in other_tokens)
    is_token_swap = sol_is_gas_only and no_stablecoin and has_other

    return {
        'sol_amount': sol_total,
        'stablecoin_amount': stable_total,
        'usd_amount': usd_amount,
        'is_token_swap': is_token_swap,
        'token_symbol': token_info['symbol'],
        'token_name': token_info['name'],
        'token_address': token_info['address'],
        'token_amount': token_info['amount'],
    }


def get_wallet_transactions(addresses, batch_size=50):
    """
    批量查询 birdeye_wallet_transactions 中指定钱包的 buy/sell 交易
    解析 balance_change，返回交易明细列表
    """
    session = get_session()
    trades = []
    addr_list = list(addresses)
    total_batches = (len(addr_list) + batch_size - 1) // batch_size

    try:
        for i in range(0, len(addr_list), batch_size):
            batch = addr_list[i:i + batch_size]
            batch_num = i // batch_size + 1

            params = {f'a{j}': addr for j, addr in enumerate(batch)}
            in_clause = ', '.join([f':a{j}' for j in range(len(batch))])

            sql = text(f"""
                SELECT `from`, block_time, side, balance_change
                FROM birdeye_wallet_transactions
                WHERE `from` IN ({in_clause})
                  AND side IN ('buy', 'sell')
                ORDER BY block_time ASC
            """)

            result = session.execute(sql, params)
            rows = result.fetchall()

            for row in rows:
                parsed = parse_balance_change(row[3])
                if parsed is None:
                    continue

                trades.append({
                    'address': row[0],
                    'block_time': row[1],
                    'side': row[2],
                    'usd_amount': parsed['usd_amount'],
                    'is_token_swap': parsed['is_token_swap'],
                    'token_symbol': parsed['token_symbol'],
                    'token_address': parsed['token_address'],
                    'token_amount': parsed['token_amount'],
                })

            if batch_num % 5 == 0 or batch_num == total_batches:
                print(f"    进度: {batch_num}/{total_batches} 批次，"
                      f"已获取 {len(trades)} 条交易")

        print(f"  共获取 {len(trades)} 条有效 buy/sell 交易记录")
        return trades
    finally:
        session.close()


def analyze_token_returns(addresses, wallets_df=None):
    """
    计算每个钱包每个币种的收益率

    返回:
      - detail_df: 每个钱包-代币的收益率明细
      - wallet_summary_df: 每个钱包的收益汇总（所有币种聚合）
      - summary_df: 按时间窗口汇总的收益率统计（分位数）
      - platform_df: 按平台分组的收益率统计（分位数）
    """
    print(f"  查询 {len(addresses)} 个钱包的交易记录...")
    trades = get_wallet_transactions(addresses)

    if not trades:
        print("  无交易数据")
        return None, None, None, None

    trades_df = pd.DataFrame(trades)
    trades_df['block_time'] = pd.to_datetime(trades_df['block_time'])

    # 时间窗口定义
    time_windows = [
        ('1小时', timedelta(hours=1)),
        ('6小时', timedelta(hours=6)),
        ('24小时', timedelta(hours=24)),
        ('3天', timedelta(days=3)),
        ('7天', timedelta(days=7)),
        ('30天', timedelta(days=30)),
    ]

    # ---- 逐钱包-代币分析 ----
    results = []
    grouped = trades_df.groupby(['address', 'token_address'])
    total_groups = len(grouped)
    print(f"  分析 {total_groups} 个钱包-代币组合...")

    skipped_swap = 0
    processed = 0
    for (address, token_address), group in grouped:
        processed += 1
        buys = group[group['side'] == 'buy'].sort_values('block_time')
        sells = group[group['side'] == 'sell'].sort_values('block_time')

        if buys.empty:
            continue

        first_buy_time = buys.iloc[0]['block_time']
        last_sell_time = sells.iloc[-1]['block_time'] if not sells.empty else None
        token_symbol = buys.iloc[0]['token_symbol']

        # 过滤掉代币互换交易（成本无法可靠计算）
        normal_buys = buys[~buys['is_token_swap']]
        normal_sells = sells[~sells['is_token_swap']]

        # 成本：仅来自非代币互换的买入（usd_amount 为负，取绝对值）
        total_cost = abs(normal_buys['usd_amount'].sum()) if not normal_buys.empty else 0

        # 如果所有买入都是代币互换，无法确定成本 → 跳过
        if total_cost < 0.01:
            skipped_swap += 1
            continue

        # 收入：仅来自非代币互换的卖出（usd_amount 为正）
        total_revenue = normal_sells['usd_amount'].sum() if not normal_sells.empty else 0
        total_return = (total_revenue - total_cost) / total_cost * 100

        row = {
            '钱包地址': address,
            '代币符号': token_symbol,
            '代币地址': token_address,
            '首次买入时间': first_buy_time,
            '最后卖出时间': last_sell_time,
            '买入总成本': round(total_cost, 2),
            '卖出总收入': round(total_revenue, 2),
            '买入次数': len(buys),
            '卖出次数': len(sells),
            '总收益率(%)': round(total_return, 2),
        }

        # 不同时间窗口的收益率
        for wname, wdelta in time_windows:
            w_end = first_buy_time + wdelta

            w_buys = normal_buys[normal_buys['block_time'] <= w_end]
            w_sells = normal_sells[normal_sells['block_time'] <= w_end]

            w_cost = abs(w_buys['usd_amount'].sum()) if not w_buys.empty else 0
            w_rev = w_sells['usd_amount'].sum() if not w_sells.empty else 0

            if w_cost > 0:
                w_ret = (w_rev - w_cost) / w_cost * 100
            else:
                w_ret = 0.0

            row[f'{wname}_收益率(%)'] = round(w_ret, 2)

        results.append(row)

        if processed % 2000 == 0:
            print(f"    已处理 {processed}/{total_groups} 组合")

    if skipped_swap > 0:
        print(f"  跳过 {skipped_swap} 个代币互换组合（成本无法确定）")

    if not results:
        print("  无有效收益率数据")
        return None, None, None, None

    detail_df = pd.DataFrame(results)
    print(f"  生成 {len(detail_df)} 条持仓收益率记录")

    # ---- 钱包收益汇总（每个钱包所有币种聚合）----
    wallet_summary_rows = []
    for addr, wgroup in detail_df.groupby('钱包地址'):
        total_cost = wgroup['买入总成本'].sum()
        total_rev = wgroup['卖出总收入'].sum()
        total_pnl = total_rev - total_cost
        total_return = (total_pnl / total_cost * 100) if total_cost > 0 else 0

        profitable_tokens = len(wgroup[wgroup['总收益率(%)'] > 0])
        losing_tokens = len(wgroup[wgroup['总收益率(%)'] < 0])
        n_tokens = len(wgroup)

        wallet_summary_rows.append({
            '钱包地址': addr,
            '交易币种数': n_tokens,
            '总买入成本(USD)': round(total_cost, 2),
            '总卖出收入(USD)': round(total_rev, 2),
            '总盈亏(USD)': round(total_pnl, 2),
            '总收益率(%)': round(total_return, 2),
            '盈利币种数': profitable_tokens,
            '亏损币种数': losing_tokens,
            '盈利币种占比(%)': round(profitable_tokens / n_tokens * 100, 1) if n_tokens > 0 else 0,
            '最佳币种收益率(%)': round(wgroup['总收益率(%)'].max(), 2),
            '最差币种收益率(%)': round(wgroup['总收益率(%)'].min(), 2),
        })

    wallet_summary_df = pd.DataFrame(wallet_summary_rows)

    # 合并钱包名称
    if wallets_df is not None and not wallets_df.empty:
        name_map = wallets_df[['address', 'name']].drop_duplicates()
        wallet_summary_df = wallet_summary_df.merge(
            name_map, left_on='钱包地址', right_on='address', how='left'
        )
        wallet_summary_df.rename(columns={'name': '钱包名称'}, inplace=True)
        wallet_summary_df.drop(columns=['address'], inplace=True, errors='ignore')
        cols = ['钱包地址', '钱包名称'] + [c for c in wallet_summary_df.columns
                                            if c not in ['钱包地址', '钱包名称']]
        wallet_summary_df = wallet_summary_df[cols]

    # 按总收益率降序排列
    wallet_summary_df = wallet_summary_df.sort_values('总收益率(%)', ascending=False)
    print(f"  生成 {len(wallet_summary_df)} 个钱包的收益汇总")

    # ---- 按时间窗口汇总（分位数）----
    summary_rows = []

    # 总体
    n = len(detail_df)
    col_total = '总收益率(%)'
    prof_total = detail_df[detail_df[col_total] > 0]
    summary_rows.append({
        '时间窗口': '总计(所有时间)',
        '样本数': n,
        '收益率_P10(%)': round(detail_df[col_total].quantile(0.10), 2),
        '收益率_P25(%)': round(detail_df[col_total].quantile(0.25), 2),
        '收益率_P50(中位数)(%)': round(detail_df[col_total].median(), 2),
        '收益率_P75(%)': round(detail_df[col_total].quantile(0.75), 2),
        '收益率_P90(%)': round(detail_df[col_total].quantile(0.90), 2),
        '盈利比例(%)': round(len(prof_total) / n * 100, 1) if n > 0 else 0,
        '最大收益率(%)': round(detail_df[col_total].max(), 2),
        '最小收益率(%)': round(detail_df[col_total].min(), 2),
    })

    for wname, _ in time_windows:
        col = f'{wname}_收益率(%)'
        # 只统计在该时间窗口内有交易的记录
        valid = detail_df[detail_df[col] != 0]

        if valid.empty:
            summary_rows.append({
                '时间窗口': wname,
                '样本数': 0,
                '收益率_P10(%)': 0,
                '收益率_P25(%)': 0,
                '收益率_P50(中位数)(%)': 0,
                '收益率_P75(%)': 0,
                '收益率_P90(%)': 0,
                '盈利比例(%)': 0,
                '最大收益率(%)': 0,
                '最小收益率(%)': 0,
            })
        else:
            prof = valid[valid[col] > 0]
            summary_rows.append({
                '时间窗口': wname,
                '样本数': len(valid),
                '收益率_P10(%)': round(valid[col].quantile(0.10), 2),
                '收益率_P25(%)': round(valid[col].quantile(0.25), 2),
                '收益率_P50(中位数)(%)': round(valid[col].median(), 2),
                '收益率_P75(%)': round(valid[col].quantile(0.75), 2),
                '收益率_P90(%)': round(valid[col].quantile(0.90), 2),
                '盈利比例(%)': round(len(prof) / len(valid) * 100, 1),
                '最大收益率(%)': round(valid[col].max(), 2),
                '最小收益率(%)': round(valid[col].min(), 2),
            })

    summary_df = pd.DataFrame(summary_rows)

    # ---- 按平台分组的收益率（分位数）----
    platform_df = None
    if wallets_df is not None and not wallets_df.empty:
        platforms = {
            'Trojan': 'uses_trojan',
            'BullX': 'uses_bullx',
            'Photon': 'uses_photon',
            'Axiom': 'uses_axiom',
        }

        # 合并钱包平台信息
        platform_cols = ['address'] + list(platforms.values())
        merged = detail_df.merge(
            wallets_df[platform_cols],
            left_on='钱包地址', right_on='address', how='left'
        )

        plat_rows = []
        for pname, pcol in platforms.items():
            pdata = merged[merged[pcol] == 1]
            if pdata.empty:
                continue

            n_p = len(pdata)
            prof_p = pdata[pdata['总收益率(%)'] > 0]

            prow = {
                '平台': pname,
                '交易对数': n_p,
                # 总收益率 分位数
                '总收益率_P10(%)': round(pdata['总收益率(%)'].quantile(0.10), 2),
                '总收益率_P25(%)': round(pdata['总收益率(%)'].quantile(0.25), 2),
                '总收益率_P50(%)': round(pdata['总收益率(%)'].median(), 2),
                '总收益率_P75(%)': round(pdata['总收益率(%)'].quantile(0.75), 2),
                '总收益率_P90(%)': round(pdata['总收益率(%)'].quantile(0.90), 2),
                '盈利比例(%)': round(len(prof_p) / n_p * 100, 1),
            }

            # 各时间窗口分位数
            for wname, _ in time_windows:
                col = f'{wname}_收益率(%)'
                valid = pdata[pdata[col] != 0]
                if not valid.empty:
                    prow[f'{wname}_P25(%)'] = round(valid[col].quantile(0.25), 2)
                    prow[f'{wname}_P50(%)'] = round(valid[col].median(), 2)
                    prow[f'{wname}_P75(%)'] = round(valid[col].quantile(0.75), 2)
                else:
                    prow[f'{wname}_P25(%)'] = 0
                    prow[f'{wname}_P50(%)'] = 0
                    prow[f'{wname}_P75(%)'] = 0

            plat_rows.append(prow)

        if plat_rows:
            platform_df = pd.DataFrame(plat_rows)

    return detail_df, wallet_summary_df, summary_df, platform_df


# ============================================================
# 4.5 币种-钱包重叠分析
# ============================================================

def analyze_token_wallet_overlap(detail_df, wallets_df=None):
    """
    分析哪些钱包共同买了同一个币

    返回:
      - overlap_summary_df: 每个币种的买入钱包汇总（按买入钱包数降序）
      - overlap_detail_df: 每个币种下各钱包的买入明细
    """
    if detail_df is None or detail_df.empty:
        print("  无收益率明细数据")
        return None, None

    # 构建钱包名称映射
    name_map = {}
    if wallets_df is not None and not wallets_df.empty:
        for _, row in wallets_df[['address', 'name']].iterrows():
            if pd.notna(row['name']) and row['name']:
                name_map[row['address']] = row['name']

    # 按代币分组
    token_groups = detail_df.groupby(['代币地址', '代币符号'])

    summary_rows = []
    detail_rows = []

    for (token_addr, token_symbol), group in token_groups:
        wallets = group['钱包地址'].unique()
        n_wallets = len(wallets)

        wallet_names = [name_map.get(w, '') for w in wallets]
        wallet_names_clean = [n for n in wallet_names if n]

        summary_rows.append({
            '代币符号': token_symbol,
            '代币地址': token_addr,
            '买入钱包数': n_wallets,
            '钱包名称列表': ', '.join(wallet_names_clean) if wallet_names_clean else '',
            '钱包地址列表': ', '.join(wallets),
            '总买入成本(USD)': round(group['买入总成本'].sum(), 2),
            '总卖出收入(USD)': round(group['卖出总收入'].sum(), 2),
            '总盈亏(USD)': round(group['卖出总收入'].sum() - group['买入总成本'].sum(), 2),
        })

        # 明细：每个钱包一行
        for _, row in group.iterrows():
            addr = row['钱包地址']
            detail_rows.append({
                '代币符号': token_symbol,
                '代币地址': token_addr,
                '买入钱包数(该币)': n_wallets,
                '钱包地址': addr,
                '钱包名称': name_map.get(addr, ''),
                '首次买入时间': row['首次买入时间'],
                '买入总成本(USD)': row['买入总成本'],
                '卖出总收入(USD)': row['卖出总收入'],
                '买入次数': row['买入次数'],
                '卖出次数': row['卖出次数'],
                '总收益率(%)': row['总收益率(%)'],
            })

    overlap_summary_df = pd.DataFrame(summary_rows).sort_values(
        '买入钱包数', ascending=False
    ).reset_index(drop=True)

    overlap_detail_df = pd.DataFrame(detail_rows).sort_values(
        ['买入钱包数(该币)', '代币符号', '首次买入时间'],
        ascending=[False, True, True]
    ).reset_index(drop=True)

    multi_count = len(overlap_summary_df[overlap_summary_df['买入钱包数'] >= 2])
    print(f"  共 {len(overlap_summary_df)} 个币种，"
          f"其中 {multi_count} 个被 2+ 钱包共同买入")

    return overlap_summary_df, overlap_detail_df


# ============================================================
# 5. 基于30D高收益钱包的深度分析
# ============================================================

def analyze_30d_smart_money(detail_df, wallets_df):
    """
    基于30D高收益钱包的深度分析

    分析内容:
      1. 筛选30D高收益钱包（pnl_30d > 0）
      2. 收益率最高的 Top10 币种
      3. 每个钱包买到 Top10 中几个币
      4. 按 Top10 币分组，各钱包在该币上的收益率
      5. 钱包买卖时间相似性（哪些钱包总是差不多时间一起买卖）
      6. 钱包行为相似性（币种、仓位、胜率）

    返回: dict of DataFrames
    """
    if detail_df is None or detail_df.empty:
        print("  无收益率明细数据，跳过30D高收益分析")
        return {}
    if wallets_df is None or wallets_df.empty:
        print("  无钱包数据，跳过30D高收益分析")
        return {}

    results = {}

    # ---- 1. 筛选30D高收益钱包 (pnl_30d > 0) ----
    high_profit = wallets_df[wallets_df['pnl_30d'] > 0].copy()
    high_profit = high_profit.sort_values('pnl_30d', ascending=False)

    if high_profit.empty:
        print("  无30D高收益钱包（pnl_30d > 0），跳过")
        return {}

    # 最多取前200个避免计算量过大
    if len(high_profit) > 200:
        print(f"  30D高收益钱包 {len(high_profit)} 个，取PnL前200名分析")
        high_profit = high_profit.head(200)

    hp_addrs = set(high_profit['address'].unique())
    print(f"  30D高收益钱包: {len(hp_addrs)} 个")

    # 输出高收益钱包概览
    hp_overview = high_profit[['address', 'name', 'pnl_30d', 'win_rate_30d',
                                'tx_count_30d', 'avg_hold_time_30d',
                                'balance', 'sol_balance']].copy()
    hp_overview.rename(columns={
        'address': '钱包地址', 'name': '钱包名称',
        'pnl_30d': '30D_PnL(USD)', 'win_rate_30d': '30D_胜率(%)',
        'tx_count_30d': '30D_交易次数', 'avg_hold_time_30d': '30D_平均持仓(秒)',
        'balance': '余额(USD)', 'sol_balance': 'SOL余额',
    }, inplace=True)
    hp_overview = hp_overview.sort_values('30D_PnL(USD)', ascending=False).reset_index(drop=True)
    results['smart_wallet_overview'] = hp_overview

    # 构建钱包名称映射
    name_map = {}
    for _, row in wallets_df[['address', 'name']].iterrows():
        if pd.notna(row['name']) and row['name']:
            name_map[row['address']] = row['name']

    # 过滤 detail_df 只保留高收益钱包
    hp_detail = detail_df[detail_df['钱包地址'].isin(hp_addrs)].copy()
    if hp_detail.empty:
        print("  高收益钱包无交易明细数据")
        return results

    # 代币地址 -> 代币符号 映射
    token_sym_map = dict(zip(detail_df['代币地址'], detail_df['代币符号']))

    # ---- 2. Top10 收益率最高的币种 ----
    token_stats = hp_detail.groupby(['代币地址', '代币符号']).agg(
        平均收益率=('总收益率(%)', 'mean'),
        中位收益率=('总收益率(%)', 'median'),
        最高收益率=('总收益率(%)', 'max'),
        买入钱包数=('钱包地址', 'nunique'),
        总买入成本=('买入总成本', 'sum'),
        总卖出收入=('卖出总收入', 'sum'),
    ).reset_index()

    # 至少2个钱包买入才有代表性
    qualified = token_stats[token_stats['买入钱包数'] >= 2]
    if len(qualified) < 10:
        qualified = token_stats  # 不够则放宽限制

    top10 = qualified.sort_values('平均收益率', ascending=False).head(10).copy()
    top10['总盈亏(USD)'] = round(top10['总卖出收入'] - top10['总买入成本'], 2)
    top10 = top10.rename(columns={
        '平均收益率': '平均收益率(%)',
        '中位收益率': '中位收益率(%)',
        '最高收益率': '最高收益率(%)',
        '总买入成本': '总买入成本(USD)',
        '总卖出收入': '总卖出收入(USD)',
    })
    # 四舍五入
    for col in ['平均收益率(%)', '中位收益率(%)', '最高收益率(%)', '总买入成本(USD)', '总卖出收入(USD)']:
        top10[col] = top10[col].round(2)

    top10.insert(0, '排名', range(1, len(top10) + 1))
    top10 = top10.reset_index(drop=True)
    results['smart_top10_tokens'] = top10

    top10_addrs = set(top10['代币地址'].tolist())
    top10_sym_map = dict(zip(top10['代币地址'], top10['代币符号']))
    print(f"  Top10高收益币种: {', '.join(top10['代币符号'].tolist())}")

    # ---- 3. 每个钱包买到 Top10 中几个币 ----
    hp_top10 = hp_detail[hp_detail['代币地址'].isin(top10_addrs)].copy()
    if hp_top10.empty:
        print("  高收益钱包未交易任何Top10币种")
        return results

    wallet_coverage = hp_top10.groupby('钱包地址').agg(
        买到Top10币种数=('代币地址', 'nunique'),
        Top10平均收益率=('总收益率(%)', 'mean'),
        Top10总买入成本=('买入总成本', 'sum'),
        Top10总卖出收入=('卖出总收入', 'sum'),
    ).reset_index()
    wallet_coverage['Top10总盈亏(USD)'] = round(
        wallet_coverage['Top10总卖出收入'] - wallet_coverage['Top10总买入成本'], 2
    )
    wallet_coverage['钱包名称'] = wallet_coverage['钱包地址'].map(name_map).fillna('')

    # 合并30D指标
    w_info = wallets_df[['address', 'pnl_30d', 'win_rate_30d']].copy()
    wallet_coverage = wallet_coverage.merge(
        w_info, left_on='钱包地址', right_on='address', how='left'
    )
    wallet_coverage.drop(columns=['address'], inplace=True, errors='ignore')
    wallet_coverage.rename(columns={
        'pnl_30d': '30D_PnL(USD)', 'win_rate_30d': '30D_胜率(%)',
        'Top10平均收益率': 'Top10平均收益率(%)',
        'Top10总买入成本': 'Top10总买入成本(USD)',
        'Top10总卖出收入': 'Top10总卖出收入(USD)',
    }, inplace=True)

    # 每个 Top10 币种加一列标记是否买入
    for token_addr in top10_addrs:
        sym = top10_sym_map.get(token_addr, token_addr[:8])
        bought_set = set(
            hp_top10[hp_top10['代币地址'] == token_addr]['钱包地址'].unique()
        )
        wallet_coverage[sym] = wallet_coverage['钱包地址'].apply(
            lambda x, bs=bought_set: '✓' if x in bs else ''
        )

    # 列排序
    base_cols = ['钱包地址', '钱包名称', '买到Top10币种数',
                 '30D_PnL(USD)', '30D_胜率(%)',
                 'Top10平均收益率(%)', 'Top10总买入成本(USD)',
                 'Top10总卖出收入(USD)', 'Top10总盈亏(USD)']
    token_cols = [c for c in wallet_coverage.columns if c not in base_cols]
    wallet_coverage = wallet_coverage[[c for c in base_cols if c in wallet_coverage.columns] + token_cols]
    wallet_coverage = wallet_coverage.sort_values(
        '买到Top10币种数', ascending=False
    ).reset_index(drop=True)
    # 四舍五入
    for col in ['Top10平均收益率(%)', 'Top10总买入成本(USD)', 'Top10总卖出收入(USD)']:
        if col in wallet_coverage.columns:
            wallet_coverage[col] = wallet_coverage[col].round(4)

    results['smart_wallet_top10_coverage'] = wallet_coverage
    print(f"  {len(wallet_coverage)} 个钱包交易了Top10币种")

    # ---- 4. 按 Top10 币分组，各钱包在该币上的收益率 ----
    token_wallet_rows = []
    for _, trow in top10.iterrows():
        token_addr = trow['代币地址']
        token_sym = trow['代币符号']
        rank = trow['排名']

        tdata = hp_detail[hp_detail['代币地址'] == token_addr].sort_values(
            '总收益率(%)', ascending=False
        )
        for _, r in tdata.iterrows():
            addr = r['钱包地址']
            token_wallet_rows.append({
                'Top10排名': rank,
                '代币符号': token_sym,
                '代币地址': token_addr,
                '钱包地址': addr,
                '钱包名称': name_map.get(addr, ''),
                '首次买入时间': r['首次买入时间'],
                '最后卖出时间': r.get('最后卖出时间', None),
                '买入总成本(USD)': round(r['买入总成本'], 2),
                '卖出总收入(USD)': round(r['卖出总收入'], 2),
                '总收益率(%)': r['总收益率(%)'],
                '买入次数': r['买入次数'],
                '卖出次数': r['卖出次数'],
            })

    token_wallet_df = pd.DataFrame(token_wallet_rows)
    results['smart_top10_wallet_returns'] = token_wallet_df
    print(f"  Top10币种-钱包收益明细: {len(token_wallet_df)} 条")

    # ---- 5. 买卖时间相似性分析 ----
    # 构建每个钱包在 Top10 币种上的买入/卖出时间
    wallet_timing = {}
    for addr in hp_top10['钱包地址'].unique():
        w_data = hp_top10[hp_top10['钱包地址'] == addr]
        timing = {}
        for _, r in w_data.iterrows():
            fb = r['首次买入时间']
            ls = r.get('最后卖出时间', None)
            timing[r['代币地址']] = {
                'first_buy': pd.Timestamp(fb) if pd.notna(fb) else None,
                'last_sell': pd.Timestamp(ls) if pd.notna(ls) else None,
            }
        wallet_timing[addr] = timing

    timing_rows = []
    wallet_list = list(wallet_timing.keys())

    for i in range(len(wallet_list)):
        for j in range(i + 1, len(wallet_list)):
            w1, w2 = wallet_list[i], wallet_list[j]
            t1, t2 = wallet_timing[w1], wallet_timing[w2]

            common_tokens = set(t1.keys()) & set(t2.keys())
            if len(common_tokens) < 2:
                continue

            buy_diffs = []
            sell_diffs = []
            for tok in common_tokens:
                b1, b2 = t1[tok]['first_buy'], t2[tok]['first_buy']
                if b1 is not None and b2 is not None:
                    buy_diffs.append(abs((b1 - b2).total_seconds()) / 3600)

                s1, s2 = t1[tok].get('last_sell'), t2[tok].get('last_sell')
                if s1 is not None and s2 is not None:
                    sell_diffs.append(abs((s1 - s2).total_seconds()) / 3600)

            avg_buy_diff = round(np.mean(buy_diffs), 2) if buy_diffs else None
            max_buy_diff = round(max(buy_diffs), 2) if buy_diffs else None
            avg_sell_diff = round(np.mean(sell_diffs), 2) if sell_diffs else None
            max_sell_diff = round(max(sell_diffs), 2) if sell_diffs else None

            timing_rows.append({
                '钱包1地址': w1,
                '钱包1名称': name_map.get(w1, ''),
                '钱包2地址': w2,
                '钱包2名称': name_map.get(w2, ''),
                '共同Top10币种数': len(common_tokens),
                '共同买入币种': ', '.join(
                    [top10_sym_map.get(t, t[:8]) for t in common_tokens]
                ),
                '平均买入时差(小时)': avg_buy_diff,
                '最大买入时差(小时)': max_buy_diff,
                '平均卖出时差(小时)': avg_sell_diff,
                '最大卖出时差(小时)': max_sell_diff,
            })

    timing_df = pd.DataFrame(timing_rows)
    if not timing_df.empty:
        timing_df = timing_df.sort_values(
            ['共同Top10币种数', '平均买入时差(小时)'],
            ascending=[False, True]
        ).reset_index(drop=True)
    results['smart_timing_similarity'] = timing_df
    print(f"  买卖时间相似性: {len(timing_df)} 个钱包对（共同Top10>=2）")

    # ---- 6. 钱包行为相似性分析 ----
    # 为每个高收益钱包构建行为特征向量
    features = []
    for addr in hp_addrs:
        w_detail = hp_detail[hp_detail['钱包地址'] == addr]
        if w_detail.empty:
            continue

        n_tokens = len(w_detail)
        profitable_n = len(w_detail[w_detail['总收益率(%)'] > 0])

        feature = {
            'address': addr,
            'name': name_map.get(addr, ''),
            'n_tokens': n_tokens,
            'avg_return': round(w_detail['总收益率(%)'].mean(), 2),
            'total_cost': w_detail['买入总成本'].sum(),
            'win_rate': round(profitable_n / n_tokens * 100, 1) if n_tokens > 0 else 0,
            'avg_buy_count': round(w_detail['买入次数'].mean(), 1),
            'avg_sell_count': round(w_detail['卖出次数'].mean(), 1),
            'token_set': set(w_detail['代币地址'].tolist()),
        }

        w_info_row = wallets_df[wallets_df['address'] == addr]
        if not w_info_row.empty:
            feature['pnl_30d'] = w_info_row.iloc[0].get('pnl_30d', 0)
            feature['win_rate_30d'] = w_info_row.iloc[0].get('win_rate_30d', 0)
            feature['tx_count_30d'] = w_info_row.iloc[0].get('tx_count_30d', 0)
        else:
            feature['pnl_30d'] = 0
            feature['win_rate_30d'] = 0
            feature['tx_count_30d'] = 0

        features.append(feature)

    # 两两比较行为相似性
    behavior_rows = []
    for i in range(len(features)):
        for j in range(i + 1, len(features)):
            f1, f2 = features[i], features[j]

            # 币种重叠度（Jaccard 相似系数）
            common = f1['token_set'] & f2['token_set']
            union = f1['token_set'] | f2['token_set']
            jaccard = len(common) / len(union) if union else 0

            # 仓位相似度（总成本比值）
            max_cost = max(f1['total_cost'], f2['total_cost'])
            cost_sim = (min(f1['total_cost'], f2['total_cost']) / max_cost
                        if max_cost > 0 else 0)

            # 胜率相似度
            wr_diff = abs(f1['win_rate'] - f2['win_rate'])
            wr_sim = max(0, 1 - wr_diff / 100)

            # 综合相似度 = 40%币种重叠 + 30%仓位相似 + 30%胜率相似
            score = jaccard * 0.4 + cost_sim * 0.3 + wr_sim * 0.3

            if score < 0.3:
                continue  # 过滤掉相似度太低的

            # 共同币种符号（最多显示10个）
            common_syms = [token_sym_map.get(t, t[:8]) for t in list(common)[:10]]
            if len(common) > 10:
                common_syms.append(f'...等{len(common)}个')

            behavior_rows.append({
                '钱包1地址': f1['address'],
                '钱包1名称': f1['name'],
                '钱包2地址': f2['address'],
                '钱包2名称': f2['name'],
                '综合相似度': round(score, 3),
                '币种重叠度(Jaccard)': round(jaccard, 3),
                '共同币种数': len(common),
                '共同币种': ', '.join(common_syms),
                '仓位相似度': round(cost_sim, 3),
                '钱包1胜率(%)': f1['win_rate'],
                '钱包2胜率(%)': f2['win_rate'],
                '胜率差(%)': round(wr_diff, 1),
                '钱包1总成本(USD)': round(f1['total_cost'], 2),
                '钱包2总成本(USD)': round(f2['total_cost'], 2),
                '钱包1交易币种数': f1['n_tokens'],
                '钱包2交易币种数': f2['n_tokens'],
                '钱包1_30D_PnL': round(f1['pnl_30d'], 2),
                '钱包2_30D_PnL': round(f2['pnl_30d'], 2),
                '钱包1_30D_胜率(%)': round(f1['win_rate_30d'], 2),
                '钱包2_30D_胜率(%)': round(f2['win_rate_30d'], 2),
            })

    behavior_df = pd.DataFrame(behavior_rows)
    if not behavior_df.empty:
        behavior_df = behavior_df.sort_values(
            '综合相似度', ascending=False
        ).reset_index(drop=True)
    results['smart_behavior_similarity'] = behavior_df
    print(f"  行为相似性: {len(behavior_df)} 个钱包对（相似度>=0.3）")

    return results


# ============================================================
# 6. 保存到 Excel
# ============================================================

def save_to_excel(all_results, filename=None):
    """将所有分析结果保存到 Excel 文件（多工作表）"""
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'wallet_report_{timestamp}.xlsx'

    print(f"\n{'=' * 60}")
    print(f"保存报表: {filename}")
    print(f"{'=' * 60}")

    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        sheet_count = 0

        def write_sheet(df, name):
            nonlocal sheet_count
            if df is not None and not df.empty:
                sname = name[:31]  # Excel 工作表名称最大 31 字符
                df.to_excel(writer, sheet_name=sname, index=False)
                print(f"  [{sname}] {len(df)} 行")
                sheet_count += 1

        # 钱包概览
        write_sheet(all_results.get('wallets'), '钱包概览')

        # 每日流动性
        write_sheet(all_results.get('daily_liquidity'), '每日流动性')

        # 钱包稳定性分析
        write_sheet(all_results.get('wallet_stability'), '钱包稳定性分析')

        # 稳定钱包清单
        write_sheet(all_results.get('stable_wallets'), '稳定钱包清单')

        # 平台分析（分位数汇总 + 各平台趋势）
        platform_results = all_results.get('platform', {})
        for name, df in platform_results.items():
            write_sheet(df, name)

        # 钱包收益汇总（每个钱包的聚合收益）
        write_sheet(all_results.get('wallet_returns_summary'), '钱包收益汇总')

        # 持仓收益率汇总（按时间窗口，分位数）
        write_sheet(all_results.get('token_returns_summary'), '持仓收益率汇总')

        # 平台持仓收益率（分位数）
        write_sheet(all_results.get('platform_returns'), '平台持仓收益率')

        # 币种钱包重叠汇总（哪些币被多个钱包共同买入）
        write_sheet(all_results.get('token_overlap_summary'), '币种钱包重叠汇总')

        # 币种钱包重叠明细
        write_sheet(all_results.get('token_overlap_detail'), '币种钱包重叠明细')

        # ---- 30D 高收益钱包深度分析 ----
        # 30D高收益钱包概览
        write_sheet(all_results.get('smart_wallet_overview'), '30D高收益钱包概览')

        # Top10 高收益币种
        write_sheet(all_results.get('smart_top10_tokens'), '30D高收益Top10币种')

        # 钱包 Top10 覆盖情况
        write_sheet(all_results.get('smart_wallet_top10_coverage'), '钱包Top10覆盖')

        # Top10 币种各钱包收益率
        write_sheet(all_results.get('smart_top10_wallet_returns'), 'Top10币种钱包收益')

        # 买卖时间相似性
        write_sheet(all_results.get('smart_timing_similarity'), '买卖时间相似性')

        # 行为相似性
        write_sheet(all_results.get('smart_behavior_similarity'), '行为相似性')

        # 钱包币种收益明细（放最后，数据量可能很大）
        write_sheet(all_results.get('token_returns_detail'), '钱包币种收益明细')

    print(f"\n文件已保存: {os.path.abspath(filename)}")
    print(f"共 {sheet_count} 个工作表")
    return filename


# ============================================================
# 主函数
# ============================================================

def main():
    print("\n" + "=" * 60)
    print("智能钱包分析报表")
    print("=" * 60)

    # 1. 查询非高频钱包
    print("\n[1/7] 查询非高频钱包...")
    wallets_df = get_non_hf_wallets()

    if wallets_df.empty:
        print("没有钱包数据，退出")
        return

    addresses = wallets_df['address'].unique().tolist()

    # 获取关联快照数据
    print("\n获取关联快照数据...")
    snapshot_df = get_snapshot_data(addresses)

    all_results = {
        'wallets': wallets_df,
    }

    # 2. 每天钱包流动性
    print("\n[2/7] 分析每天钱包流动性...")
    all_results['daily_liquidity'] = analyze_daily_liquidity(snapshot_df)

    # 3. 钱包稳定性分析
    print("\n[3/7] 分析钱包稳定性（1D/7D/30D 变动性）...")
    stability_df, stable_df = analyze_wallet_stability(snapshot_df, wallets_df)
    all_results['wallet_stability'] = stability_df
    all_results['stable_wallets'] = stable_df

    # 4. 不同渠道平台分析（分位数汇总）
    print("\n[4/7] 分析不同渠道平台（分位数）...")
    all_results['platform'] = analyze_by_platform(snapshot_df)

    # 5. 每个钱包每个币种收益率
    print("\n[5/7] 计算钱包币种收益率...")
    detail_df, wallet_summary_df, summary_df, platform_df = analyze_token_returns(
        addresses, wallets_df
    )
    all_results['token_returns_detail'] = detail_df
    all_results['wallet_returns_summary'] = wallet_summary_df
    all_results['token_returns_summary'] = summary_df
    all_results['platform_returns'] = platform_df

    # 6. 币种-钱包重叠分析
    print("\n[6/7] 分析币种-钱包重叠（共同买入）...")
    overlap_summary, overlap_detail = analyze_token_wallet_overlap(
        detail_df, wallets_df
    )
    all_results['token_overlap_summary'] = overlap_summary
    all_results['token_overlap_detail'] = overlap_detail

    # 7. 基于30D高收益钱包的深度分析
    print("\n[7/7] 基于30D高收益钱包深度分析...")
    smart_money_results = analyze_30d_smart_money(detail_df, wallets_df)
    all_results.update(smart_money_results)

    # 保存 Excel
    save_to_excel(all_results)

    print("\n分析完成!")


if __name__ == '__main__':
    main()
