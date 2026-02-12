#!/usr/bin/env python3
"""
基于SOL等值计价的30D高收益钱包深度分析报表

只查询 get_non_hf_wallets (is_high_frequency=0) 的钱包。
所有盈利以 SOL 等值为单位（SOL + 稳定币折算为SOL）。

分析内容:
1. 30D盈利钱包概览（必须 pnl_30d > 0）
2. 钱包买入币种中盈利最高的 Top10 币种（按 SOL 盈利排序）
3. 30D盈利钱包买到 Top10 中几个币
4. 按 Top10 币分组，各钱包在该币上的 SOL 盈利
5. 哪些30D盈利钱包总是差不多一起买卖 Top10 币（时间相似性）
6. 哪些30D盈利钱包行为模式相似（币种、仓位、胜率）
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from sqlalchemy import text
from config.database import get_session

# Quote Tokens（用于判断成本/收入币种）
SOL_TOKENS = {'SOL', 'Wrapped SOL', 'WSOL'}
STABLECOINS = {'USDC', 'USDT', 'USD Coin'}
QUOTE_TOKENS = SOL_TOKENS | STABLECOINS

# 默认 SOL 参考价格
DEFAULT_SOL_PRICE_USD = 200


class SmartMoneySOLAnalyzer:
    """
    基于 SOL 等值计价的 30D 高收益钱包深度分析

    只查询 is_high_frequency=0 的钱包，筛选 pnl_30d > 0 的盈利钱包。
    所有盈利数值以 SOL 等值为单位（SOL + 稳定币折算为SOL）。

    输出 6 个 Sheet:
      1. 30D盈利钱包概览
      2. Top10高收益币种
      3. 钱包Top10覆盖
      4. Top10币种钱包盈利明细
      5. 买卖时间相似性
      6. 行为相似性
    """

    def __init__(self, sol_price_usd=DEFAULT_SOL_PRICE_USD, days=30):
        """
        Args:
            sol_price_usd: SOL 参考价格（用于稳定币→SOL折算及 pnl_30d 显示转换）
            days: 分析的天数窗口（默认30天）
        """
        self.sol_price_usd = sol_price_usd
        self.days = days

        # 数据容器
        self.wallets_df = None             # 所有非高频钱包
        self.profitable_wallets = None     # 30D盈利钱包
        self.trades_df = None              # 原始交易数据（sol_amount为SOL等值）
        self.token_profit_df = None        # 每个钱包-币种的SOL等值盈利
        self.top10_tokens = None           # Top10高收益币种
        self.name_map = {}                 # address -> 钱包名称
        self.results = {}                  # 所有结果 DataFrame

    # ============================================================
    # 数据加载
    # ============================================================

    def _load_wallets(self):
        """加载非高频钱包（is_high_frequency=0）"""
        print("\n[1/6] 加载非高频钱包...")

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
            self.wallets_df = pd.DataFrame(rows, columns=columns)

            # 数值类型转换
            float_cols = ['pnl_1d', 'pnl_7d', 'pnl_30d',
                          'win_rate_1d', 'win_rate_7d', 'win_rate_30d',
                          'balance', 'sol_balance']
            for col in float_cols:
                if col in self.wallets_df.columns:
                    self.wallets_df[col] = pd.to_numeric(
                        self.wallets_df[col], errors='coerce'
                    ).fillna(0)

            int_cols = ['tx_count_1d', 'tx_count_7d', 'tx_count_30d',
                        'avg_hold_time_1d', 'avg_hold_time_7d', 'avg_hold_time_30d']
            for col in int_cols:
                if col in self.wallets_df.columns:
                    self.wallets_df[col] = pd.to_numeric(
                        self.wallets_df[col], errors='coerce'
                    ).fillna(0).astype(int)

            # 构建钱包名称映射
            for _, row in self.wallets_df[['address', 'name']].iterrows():
                if pd.notna(row['name']) and row['name']:
                    self.name_map[row['address']] = row['name']

            print(f"  加载 {len(self.wallets_df)} 个非高频钱包")

        except Exception as e:
            print(f"  加载钱包失败: {e}")
            self.wallets_df = pd.DataFrame()
        finally:
            session.close()

    def _filter_profitable_wallets(self):
        """筛选30D盈利钱包（pnl_30d > 0），按盈利降序排列"""
        if self.wallets_df is None or self.wallets_df.empty:
            self.profitable_wallets = pd.DataFrame()
            return

        self.profitable_wallets = self.wallets_df[
            self.wallets_df['pnl_30d'] > 0
        ].copy()
        self.profitable_wallets = self.profitable_wallets.sort_values(
            'pnl_30d', ascending=False
        )

        # 添加 SOL 计价的 PnL
        self.profitable_wallets['pnl_30d_sol'] = round(
            self.profitable_wallets['pnl_30d'] / self.sol_price_usd, 4
        )

        print(f"  30D盈利钱包: {len(self.profitable_wallets)} 个")
        if len(self.profitable_wallets) > 0:
            top = self.profitable_wallets.iloc[0]
            print(f"  最高盈利: {top['pnl_30d_sol']:.4f} SOL "
                  f"(${top['pnl_30d']:.2f})")

    def _parse_balance_change(self, bc_str):
        """
        解析 balance_change JSON

        返回 dict:
          - sol_amount:         SOL 数量变化（人类可读单位，买入为负、卖出为正）
          - stablecoin_amount:  稳定币(USDC/USDT)数量变化
          - sol_equivalent:     统一 SOL 等值 = sol_amount + stablecoin_amount / sol_price_usd
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
        other_tokens = []

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
        sol_equivalent = sol_total + stable_total / self.sol_price_usd

        # 检测代币互换：如果 SOL 变化极小（仅 gas）且没有稳定币参与，
        # 但有其他非目标代币参与（如用 TokenA 买 TokenB），则为代币互换
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

    def _load_transactions(self):
        """
        加载30D盈利钱包的交易数据（近N天）

        保留 SOL 计价和稳定币计价的交易，统一用 SOL 等值计算。
        跳过代币互换（Token A ↔ Token B，SOL 仅 gas 且无稳定币参与）。
        """
        print("\n[2/6] 加载交易数据...")

        if self.profitable_wallets is None or self.profitable_wallets.empty:
            self.trades_df = pd.DataFrame()
            return

        addresses = self.profitable_wallets['address'].unique().tolist()
        session = get_session()
        trades = []
        skipped_swap = 0
        batch_size = 50
        total_batches = (len(addresses) + batch_size - 1) // batch_size

        # 时间过滤：只取近 N 天
        cutoff = datetime.now() - timedelta(days=self.days)
        cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:%S')

        try:
            for i in range(0, len(addresses), batch_size):
                batch = addresses[i:i + batch_size]
                batch_num = i // batch_size + 1

                params = {f'a{j}': addr for j, addr in enumerate(batch)}
                params['cutoff'] = cutoff_str
                in_clause = ', '.join([f':a{j}' for j in range(len(batch))])

                sql = text(f"""
                    SELECT `from`, block_time, side, balance_change
                    FROM birdeye_wallet_transactions
                    WHERE `from` IN ({in_clause})
                      AND side IN ('buy', 'sell')
                      AND block_time >= :cutoff
                    ORDER BY block_time ASC
                """)

                result = session.execute(sql, params)
                rows = result.fetchall()

                for row in rows:
                    parsed = self._parse_balance_change(row[3])
                    if parsed is None:
                        continue

                    # 跳过代币互换（Token A ↔ Token B，SOL仅gas且无稳定币）
                    if parsed['is_token_swap']:
                        skipped_swap += 1
                        continue

                    trades.append({
                        'address': row[0],
                        'block_time': row[1],
                        'side': row[2],
                        'sol_amount': parsed['sol_equivalent'],
                        'token_symbol': parsed['token_symbol'],
                        'token_address': parsed['token_address'],
                        'token_amount': parsed['token_amount'],
                    })

                if batch_num % 5 == 0 or batch_num == total_batches:
                    print(f"    进度: {batch_num}/{total_batches} 批次，"
                          f"已获取 {len(trades)} 条交易")

            if trades:
                self.trades_df = pd.DataFrame(trades)
                self.trades_df['block_time'] = pd.to_datetime(
                    self.trades_df['block_time']
                )
                print(f"  共获取 {len(self.trades_df)} 条有效交易"
                      f"（近{self.days}天，SOL等值计价）")
                if skipped_swap > 0:
                    print(f"  跳过 {skipped_swap} 条代币互换交易")
            else:
                self.trades_df = pd.DataFrame()
                print("  无有效交易数据")
        finally:
            session.close()

    # ============================================================
    # 分析计算
    # ============================================================

    def _calc_token_profits(self):
        """
        计算每个钱包每个币种的 SOL 等值盈亏，并判断持仓状态

        SOL 等值计算（SOL + 稳定币折算）:
          - sol_amount 已经是 sol_equivalent = sol + stablecoin / sol_price_usd
          - 买入: 钱包花 SOL/稳定币 买 Token → sol_amount 为负
          - 卖出: 钱包卖 Token 收 SOL/稳定币 → sol_amount 为正
          - 买入成本(SOL) = abs(sum of sol_amount for buys)
          - 卖出收入(SOL) = sum of sol_amount for sells
          - SOL盈亏 = 卖出收入 - 买入成本

        持仓状态判断:
          - 卖出比例 < 10% → 持仓中（几乎没卖）
          - 卖出比例 10%~90% → 部分卖出
          - 卖出比例 > 90% → 已清仓
        """
        print("\n[3/6] 计算每个钱包-币种的纯SOL盈亏...")

        if self.trades_df is None or self.trades_df.empty:
            self.token_profit_df = pd.DataFrame()
            return

        results = []
        grouped = self.trades_df.groupby(['address', 'token_address'])
        total_groups = len(grouped)
        skipped_dust = 0

        for idx, ((address, token_address), group) in enumerate(grouped):
            buys = group[group['side'] == 'buy'].sort_values('block_time')
            sells = group[group['side'] == 'sell'].sort_values('block_time')

            if buys.empty:
                continue

            token_symbol = buys.iloc[0]['token_symbol']
            first_buy_time = buys.iloc[0]['block_time']
            last_sell_time = (
                sells.iloc[-1]['block_time'] if not sells.empty else None
            )

            # 纯 SOL 计算：sol_amount 买入时为负数，卖出时为正数
            cost_sol = abs(buys['sol_amount'].sum())
            revenue_sol = (
                sells['sol_amount'].sum() if not sells.empty else 0.0
            )

            # 过滤掉成本极小的交易（dust / gas only）
            if cost_sol < 0.01:
                skipped_dust += 1
                continue

            # ---- 持仓状态判断 ----
            # 代币数量：买入为正，卖出为负
            bought_tokens = abs(buys['token_amount'].sum())
            sold_tokens = (
                abs(sells['token_amount'].sum()) if not sells.empty else 0.0
            )

            if bought_tokens > 0:
                sell_ratio = sold_tokens / bought_tokens
            else:
                sell_ratio = 0.0

            # 判断持仓状态
            if sell_ratio < 0.10:
                position_status = '持仓中'
            elif sell_ratio < 0.90:
                position_status = '部分卖出'
            else:
                position_status = '已清仓'

            # ---- 盈利计算（区分已实现/未实现）----
            if position_status == '持仓中':
                # 几乎没卖，所有盈亏都是未实现的
                realized_profit = 0.0
                realized_return = 0.0
                unrealized_cost = cost_sol
            elif position_status == '部分卖出':
                # 按卖出比例分摊成本
                sold_cost = cost_sol * sell_ratio
                realized_profit = revenue_sol - sold_cost
                realized_return = (
                    (realized_profit / sold_cost * 100) if sold_cost > 0 else 0
                )
                unrealized_cost = cost_sol * (1 - sell_ratio)
            else:
                # 已清仓：全部已实现
                realized_profit = revenue_sol - cost_sol
                realized_return = (
                    (realized_profit / cost_sol * 100) if cost_sol > 0 else 0
                )
                unrealized_cost = 0.0

            results.append({
                '钱包地址': address,
                '钱包名称': self.name_map.get(address, ''),
                '代币符号': token_symbol,
                '代币地址': token_address,
                '首次买入时间': first_buy_time,
                '最后卖出时间': last_sell_time,
                '持仓状态': position_status,
                '卖出比例(%)': round(min(sell_ratio * 100, 100), 1),
                '买入成本(SOL)': round(cost_sol, 4),
                '卖出收入(SOL)': round(revenue_sol, 4),
                '已实现盈亏(SOL)': round(realized_profit, 4),
                '已实现收益率(%)': round(realized_return, 2),
                '未实现成本(SOL)': round(unrealized_cost, 4),
                '买入次数': len(buys),
                '卖出次数': len(sells),
            })

            if (idx + 1) % 2000 == 0:
                print(f"    已处理 {idx + 1}/{total_groups} 组合")

        if skipped_dust > 0:
            print(f"  跳过 {skipped_dust} 个极小金额交易（< 0.01 SOL）")

        if results:
            self.token_profit_df = pd.DataFrame(results)

            # 统计持仓状态分布
            status_counts = self.token_profit_df['持仓状态'].value_counts()
            print(f"  生成 {len(self.token_profit_df)} 条钱包-币种记录:")
            for status, count in status_counts.items():
                print(f"    {status}: {count} 条")
        else:
            self.token_profit_df = pd.DataFrame()
            print("  无有效盈利数据")

    def _analyze_overview_and_top10(self):
        """
        Sheet 1: 30D盈利钱包概览（含持仓状态统计）
        Sheet 2: Top10高收益币种（综合加权排名）
        """
        print("\n[4/6] 生成盈利钱包概览 & Top10高收益币种...")

        if self.token_profit_df is None or self.token_profit_df.empty:
            return

        # ---- Sheet 1: 30D盈利钱包概览 ----
        hp = self.profitable_wallets.copy()
        hp_overview = hp[[
            'address', 'name', 'pnl_30d', 'pnl_30d_sol',
            'win_rate_30d', 'tx_count_30d',
            'avg_hold_time_30d', 'sol_balance'
        ]].copy()
        hp_overview.rename(columns={
            'address': '钱包地址',
            'name': '钱包名称',
            'pnl_30d': '30D_PnL(USD)',
            'pnl_30d_sol': '30D_PnL(SOL)',
            'win_rate_30d': '30D_胜率(%)',
            'tx_count_30d': '30D_交易次数',
            'avg_hold_time_30d': '30D_平均持仓(秒)',
            'sol_balance': 'SOL余额',
        }, inplace=True)

        # 合并交易统计（区分持仓状态）
        # 只用已清仓 + 部分卖出的数据计算已实现盈利
        closed_df = self.token_profit_df[
            self.token_profit_df['持仓状态'] != '持仓中'
        ]

        wallet_trade_stats = self.token_profit_df.groupby('钱包地址').agg(
            交易币种数=('代币地址', 'nunique'),
            总买入成本SOL=('买入成本(SOL)', 'sum'),
        ).reset_index()

        # 持仓状态统计：用 crosstab 替代 groupby+apply，兼容性更好
        status_ct = pd.crosstab(
            self.token_profit_df['钱包地址'],
            self.token_profit_df['持仓状态']
        ).reset_index()

        # 确保三列都存在
        for col in ['已清仓', '部分卖出', '持仓中']:
            if col not in status_ct.columns:
                status_ct[col] = 0

        status_ct.rename(columns={
            '已清仓': '已清仓币种',
            '部分卖出': '部分卖出币种',
            '持仓中': '持仓中币种',
        }, inplace=True)
        status_ct = status_ct[['钱包地址', '已清仓币种', '部分卖出币种', '持仓中币种']]

        wallet_trade_stats = wallet_trade_stats.merge(
            status_ct, on='钱包地址', how='left'
        )

        # 已实现盈利统计（只算已清仓+部分卖出）
        if not closed_df.empty:
            realized_stats = closed_df.groupby('钱包地址').agg(
                已实现总盈亏SOL=('已实现盈亏(SOL)', 'sum'),
                已实现盈利币种=('已实现盈亏(SOL)', lambda x: (x > 0).sum()),
                已实现亏损币种=('已实现盈亏(SOL)', lambda x: (x < 0).sum()),
            ).reset_index()
            wallet_trade_stats = wallet_trade_stats.merge(
                realized_stats, on='钱包地址', how='left'
            )
        else:
            wallet_trade_stats['已实现总盈亏SOL'] = 0
            wallet_trade_stats['已实现盈利币种'] = 0
            wallet_trade_stats['已实现亏损币种'] = 0

        wallet_trade_stats['已实现总盈亏SOL'] = wallet_trade_stats[
            '已实现总盈亏SOL'
        ].fillna(0)

        # 已实现胜率：盈利币种 / (盈利+亏损)
        denom = (
            wallet_trade_stats['已实现盈利币种']
            + wallet_trade_stats['已实现亏损币种']
        )
        wallet_trade_stats['已实现胜率(%)'] = round(
            wallet_trade_stats['已实现盈利币种'] / denom * 100, 1
        ).fillna(0)

        wallet_trade_stats.rename(columns={
            '总买入成本SOL': '总买入成本(SOL)',
            '已实现总盈亏SOL': '已实现总盈亏(SOL)',
        }, inplace=True)

        hp_overview = hp_overview.merge(
            wallet_trade_stats,
            on='钱包地址', how='left'
        )

        # 排序：SOL盈利降序
        hp_overview = hp_overview.sort_values(
            '30D_PnL(SOL)', ascending=False
        ).reset_index(drop=True)

        # 列排序
        col_order = [
            '钱包地址', '钱包名称',
            '30D_PnL(SOL)', '30D_PnL(USD)', '30D_胜率(%)', '30D_交易次数',
            '30D_平均持仓(秒)', 'SOL余额',
            '交易币种数', '已清仓币种', '部分卖出币种', '持仓中币种',
            '已实现总盈亏(SOL)', '总买入成本(SOL)',
            '已实现盈利币种', '已实现亏损币种', '已实现胜率(%)',
        ]
        hp_overview = hp_overview[
            [c for c in col_order if c in hp_overview.columns]
        ]

        self.results['30D盈利钱包概览'] = hp_overview
        print(f"  30D盈利钱包概览: {len(hp_overview)} 个钱包")

        # ---- Sheet 2: Top10 高收益币种（综合加权排名）----
        # 只分析已清仓和部分卖出的（已实现盈利可靠）
        realized_df = self.token_profit_df[
            self.token_profit_df['持仓状态'] != '持仓中'
        ]

        if realized_df.empty:
            print("  无已实现盈利数据，跳过Top10")
            return

        token_stats = realized_df.groupby(
            ['代币地址', '代币符号']
        ).agg(
            已实现总盈亏SOL=('已实现盈亏(SOL)', 'sum'),
            平均已实现盈亏SOL=('已实现盈亏(SOL)', 'mean'),
            最高已实现盈亏SOL=('已实现盈亏(SOL)', 'max'),
            盈利钱包数=('已实现盈亏(SOL)', lambda x: (x > 0).sum()),
            买入钱包数=('钱包地址', 'nunique'),
            总买入成本SOL=('买入成本(SOL)', 'sum'),
            总卖出收入SOL=('卖出收入(SOL)', 'sum'),
            平均收益率=('已实现收益率(%)', 'mean'),
        ).reset_index()

        # 补充：仍有多少钱包在持仓这个币
        holding_df = self.token_profit_df[
            self.token_profit_df['持仓状态'] == '持仓中'
        ]
        if not holding_df.empty:
            holding_stats = holding_df.groupby('代币地址').agg(
                持仓中钱包数=('钱包地址', 'nunique'),
                持仓总成本SOL=('买入成本(SOL)', 'sum'),
            ).reset_index()
            token_stats = token_stats.merge(
                holding_stats, on='代币地址', how='left'
            )
            token_stats['持仓中钱包数'] = token_stats['持仓中钱包数'].fillna(0).astype(int)
            token_stats['持仓总成本SOL'] = token_stats['持仓总成本SOL'].fillna(0)
        else:
            token_stats['持仓中钱包数'] = 0
            token_stats['持仓总成本SOL'] = 0

        # 只看有盈利的币种
        profitable_tokens = token_stats[token_stats['已实现总盈亏SOL'] > 0]
        if profitable_tokens.empty:
            print("  无盈利币种，跳过Top10")
            return

        # ---- 综合加权排名 ----
        # 维度1: 盈利钱包数（被多个钱包独立验证过）
        # 维度2: 平均收益率（每个钱包平均赚多少%）
        # 维度3: 总SOL盈利（绝对规模）
        # 归一化到 0-1，加权：40%钱包数 + 30%平均收益率 + 30%总盈利
        df_rank = profitable_tokens.copy()

        # Min-max 归一化
        def normalize(series):
            min_v, max_v = series.min(), series.max()
            if max_v == min_v:
                return pd.Series([0.5] * len(series), index=series.index)
            return (series - min_v) / (max_v - min_v)

        df_rank['_norm_wallets'] = normalize(df_rank['盈利钱包数'])
        df_rank['_norm_return'] = normalize(df_rank['平均收益率'])
        df_rank['_norm_profit'] = normalize(df_rank['已实现总盈亏SOL'])

        df_rank['综合评分'] = round(
            df_rank['_norm_wallets'] * 0.4
            + df_rank['_norm_return'] * 0.3
            + df_rank['_norm_profit'] * 0.3, 4
        )

        self.top10_tokens = df_rank.sort_values(
            '综合评分', ascending=False
        ).head(10).copy()

        # 清理临时列
        self.top10_tokens.drop(
            columns=['_norm_wallets', '_norm_return', '_norm_profit'],
            inplace=True
        )
        self.top10_tokens.insert(0, '排名', range(1, len(self.top10_tokens) + 1))

        # 四舍五入
        for col in ['已实现总盈亏SOL', '平均已实现盈亏SOL', '最高已实现盈亏SOL',
                     '总买入成本SOL', '总卖出收入SOL', '平均收益率',
                     '持仓总成本SOL', '综合评分']:
            if col in self.top10_tokens.columns:
                self.top10_tokens[col] = self.top10_tokens[col].round(4)

        self.top10_tokens.rename(columns={
            '已实现总盈亏SOL': '已实现总盈亏(SOL)',
            '平均已实现盈亏SOL': '平均已实现盈亏(SOL)',
            '最高已实现盈亏SOL': '最高已实现盈亏(SOL)',
            '平均收益率': '平均收益率(%)',
            '总买入成本SOL': '总买入成本(SOL)',
            '总卖出收入SOL': '总卖出收入(SOL)',
            '持仓总成本SOL': '持仓总成本(SOL)',
        }, inplace=True)
        self.top10_tokens = self.top10_tokens.reset_index(drop=True)

        self.results['Top10高收益币种'] = self.top10_tokens

        top10_syms = ', '.join(self.top10_tokens['代币符号'].tolist())
        print(f"  Top10高收益币种（综合加权）: {top10_syms}")

    def _analyze_wallet_top10_coverage(self):
        """
        Sheet 3: 30D盈利钱包买到 Top10 中几个币
        每个 Top10 币种加一列标记（持仓状态），直观展示覆盖情况
        """
        if self.top10_tokens is None or self.top10_tokens.empty:
            return
        if self.token_profit_df is None or self.token_profit_df.empty:
            return

        top10_addrs = set(self.top10_tokens['代币地址'].tolist())
        top10_sym_map = dict(zip(
            self.top10_tokens['代币地址'],
            self.top10_tokens['代币符号']
        ))

        # 筛选交易了 Top10 币种的记录
        hp_top10 = self.token_profit_df[
            self.token_profit_df['代币地址'].isin(top10_addrs)
        ].copy()

        if hp_top10.empty:
            print("  盈利钱包未交易任何Top10币种")
            return

        wallet_coverage = hp_top10.groupby('钱包地址').agg(
            买到Top10币种数=('代币地址', 'nunique'),
            Top10已实现盈亏SOL=('已实现盈亏(SOL)', 'sum'),
            Top10总买入成本=('买入成本(SOL)', 'sum'),
            Top10总卖出收入=('卖出收入(SOL)', 'sum'),
            Top10平均收益率=('已实现收益率(%)', 'mean'),
        ).reset_index()

        wallet_coverage['钱包名称'] = wallet_coverage['钱包地址'].map(
            self.name_map
        ).fillna('')

        # 合并30D指标（SOL计价）
        w_info = self.profitable_wallets[[
            'address', 'pnl_30d', 'pnl_30d_sol', 'win_rate_30d'
        ]].copy()
        wallet_coverage = wallet_coverage.merge(
            w_info, left_on='钱包地址', right_on='address', how='left'
        )
        wallet_coverage.drop(columns=['address'], inplace=True, errors='ignore')
        wallet_coverage.rename(columns={
            'pnl_30d': '30D_PnL(USD)',
            'pnl_30d_sol': '30D_PnL(SOL)',
            'win_rate_30d': '30D_胜率(%)',
            'Top10已实现盈亏SOL': 'Top10已实现盈亏(SOL)',
            'Top10总买入成本': 'Top10总买入成本(SOL)',
            'Top10总卖出收入': 'Top10总卖出收入(SOL)',
            'Top10平均收益率': 'Top10平均收益率(%)',
        }, inplace=True)

        # 四舍五入
        for col in ['Top10已实现盈亏(SOL)', 'Top10总买入成本(SOL)',
                     'Top10总卖出收入(SOL)', 'Top10平均收益率(%)']:
            if col in wallet_coverage.columns:
                wallet_coverage[col] = wallet_coverage[col].round(4)

        # 每个 Top10 币种加一列：标记持仓状态（✓已清仓 / ◐部分卖出 / ●持仓中）
        for token_addr in top10_addrs:
            sym = top10_sym_map.get(token_addr, token_addr[:8])
            token_records = hp_top10[hp_top10['代币地址'] == token_addr]
            status_map = dict(zip(
                token_records['钱包地址'], token_records['持仓状态']
            ))
            wallet_coverage[sym] = wallet_coverage['钱包地址'].apply(
                lambda x, sm=status_map: (
                    '●持仓' if sm.get(x) == '持仓中'
                    else '◐部分' if sm.get(x) == '部分卖出'
                    else '✓清仓' if sm.get(x) == '已清仓'
                    else ''
                )
            )

        # 列排序
        base_cols = [
            '钱包地址', '钱包名称', '买到Top10币种数',
            '30D_PnL(SOL)', '30D_PnL(USD)', '30D_胜率(%)',
            'Top10已实现盈亏(SOL)', 'Top10总买入成本(SOL)',
            'Top10总卖出收入(SOL)', 'Top10平均收益率(%)',
        ]
        token_cols = [c for c in wallet_coverage.columns if c not in base_cols]
        wallet_coverage = wallet_coverage[
            [c for c in base_cols if c in wallet_coverage.columns] + token_cols
        ]
        wallet_coverage = wallet_coverage.sort_values(
            '买到Top10币种数', ascending=False
        ).reset_index(drop=True)

        self.results['钱包Top10覆盖'] = wallet_coverage
        print(f"  {len(wallet_coverage)} 个钱包交易了Top10币种")

    def _analyze_top10_wallet_profit(self):
        """
        Sheet 4: 按 Top10 币分组，各钱包在该币上的 SOL 盈利
        包含持仓状态，区分已实现和未实现
        """
        if self.top10_tokens is None or self.top10_tokens.empty:
            return
        if self.token_profit_df is None or self.token_profit_df.empty:
            return

        rows = []
        for _, trow in self.top10_tokens.iterrows():
            token_addr = trow['代币地址']
            token_sym = trow['代币符号']
            rank = trow['排名']

            tdata = self.token_profit_df[
                self.token_profit_df['代币地址'] == token_addr
            ].sort_values('已实现盈亏(SOL)', ascending=False)

            for _, r in tdata.iterrows():
                rows.append({
                    'Top10排名': rank,
                    '代币符号': token_sym,
                    '代币地址': token_addr,
                    '钱包地址': r['钱包地址'],
                    '钱包名称': r['钱包名称'],
                    '持仓状态': r['持仓状态'],
                    '卖出比例(%)': r['卖出比例(%)'],
                    '首次买入时间': r['首次买入时间'],
                    '最后卖出时间': r['最后卖出时间'],
                    '买入成本(SOL)': r['买入成本(SOL)'],
                    '卖出收入(SOL)': r['卖出收入(SOL)'],
                    '已实现盈亏(SOL)': r['已实现盈亏(SOL)'],
                    '已实现收益率(%)': r['已实现收益率(%)'],
                    '未实现成本(SOL)': r['未实现成本(SOL)'],
                    '买入次数': r['买入次数'],
                    '卖出次数': r['卖出次数'],
                })

        if rows:
            df = pd.DataFrame(rows)
            self.results['Top10币种钱包盈利明细'] = df
            print(f"  Top10币种-钱包盈利明细: {len(df)} 条")

    def _analyze_timing_similarity(self):
        """
        Sheet 5: 哪些30D盈利钱包总是差不多一起买卖 Top10 币

        对所有交易了 Top10 币种的钱包两两比较:
          - 比较它们在共同买入的 Top10 币种上的首次买入时间差
          - 比较最后卖出时间差
          - 计算时间相似度分数（时差越小越相似）
        """
        print("\n[5/6] 分析买卖时间相似性...")

        if self.top10_tokens is None or self.top10_tokens.empty:
            return
        if self.token_profit_df is None or self.token_profit_df.empty:
            return

        top10_addrs = set(self.top10_tokens['代币地址'].tolist())
        top10_sym_map = dict(zip(
            self.top10_tokens['代币地址'],
            self.top10_tokens['代币符号']
        ))

        hp_top10 = self.token_profit_df[
            self.token_profit_df['代币地址'].isin(top10_addrs)
        ].copy()

        if hp_top10.empty:
            return

        # 构建时间字典: wallet -> {token_addr: {first_buy, last_sell}}
        wallet_timing = {}
        for addr in hp_top10['钱包地址'].unique():
            w_data = hp_top10[hp_top10['钱包地址'] == addr]
            timing = {}
            for _, r in w_data.iterrows():
                fb = r['首次买入时间']
                ls = r['最后卖出时间']
                timing[r['代币地址']] = {
                    'first_buy': pd.Timestamp(fb) if pd.notna(fb) else None,
                    'last_sell': pd.Timestamp(ls) if pd.notna(ls) else None,
                }
            wallet_timing[addr] = timing

        # 两两比较
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
                        buy_diffs.append(
                            abs((b1 - b2).total_seconds()) / 3600
                        )

                    s1 = t1[tok].get('last_sell')
                    s2 = t2[tok].get('last_sell')
                    if s1 is not None and s2 is not None:
                        sell_diffs.append(
                            abs((s1 - s2).total_seconds()) / 3600
                        )

                avg_buy_diff = (
                    round(np.mean(buy_diffs), 2) if buy_diffs else None
                )
                max_buy_diff = (
                    round(max(buy_diffs), 2) if buy_diffs else None
                )
                avg_sell_diff = (
                    round(np.mean(sell_diffs), 2) if sell_diffs else None
                )
                max_sell_diff = (
                    round(max(sell_diffs), 2) if sell_diffs else None
                )

                # 时间相似度分数: 1 / (1 + avg_diff)，越高越相似
                buy_score = (
                    1 / (1 + avg_buy_diff) if avg_buy_diff is not None else 0
                )
                sell_score = (
                    1 / (1 + avg_sell_diff) if avg_sell_diff is not None else 0
                )
                timing_score = round((buy_score + sell_score) / 2, 3)

                timing_rows.append({
                    '钱包1地址': w1,
                    '钱包1名称': self.name_map.get(w1, ''),
                    '钱包2地址': w2,
                    '钱包2名称': self.name_map.get(w2, ''),
                    '时间相似度': timing_score,
                    '共同Top10币种数': len(common_tokens),
                    '共同买入币种': ', '.join(
                        [top10_sym_map.get(t, t[:8]) for t in common_tokens]
                    ),
                    '平均买入时差(小时)': avg_buy_diff,
                    '最大买入时差(小时)': max_buy_diff,
                    '平均卖出时差(小时)': avg_sell_diff,
                    '最大卖出时差(小时)': max_sell_diff,
                })

        if timing_rows:
            timing_df = pd.DataFrame(timing_rows)
            timing_df = timing_df.sort_values(
                ['共同Top10币种数', '时间相似度'],
                ascending=[False, False]
            ).reset_index(drop=True)
            self.results['买卖时间相似性'] = timing_df
            print(f"  买卖时间相似性: {len(timing_df)} 个钱包对"
                  f"（共同Top10>=2）")
        else:
            print("  无足够数据进行时间相似性分析")

    def _analyze_behavior_similarity(self):
        """
        Sheet 6: 哪些30D盈利钱包行为模式相似

        对所有盈利钱包两两比较:
          - 币种重叠度 (Jaccard): 买了多少相同的币
          - 仓位相似度: 总买入成本(SOL)接近程度
          - 胜率相似度: 盈利币种占比接近程度
          - 综合相似度 = 40%币种 + 30%仓位 + 30%胜率
        """
        print("\n[6/6] 分析行为相似性...")

        if self.token_profit_df is None or self.token_profit_df.empty:
            return

        hp_addrs = set(self.profitable_wallets['address'].unique())
        token_sym_map = dict(zip(
            self.token_profit_df['代币地址'],
            self.token_profit_df['代币符号']
        ))

        # 为每个盈利钱包构建行为特征向量
        features = []
        for addr in hp_addrs:
            w_detail = self.token_profit_df[
                self.token_profit_df['钱包地址'] == addr
            ]
            if w_detail.empty:
                continue

            n_tokens = len(w_detail)
            # 已实现盈利的币种数（不含持仓中）
            closed = w_detail[w_detail['持仓状态'] != '持仓中']
            profitable_n = len(closed[closed['已实现盈亏(SOL)'] > 0])
            closed_n = len(closed)

            feature = {
                'address': addr,
                'name': self.name_map.get(addr, ''),
                'n_tokens': n_tokens,
                'closed_tokens': closed_n,
                'holding_tokens': n_tokens - closed_n,
                'total_cost_sol': w_detail['买入成本(SOL)'].sum(),
                'realized_profit_sol': closed['已实现盈亏(SOL)'].sum() if not closed.empty else 0,
                'win_rate': round(
                    profitable_n / closed_n * 100, 1
                ) if closed_n > 0 else 0,
                'avg_buy_count': round(w_detail['买入次数'].mean(), 1),
                'avg_sell_count': round(w_detail['卖出次数'].mean(), 1),
                'token_set': set(w_detail['代币地址'].tolist()),
            }

            w_info_row = self.wallets_df[self.wallets_df['address'] == addr]
            if not w_info_row.empty:
                feature['pnl_30d'] = w_info_row.iloc[0].get('pnl_30d', 0)
                feature['pnl_30d_sol'] = round(
                    feature['pnl_30d'] / self.sol_price_usd, 4
                )
                feature['win_rate_30d'] = w_info_row.iloc[0].get(
                    'win_rate_30d', 0
                )
                feature['tx_count_30d'] = w_info_row.iloc[0].get(
                    'tx_count_30d', 0
                )
            else:
                feature['pnl_30d'] = 0
                feature['pnl_30d_sol'] = 0
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
                max_cost = max(f1['total_cost_sol'], f2['total_cost_sol'])
                cost_sim = (
                    min(f1['total_cost_sol'], f2['total_cost_sol']) / max_cost
                    if max_cost > 0 else 0
                )

                # 胜率相似度
                wr_diff = abs(f1['win_rate'] - f2['win_rate'])
                wr_sim = max(0, 1 - wr_diff / 100)

                # 综合相似度 = 40%币种重叠 + 30%仓位相似 + 30%胜率相似
                score = jaccard * 0.4 + cost_sim * 0.3 + wr_sim * 0.3

                if score < 0.3:
                    continue  # 过滤掉相似度太低的

                # 共同币种符号（最多显示10个）
                common_syms = [
                    token_sym_map.get(t, t[:8]) for t in list(common)[:10]
                ]
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
                    '钱包1已实现胜率(%)': f1['win_rate'],
                    '钱包2已实现胜率(%)': f2['win_rate'],
                    '胜率差(%)': round(wr_diff, 1),
                    '钱包1总成本(SOL)': round(f1['total_cost_sol'], 4),
                    '钱包2总成本(SOL)': round(f2['total_cost_sol'], 4),
                    '钱包1已实现盈利(SOL)': round(f1['realized_profit_sol'], 4),
                    '钱包2已实现盈利(SOL)': round(f2['realized_profit_sol'], 4),
                    '钱包1交易币种数': f1['n_tokens'],
                    '钱包2交易币种数': f2['n_tokens'],
                    '钱包1持仓中币种': f1['holding_tokens'],
                    '钱包2持仓中币种': f2['holding_tokens'],
                    '钱包1_30D_PnL(SOL)': f1['pnl_30d_sol'],
                    '钱包2_30D_PnL(SOL)': f2['pnl_30d_sol'],
                    '钱包1_30D_胜率(%)': round(f1['win_rate_30d'], 2),
                    '钱包2_30D_胜率(%)': round(f2['win_rate_30d'], 2),
                })

        if behavior_rows:
            behavior_df = pd.DataFrame(behavior_rows)
            behavior_df = behavior_df.sort_values(
                '综合相似度', ascending=False
            ).reset_index(drop=True)
            self.results['行为相似性'] = behavior_df
            print(f"  行为相似性: {len(behavior_df)} 个钱包对"
                  f"（相似度>=0.3）")
        else:
            print("  无足够数据进行行为相似性分析")

    # ============================================================
    # 报表输出
    # ============================================================

    def _save_report(self):
        """保存所有分析结果到 Excel"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'smart_money_sol_report_{timestamp}.xlsx'

        print(f"\n{'=' * 60}")
        print(f"保存报表: {filename}")
        print(f"{'=' * 60}")

        sheet_order = [
            '30D盈利钱包概览',
            'Top10高收益币种',
            '钱包Top10覆盖',
            'Top10币种钱包盈利明细',
            '买卖时间相似性',
            '行为相似性',
        ]

        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            sheet_count = 0
            for name in sheet_order:
                df = self.results.get(name)
                if df is not None and not df.empty:
                    sname = name[:31]  # Excel 工作表名最大31字符
                    df.to_excel(writer, sheet_name=sname, index=False)
                    print(f"  [{sname}] {len(df)} 行")
                    sheet_count += 1

        print(f"\n文件已保存: {os.path.abspath(filename)}")
        print(f"共 {sheet_count} 个工作表")
        return filename

    # ============================================================
    # 主流程
    # ============================================================

    def run(self):
        """执行完整分析流程"""
        print("\n" + "=" * 60)
        print("30D高收益钱包 纯SOL 计价深度分析")
        print(f"盈亏计算: SOL 等值（SOL + 稳定币折算为SOL）")
        print(f"SOL 参考价格: ${self.sol_price_usd}（用于稳定币→SOL折算及 pnl_30d 显示转换）")
        print(f"分析时间窗口: 近 {self.days} 天")
        print("=" * 60)

        # 1. 加载非高频钱包
        self._load_wallets()
        if self.wallets_df is None or self.wallets_df.empty:
            print("没有钱包数据，退出")
            return

        # 2. 筛选30D盈利钱包
        self._filter_profitable_wallets()
        if self.profitable_wallets is None or self.profitable_wallets.empty:
            print("没有30D盈利钱包，退出")
            return

        # 3. 加载近30D交易数据
        self._load_transactions()
        if self.trades_df is None or self.trades_df.empty:
            print("没有交易数据，退出")
            return

        # 4. 计算每个钱包-币种的SOL盈利
        self._calc_token_profits()
        if self.token_profit_df is None or self.token_profit_df.empty:
            print("没有有效盈利数据，退出")
            return

        # 5. 生成概览 + Top10高收益币种
        self._analyze_overview_and_top10()

        # 6. 钱包Top10覆盖（买到几个）
        self._analyze_wallet_top10_coverage()

        # 7. Top10币种-钱包盈利明细
        self._analyze_top10_wallet_profit()

        # 8. 买卖时间相似性
        self._analyze_timing_similarity()

        # 9. 行为相似性
        self._analyze_behavior_similarity()

        # 10. 保存报表
        self._save_report()

        print("\n分析完成!")


if __name__ == '__main__':
    analyzer = SmartMoneySOLAnalyzer(sol_price_usd=200)
    analyzer.run()
