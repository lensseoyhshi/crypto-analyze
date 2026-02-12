#!/usr/bin/env python3
"""
智能钱包分析报表

1. 查询非高频钱包（is_high_frequency=0）及关联快照数据
2. 分析每天钱包的流动性（基于30D滚动指标）
3. 各平台下钱包稳定性分析（30D 变动性），识别稳定钱包
4. 分析不同渠道（Trojan/BullX/Photon/Axiom）的30D收益、交易频次、持仓时长（分位数汇总）
5. 按平台分组的持仓收益率（分位数）
6. 输出 Excel 报表

所有盈利/亏损均以 SOL 为单位计算，不转换为 USD
"""

import pandas as pd
import json
import os
from datetime import datetime, timedelta
from sqlalchemy import text
from config.database import get_session

# Quote Tokens（用于判断成本/收入币种）
SOL_TOKENS = {'SOL', 'Wrapped SOL', 'WSOL'}
STABLECOINS = {'USDC', 'USDT', 'USD Coin'}
QUOTE_TOKENS = SOL_TOKENS | STABLECOINS

# SOL → USD 参考价格（用于将数据库中 USD 计价的数据转换为 SOL）
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
    按日期分析钱包流动性指标（基于30D滚动窗口，所有金额以 SOL 为单位）：
    - 活跃钱包数、SOL 余额
    - 30D交易量、净流入、交易次数（转换为 SOL）
    - 30D买卖频次、PnL（SOL）
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
            # --- SOL 余额 ---
            '平均SOL余额': round(day['sol_balance'].mean(), 4),
            '总SOL余额': round(day['sol_balance'].sum(), 4),
            # --- 30D 流动性（转换为 SOL）---
            '平均30D交易量(SOL)': round(day['volume_30d'].mean() / SOL_PRICE_USD, 4),
            '总30D交易量(SOL)': round(day['volume_30d'].sum() / SOL_PRICE_USD, 4),
            '平均30D净流入(SOL)': round(day['net_inflow_30d'].mean() / SOL_PRICE_USD, 4),
            '总30D净流入(SOL)': round(day['net_inflow_30d'].sum() / SOL_PRICE_USD, 4),
            '平均30D交易次数': round(day['tx_count_30d'].mean(), 1),
            '总30D交易次数': int(day['tx_count_30d'].sum()),
            '平均30D买入次数': round(day['buy_count_30d'].mean(), 1),
            '平均30D卖出次数': round(day['sell_count_30d'].mean(), 1),
            '平均30D_PnL(SOL)': round(day['pnl_30d'].mean() / SOL_PRICE_USD, 4),
            '总30D_PnL(SOL)': round(day['pnl_30d'].sum() / SOL_PRICE_USD, 4),
        })

    result = pd.DataFrame(rows)
    print(f"  生成 {len(result)} 天流动性数据")
    return result


# ============================================================
# 2.5 钱包稳定性分析
# ============================================================

def analyze_wallet_stability(snapshot_df, wallets_df):
    """
    分析各平台下钱包在 30D 维度的稳定性

    稳定性指标：
      - 出现率：钱包在所有快照日期中出现的比例
      - 变异系数(CV = std/mean)：指标波动程度，越小越稳定

    稳定钱包标准：
      - 出现率 >= 80%
      - 30D 胜率的变异系数 < 30%

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

    metrics_30d = {
        'pnl': 'pnl_30d',
        'win_rate': 'win_rate_30d',
        'tx_count': 'tx_count_30d',
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

            for metric_label, col_name in metrics_30d.items():
                series = wdata[col_name]
                mean_val = series.mean()
                std_val = series.std() if len(series) > 1 else 0

                if abs(mean_val) > 1e-9:
                    cv = abs(std_val / mean_val) * 100
                else:
                    cv = 0.0 if abs(std_val) < 1e-9 else 999.9

                row[f'30D_{metric_label}_均值'] = round(mean_val, 2)
                row[f'30D_{metric_label}_标准差'] = round(std_val, 2)
                row[f'30D_{metric_label}_CV(%)'] = round(cv, 1)

            # 稳定性看 30D 胜率的变异系数
            wr_cv = row['30D_win_rate_CV(%)']
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
                    '30D_PnL均值(SOL)': round(wdata['pnl_30d'].mean() / SOL_PRICE_USD, 4),
                    '30D_胜率均值(%)': round(wdata['win_rate_30d'].mean(), 2),
                    '30D_胜率CV(%)': row['30D_win_rate_CV(%)'],
                    '30D_交易次数均值': round(wdata['tx_count_30d'].mean(), 1),
                    '30D_持仓时长均值(小时)': round(wdata['avg_hold_time_30d'].mean() / 3600, 2) if wdata['avg_hold_time_30d'].mean() > 0 else 0,
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
    按平台 (Trojan / BullX / Photon / Axiom) 分析（仅 30D 维度）：
      - 收益 (PnL)
      - 交易频次
      - 持仓时长
    同时输出每个平台的每日 30D 滚动趋势
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

    # ---- 汇总表（使用最新日期的快照，仅 30D）----
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

        profit_n = len(pdata[pdata['pnl_30d'] > 0])
        loss_n = len(pdata[pdata['pnl_30d'] < 0])

        pnl_series = pdata['pnl_30d'] / SOL_PRICE_USD
        vol_series = pdata['volume_30d'] / SOL_PRICE_USD

        summary_rows.append({
            '平台': pname,
            '钱包数': n,
            # PnL 分位数（SOL）
            'PnL_P10(SOL)': round(pnl_series.quantile(0.10), 4),
            'PnL_P25(SOL)': round(pnl_series.quantile(0.25), 4),
            'PnL_P50(SOL)': round(pnl_series.median(), 4),
            'PnL_P75(SOL)': round(pnl_series.quantile(0.75), 4),
            'PnL_P90(SOL)': round(pnl_series.quantile(0.90), 4),
            '总PnL(SOL)': round(pnl_series.sum(), 4),
            # 胜率 分位数
            '胜率_P25(%)': round(pdata['win_rate_30d'].quantile(0.25), 2),
            '胜率_P50(%)': round(pdata['win_rate_30d'].median(), 2),
            '胜率_P75(%)': round(pdata['win_rate_30d'].quantile(0.75), 2),
            # 交易次数 分位数
            '交易次数_P25': round(pdata['tx_count_30d'].quantile(0.25), 1),
            '交易次数_P50': round(pdata['tx_count_30d'].median(), 1),
            '交易次数_P75': round(pdata['tx_count_30d'].quantile(0.75), 1),
            # 买卖次数 中位数
            '买入次数_P50': round(pdata['buy_count_30d'].median(), 1),
            '卖出次数_P50': round(pdata['sell_count_30d'].median(), 1),
            # 持仓时长 分位数
            '持仓时长_P50(小时)': round(pdata['avg_hold_time_30d'].median() / 3600, 2) if pdata['avg_hold_time_30d'].median() > 0 else 0,
            # 交易量 分位数（SOL）
            '交易量_P25(SOL)': round(vol_series.quantile(0.25), 4),
            '交易量_P50(SOL)': round(vol_series.median(), 4),
            '交易量_P75(SOL)': round(vol_series.quantile(0.75), 4),
            # 盈亏钱包分布
            '盈利钱包数': profit_n,
            '亏损钱包数': loss_n,
            '盈利占比(%)': round(profit_n / n * 100, 1),
        })

    if summary_rows:
        result_dfs['平台汇总'] = pd.DataFrame(summary_rows)

    # ---- 每个平台的每日 30D 趋势 ----
    for pname, pcol in platforms.items():
        pdata = snapshot_df[snapshot_df[pcol] == 1]
        if pdata.empty:
            continue

        dates = sorted(pdata['snapshot_date'].unique())
        daily = []
        for d in dates:
            day = pdata[pdata['snapshot_date'] == d]
            n = day['address'].nunique()
            hold_mean = day['avg_hold_time_30d'].mean()

            daily.append({
                '日期': d,
                '钱包数': n,
                '平均30D_PnL(SOL)': round(day['pnl_30d'].mean() / SOL_PRICE_USD, 4),
                '中位30D_PnL(SOL)': round(day['pnl_30d'].median() / SOL_PRICE_USD, 4),
                '总30D_PnL(SOL)': round(day['pnl_30d'].sum() / SOL_PRICE_USD, 4),
                '平均30D胜率(%)': round(day['win_rate_30d'].mean(), 2),
                '平均30D交易次数': round(day['tx_count_30d'].mean(), 1),
                '平均30D持仓时长(小时)': round(hold_mean / 3600, 2) if hold_mean > 0 else 0,
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
      - stablecoin_amount:  稳定币(USDC/USDT)数量变化
      - sol_equivalent:     统一 SOL 等值 = sol_amount + stablecoin_amount / SOL_PRICE_USD
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

    # 统一 SOL 等值（将稳定币折算为 SOL）
    sol_equivalent = sol_total + stable_total / SOL_PRICE_USD

    # 检测代币互换：如果 SOL 变化极小（仅 gas）且没有稳定币参与，
    # 但有其他非目标代币参与（如用 Buttcoin 买 x1xhlol），则为代币互换
    sol_is_gas_only = abs(sol_total) < 0.01  # < 0.01 SOL
    no_stablecoin = abs(stable_total) < 0.01
    has_other = any(abs(t['amount']) > 0 for t in other_tokens)
    is_token_swap = sol_is_gas_only and no_stablecoin and has_other

    return {
        'sol_amount': sol_total,
        'stablecoin_amount': stable_total,
        'sol_equivalent': sol_equivalent,
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
                    'sol_amount': parsed['sol_equivalent'],
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
    计算每个钱包每个币种的收益率（以 SOL 为单位）

    返回:
      - platform_df: 按平台分组的收益率统计（分位数）
    """
    print(f"  查询 {len(addresses)} 个钱包的交易记录...")
    trades = get_wallet_transactions(addresses)

    if not trades:
        print("  无交易数据")
        return None

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
        token_symbol = buys.iloc[0]['token_symbol']

        # 过滤掉代币互换交易（成本无法可靠计算）
        normal_buys = buys[~buys['is_token_swap']]
        normal_sells = sells[~sells['is_token_swap']]

        # 成本（SOL）：仅来自非代币互换的买入（sol_amount 为负，取绝对值）
        total_cost = abs(normal_buys['sol_amount'].sum()) if not normal_buys.empty else 0

        # 如果所有买入都是代币互换，无法确定成本 → 跳过
        if total_cost < 0.0001:
            skipped_swap += 1
            continue

        # 收入（SOL）：仅来自非代币互换的卖出（sol_amount 为正）
        total_revenue = normal_sells['sol_amount'].sum() if not normal_sells.empty else 0
        total_return = (total_revenue - total_cost) / total_cost * 100

        row = {
            '钱包地址': address,
            '代币符号': token_symbol,
            '代币地址': token_address,
            '买入总成本(SOL)': round(total_cost, 4),
            '卖出总收入(SOL)': round(total_revenue, 4),
            '总收益率(%)': round(total_return, 2),
        }

        # 不同时间窗口的收益率
        for wname, wdelta in time_windows:
            w_end = first_buy_time + wdelta

            w_buys = normal_buys[normal_buys['block_time'] <= w_end]
            w_sells = normal_sells[normal_sells['block_time'] <= w_end]

            w_cost = abs(w_buys['sol_amount'].sum()) if not w_buys.empty else 0
            w_rev = w_sells['sol_amount'].sum() if not w_sells.empty else 0

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
        return None

    detail_df = pd.DataFrame(results)
    print(f"  生成 {len(detail_df)} 条持仓收益率记录")

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

            # 计算盈亏 SOL 汇总
            total_pnl_sol = (pdata['卖出总收入(SOL)'].sum() - pdata['买入总成本(SOL)'].sum())

            prow = {
                '平台': pname,
                '交易对数': n_p,
                # 总盈亏（SOL）
                '总盈亏(SOL)': round(total_pnl_sol, 4),
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

    return platform_df


# ============================================================
# 5. 保存到 Excel
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

        # 每日流动性
        write_sheet(all_results.get('daily_liquidity'), '每日流动性')

        # 稳定钱包清单
        write_sheet(all_results.get('stable_wallets'), '稳定钱包清单')

        # 平台分析（分位数汇总 + 各平台趋势）
        platform_results = all_results.get('platform', {})
        for name, df in platform_results.items():
            write_sheet(df, name)

        # 平台持仓收益率（分位数）
        write_sheet(all_results.get('platform_returns'), '平台持仓收益率')

    print(f"\n文件已保存: {os.path.abspath(filename)}")
    print(f"共 {sheet_count} 个工作表")
    return filename


# ============================================================
# 主函数
# ============================================================

def main():
    print("\n" + "=" * 60)
    print("智能钱包分析报表（SOL 计价）")
    print("=" * 60)

    # 1. 查询非高频钱包
    print("\n[1/5] 查询非高频钱包...")
    wallets_df = get_non_hf_wallets()

    if wallets_df.empty:
        print("没有钱包数据，退出")
        return

    addresses = wallets_df['address'].unique().tolist()

    # 获取关联快照数据
    print("\n获取关联快照数据...")
    snapshot_df = get_snapshot_data(addresses)

    all_results = {}

    # 2. 每天钱包流动性
    print("\n[2/5] 分析每天钱包流动性...")
    all_results['daily_liquidity'] = analyze_daily_liquidity(snapshot_df)

    # 3. 钱包稳定性分析（仅保留稳定钱包清单）
    print("\n[3/5] 分析钱包稳定性（30D 变动性）...")
    _, stable_df = analyze_wallet_stability(snapshot_df, wallets_df)
    all_results['stable_wallets'] = stable_df

    # 4. 不同渠道平台分析（分位数汇总 + 各平台趋势）
    print("\n[4/5] 分析不同渠道平台（分位数）...")
    all_results['platform'] = analyze_by_platform(snapshot_df)

    # 5. 平台持仓收益率（分位数）
    print("\n[5/5] 计算平台持仓收益率...")
    platform_df = analyze_token_returns(addresses, wallets_df)
    all_results['platform_returns'] = platform_df

    # 保存 Excel
    save_to_excel(all_results)

    print("\n分析完成!")


if __name__ == '__main__':
    main()
