#!/usr/bin/env python3
"""
潜力币筛选 - 盈利钱包集中买入分析

逻辑:
  1. 筛选30D盈利钱包（pnl_30d > 0，非高频）
  2. 加载这些钱包的30D交易记录
  3. 找出被 >= N 个盈利钱包在时间窗口内集中首次买入的Token
  4. 展示买入明细和钱包关系

时间窗口说明:
  - 对每个Token，取每个钱包的首次买入时间
  - 用滑动窗口找到 buy_window_hours 内首次买入钱包数最多的区间
  - 如果窗口内钱包数 >= min_wallets，判定为"集中买入信号"

输出 3 个 Sheet:
  1. 集中买入信号 - 被盈利钱包集中买入的Token，按买入钱包数排序
  2. 买入钱包明细 - 每个信号Token的具体买入钱包、时间、金额
  3. 盈利钱包列表 - 所有30D盈利钱包及其指标
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from sqlalchemy import text
from config.database import get_session

# ============================================================
# Constants
# ============================================================

SOL_TOKENS = {'SOL', 'Wrapped SOL', 'WSOL'}
STABLECOINS = {'USDC', 'USDT', 'USD Coin'}
SOL_TOKEN_ADDRESSES = {
    'So11111111111111111111111111111111111111112',
    'So11111111111111111111111111111111111111111',
}
DEFAULT_SOL_PRICE_USD = 200


class PotentialCoinAnalyzer:
    """
    潜力币筛选分析器（精简版）

    核心: 30D盈利钱包 → 交易数据 → 集中买入检测 → 输出数据
    """

    def __init__(self, min_wallets=2, buy_window_hours=48,
                 sol_price_usd=DEFAULT_SOL_PRICE_USD):
        """
        Args:
            min_wallets: 集中买入最低钱包数（默认2）
            buy_window_hours: 集中买入时间窗口（默认48小时）
            sol_price_usd: SOL参考价格（仅用于稳定币折算）
        """
        self.min_wallets = min_wallets
        self.buy_window_hours = buy_window_hours
        self.sol_price_usd = sol_price_usd

        self.wallets_df = None       # 盈利钱包 DataFrame
        self.trades_df = None        # 交易数据 DataFrame
        self.name_map = {}           # address -> name
        self.wallet_labels = {}      # address -> {labels}
        self.results = {}            # sheet_name -> DataFrame

    # ============================================================
    # Step 1: 加载30D盈利钱包
    # ============================================================

    def _load_profitable_wallets(self):
        """筛选30D盈利钱包（pnl_30d > 0，排除高频钱包）"""
        print("\n[Step 1] 加载30D盈利钱包...")
        session = get_session()
        try:
            sql = text("""
                SELECT address, name,
                       is_smart_money, is_kol, is_whale, is_sniper,
                       is_hot_followed, is_hot_remarked,
                       pnl_30d, pnl_30d_roi, win_rate_30d,
                       tx_count_30d, avg_hold_time_30d,
                       balance, sol_balance
                FROM smart_wallets
                WHERE pnl_30d > 0
                  AND is_high_frequency = 0
                ORDER BY pnl_30d DESC
            """)
            result = session.execute(sql)
            columns = list(result.keys())
            rows = result.fetchall()
            self.wallets_df = pd.DataFrame(rows, columns=columns)

            for col in ['pnl_30d', 'pnl_30d_roi', 'win_rate_30d',
                        'balance', 'sol_balance']:
                if col in self.wallets_df.columns:
                    self.wallets_df[col] = pd.to_numeric(
                        self.wallets_df[col], errors='coerce'
                    ).fillna(0)

            for col in ['tx_count_30d', 'avg_hold_time_30d']:
                if col in self.wallets_df.columns:
                    self.wallets_df[col] = pd.to_numeric(
                        self.wallets_df[col], errors='coerce'
                    ).fillna(0).astype(int)

            for _, row in self.wallets_df.iterrows():
                addr = row['address']
                if pd.notna(row['name']) and row['name']:
                    self.name_map[addr] = row['name']
                self.wallet_labels[addr] = {
                    'is_smart_money': int(row.get('is_smart_money', 0) or 0),
                    'is_kol': int(row.get('is_kol', 0) or 0),
                    'is_whale': int(row.get('is_whale', 0) or 0),
                    'is_sniper': int(row.get('is_sniper', 0) or 0),
                    'is_hot_followed': int(row.get('is_hot_followed', 0) or 0),
                    'is_hot_remarked': int(row.get('is_hot_remarked', 0) or 0),
                }

            print(f"  30D盈利钱包: {len(self.wallets_df)} 个")
            if not self.wallets_df.empty:
                top = self.wallets_df.iloc[0]
                print(f"  最高盈利: {top['address'][:10]}.. "
                      f"PnL=${float(top['pnl_30d']):.2f}")

            # Sheet 3: 盈利钱包列表
            if not self.wallets_df.empty:
                wallet_list = self.wallets_df.copy()
                wallet_list.rename(columns={
                    'address': '钱包地址',
                    'name': '钱包名称',
                    'pnl_30d': '30D盈利(USD)',
                    'pnl_30d_roi': '30D收益率(%)',
                    'win_rate_30d': '30D胜率(%)',
                    'tx_count_30d': '30D交易次数',
                    'avg_hold_time_30d': '平均持仓(秒)',
                    'balance': '余额(USD)',
                    'sol_balance': 'SOL余额',
                }, inplace=True)

                label_cols = ['is_smart_money', 'is_kol', 'is_whale',
                              'is_sniper', 'is_hot_followed', 'is_hot_remarked']
                label_names = ['聪明钱', 'KOL', '巨鲸',
                               '狙击手', '热门追踪', '热门备注']
                for old, new in zip(label_cols, label_names):
                    if old in wallet_list.columns:
                        wallet_list[new] = wallet_list[old].apply(
                            lambda x: '是' if x else ''
                        )
                        wallet_list.drop(columns=[old], inplace=True)

                self.results['盈利钱包列表'] = wallet_list

        except Exception as e:
            print(f"  加载失败: {e}")
            import traceback
            traceback.print_exc()
            self.wallets_df = pd.DataFrame()
        finally:
            session.close()

    # ============================================================
    # Step 2: 加载交易数据
    # ============================================================

    def _parse_balance_change(self, bc_str):
        """解析 balance_change JSON，提取SOL金额和Token信息"""
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

        for item in bc:
            symbol = item.get('symbol', '')
            name = item.get('name', '')
            raw_amount = item.get('amount', 0)
            decimals = item.get('decimals', 0)
            address = item.get('address', '')

            if decimals and decimals > 0:
                amount = raw_amount / (10 ** decimals)
            else:
                amount = raw_amount

            is_sol = (symbol in SOL_TOKENS or name in SOL_TOKENS
                      or address in SOL_TOKEN_ADDRESSES)
            is_stable = (symbol in STABLECOINS or name in STABLECOINS)

            if is_sol:
                sol_total += amount
            elif is_stable:
                stable_total += amount
            else:
                if token_info is None or abs(amount) > abs(token_info['amount']):
                    token_info = {
                        'symbol': symbol or name or 'UNKNOWN',
                        'name': name,
                        'address': address,
                        'amount': amount,
                    }

        if token_info is None:
            return None

        sol_equivalent = sol_total + stable_total / self.sol_price_usd
        if abs(sol_equivalent) < 0.001:
            return None

        token_amt = abs(token_info['amount'])
        price_sol = abs(sol_equivalent) / token_amt if token_amt > 0 else 0

        return {
            'sol_amount': sol_equivalent,
            'token_symbol': token_info['symbol'],
            'token_name': token_info['name'],
            'token_address': token_info['address'],
            'token_amount': token_info['amount'],
            'price_sol': price_sol,
        }

    def _load_transactions(self):
        """加载盈利钱包的30D交易数据"""
        print("\n[Step 2] 加载盈利钱包交易数据...")

        if self.wallets_df is None or self.wallets_df.empty:
            self.trades_df = pd.DataFrame()
            return

        addresses = self.wallets_df['address'].tolist()
        session = get_session()
        cutoff = datetime.now() - timedelta(days=30)
        cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:%S')

        try:
            trades = []
            skipped = 0
            batch_size = 50
            total_batches = (len(addresses) + batch_size - 1) // batch_size

            for i in range(0, len(addresses), batch_size):
                batch = addresses[i:i + batch_size]
                batch_num = i // batch_size + 1

                params = {f'a{j}': addr for j, addr in enumerate(batch)}
                params['cutoff'] = cutoff_str
                in_clause = ', '.join([f':a{j}' for j in range(len(batch))])

                sql = text(f"""
                    SELECT `from`, block_time, block_time_unix, side,
                           balance_change
                    FROM birdeye_wallet_transactions
                    WHERE `from` IN ({in_clause})
                      AND side IN ('buy', 'sell')
                      AND block_time >= :cutoff
                    ORDER BY block_time ASC
                """)

                result = session.execute(sql, params)
                rows = result.fetchall()

                for row in rows:
                    parsed = self._parse_balance_change(row[4])
                    if parsed is None or parsed['price_sol'] <= 0:
                        skipped += 1
                        continue

                    trades.append({
                        'wallet_address': row[0],
                        'block_time': row[1],
                        'block_time_unix': row[2],
                        'side': row[3],
                        'sol_amount': parsed['sol_amount'],
                        'token_symbol': parsed['token_symbol'],
                        'token_name': parsed['token_name'],
                        'token_address': parsed['token_address'],
                        'token_amount': parsed['token_amount'],
                        'price_sol': parsed['price_sol'],
                    })

                if batch_num % 10 == 0 or batch_num == total_batches:
                    print(f"    进度: {batch_num}/{total_batches}，"
                          f"有效 {len(trades)} 条")

            if trades:
                self.trades_df = pd.DataFrame(trades)
                self.trades_df['block_time'] = pd.to_datetime(
                    self.trades_df['block_time']
                )
                print(f"  共 {len(self.trades_df)} 条有效交易（跳过 {skipped}）")
                print(f"  涉及 {self.trades_df['wallet_address'].nunique()} 个钱包、"
                      f"{self.trades_df['token_address'].nunique()} 个Token")
            else:
                self.trades_df = pd.DataFrame()
                print("  无有效交易数据")

        except Exception as e:
            print(f"  加载失败: {e}")
            import traceback
            traceback.print_exc()
            self.trades_df = pd.DataFrame()
        finally:
            session.close()

    # ============================================================
    # Step 3: 集中买入检测
    # ============================================================

    def _find_best_window(self, wallet_first_buys):
        """
        滑动窗口: 找到 buy_window_hours 内首次买入钱包数最多的区间

        Args:
            wallet_first_buys: list of (wallet_address, first_buy_time)

        Returns:
            dict {wallets, start, end, count} 或 None
        """
        if len(wallet_first_buys) < self.min_wallets:
            return None

        sorted_buys = sorted(wallet_first_buys, key=lambda x: x[1])
        window_td = timedelta(hours=self.buy_window_hours)

        best = None
        for i in range(len(sorted_buys)):
            window_end = sorted_buys[i][1] + window_td
            in_window = [
                sb for sb in sorted_buys[i:]
                if sb[1] <= window_end
            ]

            if (len(in_window) >= self.min_wallets
                    and (best is None or len(in_window) > best['count'])):
                best = {
                    'wallets': [w[0] for w in in_window],
                    'times': [w[1] for w in in_window],
                    'start': in_window[0][1],
                    'end': in_window[-1][1],
                    'count': len(in_window),
                }

        return best

    def _detect_concentrated_buying(self):
        """
        集中买入检测

        对每个Token:
          1. 取每个盈利钱包的首次买入时间
          2. 滑动窗口找最密集的区间
          3. 窗口内钱包数 >= min_wallets → 信号
          4. 计算收益倍数
        """
        print(f"\n[Step 3] 集中买入检测（窗口={self.buy_window_hours}h，"
              f"最少{self.min_wallets}个钱包）...")

        if self.trades_df is None or self.trades_df.empty:
            return

        buys = self.trades_df[self.trades_df['side'] == 'buy']
        sells = self.trades_df[self.trades_df['side'] == 'sell']

        signals = []
        detail_rows = []

        for token_address, token_buys in buys.groupby('token_address'):
            # Each wallet's first buy time
            wallet_first = (
                token_buys.groupby('wallet_address')['block_time']
                .min().reset_index()
            )
            wallet_first_list = list(zip(
                wallet_first['wallet_address'],
                wallet_first['block_time']
            ))

            # Find concentrated window
            window = self._find_best_window(wallet_first_list)
            if window is None:
                continue

            token_symbol = token_buys.iloc[0]['token_symbol']
            token_name = token_buys.iloc[0]['token_name']

            # --- All buys for this token (not just window) ---
            total_buy_wallets = token_buys['wallet_address'].nunique()
            total_sol_cost = abs(token_buys['sol_amount'].sum())
            total_tokens_bought = abs(token_buys['token_amount'].sum())
            avg_buy_price = (
                total_sol_cost / total_tokens_bought
                if total_tokens_bought > 0 else 0
            )

            # --- Price from all trades ---
            token_all = self.trades_df[
                self.trades_df['token_address'] == token_address
            ].sort_values('block_time')
            latest_price = token_all.iloc[-1]['price_sol']
            latest_time = token_all.iloc[-1]['block_time']
            max_price = token_all['price_sol'].max()

            current_return = (
                latest_price / avg_buy_price if avg_buy_price > 0 else 0
            )
            max_return = (
                max_price / avg_buy_price if avg_buy_price > 0 else 0
            )

            # --- Sell info ---
            token_sells = sells[sells['token_address'] == token_address]
            n_sell_wallets = (
                token_sells['wallet_address'].nunique()
                if not token_sells.empty else 0
            )
            total_sol_revenue = (
                token_sells['sol_amount'].sum()
                if not token_sells.empty else 0
            )

            # --- Per-wallet holding analysis ---
            wallet_hold_stats = {}
            hold_hours_list = []
            still_holding_count = 0
            wallet_return_multiples = []
            now_ts = pd.Timestamp(datetime.now())

            for _w in token_buys['wallet_address'].unique():
                _wb = token_buys[token_buys['wallet_address'] == _w]
                _w_first = _wb['block_time'].min()
                # Buy: sol_amount is negative (SOL out), so cost is absolute value
                _w_sol_cost = abs(_wb['sol_amount'].sum())
                _w_tokens = abs(_wb['token_amount'].sum())

                _ws = token_sells[token_sells['wallet_address'] == _w]
                # Sell: sol_amount is positive (SOL in), so revenue is absolute value
                _w_sell_sol = (abs(_ws['sol_amount'].sum())
                               if not _ws.empty else 0)
                _w_sell_cnt = len(_ws) if not _ws.empty else 0
                _w_last_sell = (_ws['block_time'].max()
                                if not _ws.empty else None)
                _w_sold = not _ws.empty and _w_sell_sol > 0

                _hold_end = _w_last_sell if _w_sold else now_ts
                _hold_h = max(
                    (_hold_end - _w_first).total_seconds() / 3600, 0
                )
                hold_hours_list.append(_hold_h)

                if not _w_sold:
                    still_holding_count += 1

                # Calculate PnL
                if _w_sol_cost > 0:
                    if _w_sold:
                        # Realized PnL: revenue - cost
                        _ret_sol = _w_sell_sol - _w_sol_cost
                        _ret_mul = _w_sell_sol / _w_sol_cost
                    else:
                        # Unrealized PnL: current value - cost
                        _cur_val = _w_tokens * latest_price
                        _ret_sol = _cur_val - _w_sol_cost
                        _ret_mul = _cur_val / _w_sol_cost
                else:
                    _ret_sol = 0
                    _ret_mul = 0
                wallet_return_multiples.append(_ret_mul)

                wallet_hold_stats[_w] = {
                    'sell_count': _w_sell_cnt,
                    'sell_sol': _w_sell_sol,
                    'has_sold': _w_sold,
                    'last_sell_time': _w_last_sell,
                    'hold_hours': _hold_h,
                    'return_sol': _ret_sol,
                    'return_multiple': _ret_mul,
                    'buy_cost': _w_sol_cost,
                }

            # --- Token characteristics ---
            first_trade_time = token_all.iloc[0]['block_time']
            token_age_h = max(
                (now_ts - first_trade_time).total_seconds() / 3600, 0
            )
            total_trades = len(token_all)
            unique_traders = token_all['wallet_address'].nunique()
            still_holding_pct = (
                still_holding_count / total_buy_wallets * 100
                if total_buy_wallets > 0 else 0
            )
            avg_hold_h = (np.mean(hold_hours_list)
                          if hold_hours_list else 0)
            avg_return_mul = (np.mean(wallet_return_multiples)
                              if wallet_return_multiples else 0)
            median_return_mul = (np.median(wallet_return_multiples)
                                 if wallet_return_multiples else 0)

            # --- Window wallets' labels ---
            window_wallets = window['wallets']
            label_summary = self._summarize_labels(window_wallets)

            # Time span within window
            span_hours = (
                (window['end'] - window['start']).total_seconds() / 3600
            )

            # Wallet display
            wallet_display = self._format_wallet_list(window_wallets)

            signals.append({
                '代币符号': token_symbol,
                '代币名称': token_name,
                '代币地址': token_address,
                '窗口内钱包数': window['count'],
                '总买入钱包数': total_buy_wallets,
                '窗口开始': window['start'],
                '窗口结束': window['end'],
                '窗口跨度(h)': round(span_hours, 1),
                '总买入(SOL)': round(total_sol_cost, 4),
                '平均买入价(SOL)': avg_buy_price,
                '最新价格(SOL)': latest_price,
                '当前收益倍数': round(current_return, 4),
                '最高收益倍数': round(max_return, 4),
                '钱包平均收益倍数': round(avg_return_mul, 4),
                '钱包中位收益倍数': round(median_return_mul, 4),
                '卖出钱包数': n_sell_wallets,
                '持仓钱包数': still_holding_count,
                '持仓比例(%)': round(still_holding_pct, 1),
                '总卖出(SOL)': round(total_sol_revenue, 4),
                '已实现PnL(SOL)': round(
                    total_sol_revenue - total_sol_cost, 4
                ),
                '平均持仓时长(h)': round(avg_hold_h, 1),
                **label_summary,
                '首笔交易时间': first_trade_time,
                'Token存续(h)': round(token_age_h, 1),
                '总交易笔数': total_trades,
                '参与地址数': unique_traders,
                '最新交易时间': latest_time,
                '窗口内钱包': wallet_display,
            })

            # --- Detail rows for each wallet ---
            for wallet in token_buys['wallet_address'].unique():
                w_buys = token_buys[token_buys['wallet_address'] == wallet]
                w_first_buy = w_buys['block_time'].min()
                w_sol_cost = abs(w_buys['sol_amount'].sum())
                w_tokens = abs(w_buys['token_amount'].sum())
                w_avg_price = w_sol_cost / w_tokens if w_tokens > 0 else 0
                in_window = wallet in window_wallets
                labels = self.wallet_labels.get(wallet, {})

                w_info = self.wallets_df[
                    self.wallets_df['address'] == wallet
                ]
                pnl_30d = (
                    float(w_info.iloc[0]['pnl_30d'])
                    if not w_info.empty else 0
                )
                win_rate = (
                    float(w_info.iloc[0]['win_rate_30d'])
                    if not w_info.empty else 0
                )

                hs = wallet_hold_stats.get(wallet, {})

                detail_rows.append({
                    '代币符号': token_symbol,
                    '代币地址': token_address,
                    '钱包地址': wallet,
                    '钱包名称': self.name_map.get(wallet, ''),
                    '首次买入时间': w_first_buy,
                    '在集中窗口内': '是' if in_window else '',
                    '买入笔数': len(w_buys),
                    '买入成本(SOL)': round(w_sol_cost, 6),
                    '买入数量': w_tokens,
                    '平均买入价(SOL)': f'{w_avg_price:.12g}',
                    '卖出笔数': hs.get('sell_count', 0),
                    '卖出收入(SOL)': round(hs.get('sell_sol', 0), 6),
                    '持仓状态': '持仓中' if not hs.get('has_sold') else '已卖出',
                    '最后卖出时间': (hs.get('last_sell_time', '')
                                  if hs.get('has_sold') else ''),
                    '持仓时长(h)': round(hs.get('hold_hours', 0), 1),
                    '盈亏(SOL)': round(hs.get('return_sol', 0), 6),
                    '收益倍数': round(hs.get('return_multiple', 0), 4),
                    '30D盈利(USD)': round(pnl_30d, 2),
                    '30D胜率(%)': round(win_rate, 1),
                    '聪明钱': '是' if labels.get('is_smart_money') else '',
                    'KOL': '是' if labels.get('is_kol') else '',
                    '巨鲸': '是' if labels.get('is_whale') else '',
                    '狙击手': '是' if labels.get('is_sniper') else '',
                    '热门追踪': '是' if labels.get('is_hot_followed') else '',
                    '热门备注': '是' if labels.get('is_hot_remarked') else '',
                })

        # --- Save signals ---
        if signals:
            sig_df = pd.DataFrame(signals)
            sig_df = sig_df.sort_values(
                ['窗口内钱包数', '当前收益倍数'], ascending=[False, False]
            ).reset_index(drop=True)
            sig_df.insert(0, '排名', range(1, len(sig_df) + 1))

            for col in ['平均买入价(SOL)', '最新价格(SOL)']:
                sig_df[col] = sig_df[col].apply(lambda x: f'{x:.12g}')

            self.results['集中买入信号'] = sig_df
            print(f"  检测到 {len(sig_df)} 个Token有集中买入信号")

            top5 = sig_df.head(5)
            for _, s in top5.iterrows():
                print(f"    {s['代币符号']}: "
                      f"{s['窗口内钱包数']}个钱包在{s['窗口跨度(h)']}h内买入，"
                      f"收益{s['当前收益倍数']}x")
        else:
            print("  无集中买入信号")

        # --- Save details ---
        if detail_rows:
            det_df = pd.DataFrame(detail_rows)
            det_df = det_df.sort_values(
                ['代币符号', '在集中窗口内', '首次买入时间'],
                ascending=[True, False, True]
            ).reset_index(drop=True)
            self.results['买入钱包明细'] = det_df
            print(f"  买入明细: {len(det_df)} 条")

    # ============================================================
    # Step 4: 钱包社区检测
    # ============================================================

    def _detect_wallet_communities(self):
        """基于集中买入共现关系，将钱包划分为社区

        算法:
          1. 从集中买入窗口中提取 钱包-Token 关系
          2. 构建钱包共现图（两钱包共同出现在同一Token窗口 → 建边，权重=共买Token数）
          3. Louvain 社区检测
          4. 输出: 钱包社区总览、社区钱包明细、社区共买Token明细
        """
        import networkx as nx

        print(f"\n[Step 4] 钱包社区检测...")

        sig_df = self.results.get('集中买入信号')
        detail_df = self.results.get('买入钱包明细')
        if sig_df is None or sig_df.empty or detail_df is None or detail_df.empty:
            print("  无集中买入数据，跳过")
            return

        in_window = detail_df[detail_df['在集中窗口内'] == '是'].copy()
        if in_window.empty:
            print("  无窗口内钱包数据，跳过")
            return

        # -- 1. 提取 钱包-Token 关系 --
        token_wallets = {}       # token_address -> set(wallet)
        wallet_tokens = {}       # wallet -> set(token_address)
        wallet_token_syms = {}   # wallet -> set(token_symbol)
        token_sym_map = {}       # token_address -> symbol

        for _, row in in_window.iterrows():
            t_addr = row['代币地址']
            t_sym = row['代币符号']
            w = row['钱包地址']
            token_wallets.setdefault(t_addr, set()).add(w)
            wallet_tokens.setdefault(w, set()).add(t_addr)
            wallet_token_syms.setdefault(w, set()).add(t_sym)
            token_sym_map[t_addr] = t_sym

        # -- 2. 构建共现图 --
        G = nx.Graph()
        for w in wallet_tokens:
            G.add_node(w)

        co_buy_map = {}  # (w1, w2) -> set(token_address), w1 < w2
        for t_addr, wallets in token_wallets.items():
            w_list = sorted(wallets)
            for i in range(len(w_list)):
                for j in range(i + 1, len(w_list)):
                    pair = (w_list[i], w_list[j])
                    co_buy_map.setdefault(pair, set()).add(t_addr)

        for (w1, w2), tokens in co_buy_map.items():
            G.add_edge(w1, w2, weight=len(tokens))

        print(f"  共现图: {G.number_of_nodes()} 个钱包, "
              f"{G.number_of_edges()} 条共买关系")

        if G.number_of_nodes() < 2:
            print("  钱包数不足，跳过")
            return

        # -- 3. Louvain 社区检测 --
        communities = nx.community.louvain_communities(
            G, weight='weight', seed=42
        )
        communities = sorted(communities, key=len, reverse=True)

        wallet_community = {}
        for idx, comm in enumerate(communities, 1):
            for w in comm:
                wallet_community[w] = idx

        n_multi = sum(1 for c in communities if len(c) >= 2)
        print(f"  检测到 {len(communities)} 个社区"
              f"（{n_multi} 个含 >=2 钱包）")
        for idx, comm in enumerate(communities[:10], 1):
            print(f"    社区 {idx}: {len(comm)} 个钱包")

        # -- 4. Sheet: 钱包社区 --
        # Per-wallet actual performance from concentrated buy detail
        iw_stats = detail_df[detail_df['在集中窗口内'] == '是'].copy()
        for _col in ['买入成本(SOL)', '卖出收入(SOL)', '盈亏(SOL)', '收益倍数']:
            if _col in iw_stats.columns:
                iw_stats[_col] = pd.to_numeric(
                    iw_stats[_col], errors='coerce'
                ).fillna(0)

        wallet_perf = {}
        for w, grp in iw_stats.groupby('钱包地址'):
            invested = grp['买入成本(SOL)'].sum()
            pnl_sol = grp['盈亏(SOL)'].sum()
            n_tokens = grp['代币地址'].nunique()
            token_ret = grp.groupby('代币地址')['收益倍数'].first()
            n_profit = int((token_ret > 1).sum())
            wallet_perf[w] = {
                'invested': invested,
                'pnl_sol': pnl_sol,
                'roi': pnl_sol / invested * 100 if invested > 0 else 0,
                'return_mul': (
                    (invested + pnl_sol) / invested
                    if invested > 0 else 0
                ),
                'n_tokens': n_tokens,
                'n_profit': n_profit,
                'n_loss': n_tokens - n_profit,
                'token_winrate': (
                    n_profit / n_tokens * 100 if n_tokens > 0 else 0
                ),
                'all_profit': n_profit == n_tokens and n_tokens > 0,
            }

        community_rows = []
        for idx, comm in enumerate(communities, 1):
            if len(comm) < 2:
                continue
            comm_wallets = sorted(comm)

            comm_tokens = set()
            for w in comm_wallets:
                comm_tokens.update(wallet_tokens.get(w, set()))

            token_counts = {}
            for w in comm_wallets:
                for t in wallet_tokens.get(w, set()):
                    token_counts[t] = token_counts.get(t, 0) + 1
            co_bought = {t: c for t, c in token_counts.items() if c >= 2}

            subgraph = G.subgraph(comm)
            density = nx.density(subgraph) if len(comm) > 1 else 0
            avg_weight = (
                np.mean([d['weight'] for _, _, d in subgraph.edges(data=True)])
                if subgraph.number_of_edges() > 0 else 0
            )

            # Community actual ROI: total SOL in vs total SOL out
            comm_invested = sum(
                wallet_perf[w]['invested']
                for w in comm_wallets if w in wallet_perf
            )
            comm_pnl = sum(
                wallet_perf[w]['pnl_sol']
                for w in comm_wallets if w in wallet_perf
            )
            comm_roi = (
                comm_pnl / comm_invested * 100
                if comm_invested > 0 else 0
            )
            comm_return_mul = (
                (comm_invested + comm_pnl) / comm_invested
                if comm_invested > 0 else 0
            )

            # Community token-level win rate
            comm_detail = iw_stats[
                iw_stats['钱包地址'].isin(comm_wallets)
            ]
            token_pnl = comm_detail.groupby('代币地址')['盈亏(SOL)'].sum()
            n_profit_tokens = int((token_pnl > 0).sum())
            n_loss_tokens = int((token_pnl <= 0).sum())
            token_win_rate = (
                n_profit_tokens / len(token_pnl) * 100
                if len(token_pnl) > 0 else 0
            )

            # Wallets where every token is profitable
            all_profit_list = [
                w for w in comm_wallets
                if wallet_perf.get(w, {}).get('all_profit', False)
            ]

            co_display = [
                f"{token_sym_map.get(t, t[:8])}({c}人)"
                for t, c in sorted(co_bought.items(), key=lambda x: -x[1])
            ]

            community_rows.append({
                '社区编号': idx,
                '钱包数量': len(comm),
                '涉及Token数': len(comm_tokens),
                '共同买入Token数': len(co_bought),
                '社区总投入(SOL)': round(comm_invested, 4),
                '社区总收益(SOL)': round(comm_pnl, 4),
                '社区收益率(%)': round(comm_roi, 2),
                '社区收益倍数': round(comm_return_mul, 4),
                '盈利Token数': n_profit_tokens,
                '亏损Token数': n_loss_tokens,
                'Token胜率(%)': round(token_win_rate, 1),
                '全盈利钱包数': len(all_profit_list),
                '图密度': round(density, 3),
                '平均共买Token数': round(avg_weight, 2),
                '共同买入Token': ', '.join(co_display[:20]),
                '全盈利钱包': ', '.join(all_profit_list),
                '社区钱包': self._format_wallet_list(
                    comm_wallets, max_show=30
                ),
            })

        if community_rows:
            self.results['钱包社区'] = pd.DataFrame(community_rows)

        # -- 5. Sheet: 社区钱包明细 --
        wallet_detail_rows = []
        for wallet in sorted(wallet_community, key=lambda w: wallet_community[w]):
            comm_id = wallet_community[wallet]
            comm = communities[comm_id - 1]
            if len(comm) < 2:
                continue

            token_syms = sorted(wallet_token_syms.get(wallet, set()))
            neighbors = list(G.neighbors(wallet))
            same_comm = [n for n in neighbors
                         if wallet_community.get(n) == comm_id]

            w_info = self.wallets_df[self.wallets_df['address'] == wallet]
            pnl = float(w_info.iloc[0]['pnl_30d']) if not w_info.empty else 0
            winrate = (float(w_info.iloc[0]['win_rate_30d'])
                       if not w_info.empty else 0)

            labels = self.wallet_labels.get(wallet, {})
            tags = []
            if labels.get('is_smart_money'):
                tags.append('聪明钱')
            if labels.get('is_kol'):
                tags.append('KOL')
            if labels.get('is_whale'):
                tags.append('巨鲸')
            if labels.get('is_sniper'):
                tags.append('狙击手')
            if labels.get('is_hot_followed'):
                tags.append('热门追踪')
            if labels.get('is_hot_remarked'):
                tags.append('热门备注')

            perf = wallet_perf.get(wallet, {})

            # 社区内共买伙伴：详细展示 钱包地址及标签、盈利情况、买入卖出情况
            partner_parts = []
            for n in same_comm:
                n_name = self.name_map.get(n, '') or ''
                n_labels = self.wallet_labels.get(n, {})
                n_tags = []
                if n_labels.get('is_smart_money'):
                    n_tags.append('聪明钱')
                if n_labels.get('is_kol'):
                    n_tags.append('KOL')
                if n_labels.get('is_whale'):
                    n_tags.append('巨鲸')
                if n_labels.get('is_sniper'):
                    n_tags.append('狙击手')
                if n_labels.get('is_hot_followed'):
                    n_tags.append('热门追踪')
                if n_labels.get('is_hot_remarked'):
                    n_tags.append('热门备注')
                n_perf = wallet_perf.get(n, {})
                pair_key = tuple(sorted([wallet, n]))
                shared_tokens = co_buy_map.get(pair_key, set())

                # 共买部分：仅统计与当前钱包共买的那几个 Token 的投入/盈亏，与下方明细一致
                co_buy_invested = 0.0
                co_buy_pnl = 0.0
                for t in shared_tokens:
                    nr = iw_stats[(iw_stats['钱包地址'] == n) & (iw_stats['代币地址'] == t)]
                    if not nr.empty:
                        r = nr.iloc[0]
                        co_buy_invested += float(r.get('买入成本(SOL)', 0) or 0)
                        co_buy_pnl += float(r.get('盈亏(SOL)', 0) or 0)
                co_buy_roi = (co_buy_pnl / co_buy_invested * 100) if co_buy_invested > 0 else 0
                co_buy_mul = ((co_buy_invested + co_buy_pnl) / co_buy_invested) if co_buy_invested > 0 else 0

                lines = [
                    f"【地址】{n}",
                    f"【名称】{n_name or '-'}",
                    f"【标签】{'|'.join(n_tags) if n_tags else '-'}",
                    ("【整体盈利(集中窗口内全部Token)】"
                     f"投入{n_perf.get('invested', 0):.4f}SOL "
                     f"收益{n_perf.get('pnl_sol', 0):.4f}SOL "
                     f"收益率{n_perf.get('roi', 0):.2f}% "
                     f"收益倍数{n_perf.get('return_mul', 0):.4f} "
                     f"Token胜率{n_perf.get('token_winrate', 0):.1f}%"),
                    ("【与当前钱包共买部分】"
                     f"投入{co_buy_invested:.4f}SOL "
                     f"盈亏{co_buy_pnl:+.4f}SOL "
                     f"收益率{co_buy_roi:.2f}% "
                     f"收益倍数{co_buy_mul:.4f}"),
                    "【共买Token买入卖出】",
                ]
                for t in sorted(shared_tokens):
                    sym = token_sym_map.get(t, t[:8])
                    nr = iw_stats[(iw_stats['钱包地址'] == n) & (iw_stats['代币地址'] == t)]
                    if not nr.empty:
                        r = nr.iloc[0]
                        buy_sol = float(r.get('买入成本(SOL)', 0) or 0)
                        sell_sol = float(r.get('卖出收入(SOL)', 0) or 0)
                        pnl_sol = float(r.get('盈亏(SOL)', 0) or 0)
                        status = r.get('持仓状态', '') or '-'
                        first_buy = r.get('首次买入时间', '')
                        last_sell = r.get('最后卖出时间', '')
                        if first_buy and hasattr(first_buy, 'strftime'):
                            first_buy = first_buy.strftime('%Y-%m-%d %H:%M')
                        else:
                            first_buy = str(first_buy) if first_buy else '-'
                        if last_sell and hasattr(last_sell, 'strftime'):
                            last_sell = last_sell.strftime('%Y-%m-%d %H:%M')
                        else:
                            last_sell = str(last_sell) if last_sell else ''
                        buy_cnt = int(r.get('买入笔数', 0) or 0)
                        sell_cnt = int(r.get('卖出笔数', 0) or 0)
                        time_part = f"首次买入 {first_buy}"
                        if last_sell:
                            time_part += f"  最后卖出 {last_sell}"
                        lines.append(
                            f"  {sym}: 买入{buy_sol:.4f}SOL({buy_cnt}笔) 卖出{sell_sol:.4f}SOL({sell_cnt}笔) "
                            f"盈亏{pnl_sol:.4f} {status}"
                        )
                        lines.append(f"      {time_part}")
                    else:
                        lines.append(f"  {sym}: (无窗口内明细)")
                partner_parts.append("\n".join(lines))

            wallet_detail_rows.append({
                '社区编号': comm_id,
                '钱包地址': wallet,
                '钱包名称': self.name_map.get(wallet, ''),
                '标签': '|'.join(tags),
                '集中买入Token数': perf.get('n_tokens', 0),
                '投入总计(SOL)': round(perf.get('invested', 0), 4),
                '收益总计(SOL)': round(perf.get('pnl_sol', 0), 4),
                '综合收益率(%)': round(perf.get('roi', 0), 2),
                '综合收益倍数': round(perf.get('return_mul', 0), 4),
                '盈利Token数': perf.get('n_profit', 0),
                '亏损Token数': perf.get('n_loss', 0),
                'Token胜率(%)': round(perf.get('token_winrate', 0), 1),
                '全盈利': '是' if perf.get('all_profit') else '',
                '参与Token': ', '.join(token_syms),
                '社区内关联数': len(same_comm),
                '总关联数': len(neighbors),
                '30D盈利(USD)': round(pnl, 2),
                '30D胜率(%)': round(winrate, 1),
                '社区内共买伙伴': '\n\n'.join(partner_parts),
            })

        if wallet_detail_rows:
            wd_df = pd.DataFrame(wallet_detail_rows)
            wd_df.sort_values(
                ['社区编号', '综合收益率(%)'],
                ascending=[True, False], inplace=True
            )
            self.results['社区钱包明细'] = wd_df

        # -- 6. Sheet: 社区共买明细 --
        co_buy_rows = []
        for idx, comm in enumerate(communities, 1):
            if len(comm) < 2:
                continue
            comm_wallets = sorted(comm)

            token_buyers = {}
            for w in comm_wallets:
                for t in wallet_tokens.get(w, set()):
                    token_buyers.setdefault(t, []).append(w)

            for t_addr, buyers in sorted(
                token_buyers.items(), key=lambda x: -len(x[1])
            ):
                if len(buyers) < 2:
                    continue

                sig_row = sig_df[sig_df['代币地址'] == t_addr]
                current_ret = (
                    float(sig_row['当前收益倍数'].iloc[0])
                    if not sig_row.empty else 0
                )
                max_ret = (
                    float(sig_row['最高收益倍数'].iloc[0])
                    if not sig_row.empty else 0
                )

                co_buy_rows.append({
                    '社区编号': idx,
                    '代币符号': token_sym_map.get(t_addr, 'UNKNOWN'),
                    '代币地址': t_addr,
                    '社区内买入钱包数': len(buyers),
                    '社区钱包总数': len(comm),
                    '社区参与率(%)': round(
                        len(buyers) / len(comm) * 100, 1
                    ),
                    '当前收益倍数': current_ret,
                    '最高收益倍数': max_ret,
                    '买入钱包': self._format_wallet_list(buyers, max_show=15),
                })

        if co_buy_rows:
            cb_df = pd.DataFrame(co_buy_rows)
            cb_df.sort_values(
                ['社区编号', '社区内买入钱包数'],
                ascending=[True, False], inplace=True
            )
            self.results['社区共买明细'] = cb_df

        # -- 7. Sheet: 社区共买亏损币明细 --
        loss_token_rows = []
        for idx, comm in enumerate(communities, 1):
            if len(comm) < 2:
                continue
            comm_wallets = sorted(comm)

            # 找出社区内共买(>=2人)的Token
            token_buyers = {}
            for w in comm_wallets:
                for t in wallet_tokens.get(w, set()):
                    token_buyers.setdefault(t, []).append(w)

            co_bought_tokens = {t: buyers for t, buyers in token_buyers.items() if len(buyers) >= 2}

            for t_addr, buyers in co_bought_tokens.items():
                # 计算该Token在这些共买钱包中的总体盈亏
                token_rows = iw_stats[(iw_stats['代币地址'] == t_addr) & (iw_stats['钱包地址'].isin(buyers))]
                if token_rows.empty:
                    continue

                total_invested = token_rows['买入成本(SOL)'].sum()
                total_pnl = token_rows['盈亏(SOL)'].sum()
                
                # 只保留总体亏损的Token
                if total_pnl >= 0:
                    continue

                sym = token_sym_map.get(t_addr, 'UNKNOWN')
                n_profit_wallets = int((token_rows['盈亏(SOL)'] > 0).sum())
                n_loss_wallets = int((token_rows['盈亏(SOL)'] <= 0).sum())
                
                sig_row = sig_df[sig_df['代币地址'] == t_addr]
                current_ret = float(sig_row['当前收益倍数'].iloc[0]) if not sig_row.empty else 0
                max_ret = float(sig_row['最高收益倍数'].iloc[0]) if not sig_row.empty else 0

                # 逐个钱包的明细
                wallet_details = []
                for _, row in token_rows.iterrows():
                    w = row['钱包地址']
                    w_name = self.name_map.get(w, '')
                    w_labels = self.wallet_labels.get(w, {})
                    tags = []
                    if w_labels.get('is_smart_money'):
                        tags.append('聪明钱')
                    if w_labels.get('is_kol'):
                        tags.append('KOL')
                    if w_labels.get('is_whale'):
                        tags.append('巨鲸')
                    if w_labels.get('is_sniper'):
                        tags.append('狙击手')
                    if w_labels.get('is_hot_followed'):
                        tags.append('热门追踪')
                    if w_labels.get('is_hot_remarked'):
                        tags.append('热门备注')
                    
                    buy_sol = float(row['买入成本(SOL)'])
                    sell_sol = float(row['卖出收入(SOL)'])
                    pnl = float(row['盈亏(SOL)'])
                    ret_mul = float(row['收益倍数'])
                    status = row['持仓状态']
                    
                    first_buy = row['首次买入时间']
                    if first_buy and hasattr(first_buy, 'strftime'):
                        first_buy_str = first_buy.strftime('%Y-%m-%d %H:%M')
                    else:
                        first_buy_str = str(first_buy) if first_buy else '-'
                    
                    last_sell = row.get('最后卖出时间', '')
                    if last_sell and hasattr(last_sell, 'strftime'):
                        last_sell_str = last_sell.strftime('%Y-%m-%d %H:%M')
                    else:
                        last_sell_str = str(last_sell) if last_sell else ''
                    
                    buy_cnt = int(row.get('买入笔数', 0))
                    sell_cnt = int(row.get('卖出笔数', 0))
                    hold_h = float(row.get('持仓时长(h)', 0))
                    
                    wallet_details.append({
                        '社区编号': idx,
                        '代币符号': sym,
                        '代币地址': t_addr,
                        '社区内买入钱包数': len(buyers),
                        '盈利钱包数': n_profit_wallets,
                        '亏损钱包数': n_loss_wallets,
                        '社区总投入(SOL)': round(total_invested, 4),
                        '社区总盈亏(SOL)': round(total_pnl, 4),
                        '当前收益倍数': round(current_ret, 4),
                        '最高收益倍数': round(max_ret, 4),
                        '钱包地址': w,
                        '钱包名称': w_name,
                        '标签': '|'.join(tags) if tags else '-',
                        '买入成本(SOL)': round(buy_sol, 6),
                        '买入笔数': buy_cnt,
                        '卖出收入(SOL)': round(sell_sol, 6),
                        '卖出笔数': sell_cnt,
                        '盈亏(SOL)': round(pnl, 6),
                        '收益倍数': round(ret_mul, 4),
                        '持仓状态': status,
                        '持仓时长(h)': round(hold_h, 1),
                        '首次买入时间': first_buy_str,
                        '最后卖出时间': last_sell_str if last_sell_str else '-',
                    })
                
                loss_token_rows.extend(wallet_details)

        if loss_token_rows:
            loss_df = pd.DataFrame(loss_token_rows)
            loss_df.sort_values(
                ['社区编号', '社区总盈亏(SOL)', '代币符号', '盈亏(SOL)'],
                ascending=[True, True, True, True],
                inplace=True
            )
            loss_df.reset_index(drop=True, inplace=True)
            self.results['社区共买亏损币明细'] = loss_df
            print(f"  社区共买亏损币明细: {len(loss_df)} 条（{loss_df['代币地址'].nunique()} 个亏损Token）")

        print(f"  社区分析完成: {len(community_rows)} 个有效社区")

        # Store for Step 5
        self._communities = communities
        self._wallet_community = wallet_community
        self._wallet_perf = wallet_perf
        self._comm_token_wallets = token_wallets
        self._comm_wallet_tokens = wallet_tokens
        self._token_sym_map = token_sym_map

    # ============================================================
    # Step 5: 社区Token详细收益分析
    # ============================================================

    def _analyze_community_token_details(self):
        """社区Token详细收益分析

        输出:
          1. 社区Token钱包收益 - 每个(社区,Token,钱包)的收益明细
             含: 共同买入标记、全盈利标记、买后价格走势、交易密度
          2. 社区共买交易记录 - 共同买入Token的逐笔买卖记录
        """
        print(f"\n[Step 5] 社区Token详细收益分析...")

        if not hasattr(self, '_communities'):
            print("  无社区数据，跳过")
            return

        communities = self._communities
        wallet_community = self._wallet_community
        wallet_perf = self._wallet_perf
        token_wallets = self._comm_token_wallets
        wallet_tokens = self._comm_wallet_tokens
        token_sym_map = self._token_sym_map

        detail_df = self.results.get('买入钱包明细')
        trades = self.trades_df
        if detail_df is None or detail_df.empty or trades is None or trades.empty:
            print("  无数据，跳过")
            return

        iw = detail_df[detail_df['在集中窗口内'] == '是'].copy()
        for _col in ['买入成本(SOL)', '卖出收入(SOL)', '盈亏(SOL)',
                      '收益倍数', '持仓时长(h)', '卖出笔数']:
            if _col in iw.columns:
                iw[_col] = pd.to_numeric(
                    iw[_col], errors='coerce'
                ).fillna(0)

        # Pre-compute per-token suffix-max price for price movement
        print("  计算Token买后价格走势...")
        token_price_cache = {}
        for t_addr, grp in trades.groupby('token_address'):
            sg = grp.sort_values('block_time')
            times = sg['block_time'].values
            prices = sg['price_sol'].values
            suffix_max = np.maximum.accumulate(prices[::-1])[::-1]
            token_price_cache[t_addr] = (times, prices, suffix_max)

        # Pre-compute trading density per token
        token_density = {}
        for t_addr, grp in trades.groupby('token_address'):
            n = len(grp)
            if n > 1:
                span_h = (
                    (grp['block_time'].max() - grp['block_time'].min())
                    .total_seconds() / 3600
                )
                token_density[t_addr] = (
                    round(n / span_h, 2) if span_h > 0 else n
                )
            else:
                token_density[t_addr] = 0

        # Per-community token buyer counts
        comm_token_counts = {}
        for idx, comm in enumerate(communities, 1):
            for w in comm:
                for t in wallet_tokens.get(w, set()):
                    key = (idx, t)
                    comm_token_counts[key] = (
                        comm_token_counts.get(key, 0) + 1
                    )

        # ---- Sheet: 社区Token钱包收益 ----
        print("  生成社区Token钱包收益...")
        tw_rows = []

        for _, row in iw.iterrows():
            wallet = row['钱包地址']
            t_addr = row['代币地址']

            comm_id = wallet_community.get(wallet)
            if comm_id is None:
                continue
            if len(communities[comm_id - 1]) < 2:
                continue

            n_buyers = comm_token_counts.get((comm_id, t_addr), 0)
            is_co = n_buyers >= 2
            is_ap = wallet_perf.get(wallet, {}).get('all_profit', False)

            buy_price_str = row.get('平均买入价(SOL)', '0')
            try:
                buy_price = float(buy_price_str)
            except (ValueError, TypeError):
                buy_price = 0

            buy_time = row['首次买入时间']
            max_price_after = 0
            current_price = 0

            cache = token_price_cache.get(t_addr)
            if cache and buy_price > 0:
                times, prices, suffix_max = cache
                buy_np = pd.Timestamp(buy_time).to_numpy()
                pos = np.searchsorted(times, buy_np)
                if pos < len(suffix_max):
                    max_price_after = float(suffix_max[pos])
                    current_price = float(prices[-1])

            max_upside = (
                (max_price_after - buy_price) / buy_price * 100
                if buy_price > 0 and max_price_after > 0 else 0
            )
            current_chg = (
                (current_price - buy_price) / buy_price * 100
                if buy_price > 0 and current_price > 0 else 0
            )

            tw_rows.append({
                '社区编号': comm_id,
                '代币符号': row['代币符号'],
                '代币地址': t_addr,
                '共同买入': '是' if is_co else '',
                '社区内买入钱包数': n_buyers,
                '钱包地址': wallet,
                '钱包名称': self.name_map.get(wallet, ''),
                '全盈利钱包': '是' if is_ap else '',
                '首次买入时间': buy_time,
                '买入成本(SOL)': row['买入成本(SOL)'],
                '买入数量': row.get('买入数量', 0),
                '卖出笔数': int(row.get('卖出笔数', 0)),
                '卖出收入(SOL)': row.get('卖出收入(SOL)', 0),
                '持仓状态': row.get('持仓状态', ''),
                '持仓时长(h)': row.get('持仓时长(h)', 0),
                '盈亏(SOL)': row.get('盈亏(SOL)', 0),
                '收益倍数': row.get('收益倍数', 0),
                '买入均价(SOL)': buy_price_str,
                '买后最高价(SOL)': (
                    f'{max_price_after:.12g}'
                    if max_price_after > 0 else ''
                ),
                '最高涨幅(%)': (
                    round(max_upside, 2)
                    if max_price_after > 0 else ''
                ),
                '当前价(SOL)': (
                    f'{current_price:.12g}'
                    if current_price > 0 else ''
                ),
                '当前涨幅(%)': (
                    round(current_chg, 2)
                    if current_price > 0 else ''
                ),
                '交易密度(笔/h)': (
                    token_density.get(t_addr, '')
                    if not is_co else ''
                ),
            })

        if tw_rows:
            tw_df = pd.DataFrame(tw_rows)
            tw_df.sort_values(
                ['社区编号', '共同买入', '社区内买入钱包数', '代币符号'],
                ascending=[True, False, False, True],
                inplace=True
            )
            tw_df.reset_index(drop=True, inplace=True)
            self.results['社区Token钱包收益'] = tw_df
            print(f"  社区Token钱包收益: {len(tw_df)} 条")

        # ---- Sheet: 社区共买交易记录 ----
        print("  生成社区共买交易记录...")
        tx_rows = []

        for idx, comm in enumerate(communities, 1):
            if len(comm) < 2:
                continue

            co_tokens = {
                t for t in set().union(
                    *(wallet_tokens.get(w, set()) for w in comm)
                )
                if comm_token_counts.get((idx, t), 0) >= 2
            }
            if not co_tokens:
                continue

            mask = (
                trades['wallet_address'].isin(comm)
                & trades['token_address'].isin(co_tokens)
            )
            ct = trades[mask].sort_values(
                ['token_address', 'wallet_address', 'block_time']
            )

            for _, tx in ct.iterrows():
                tx_rows.append({
                    '社区编号': idx,
                    '代币符号': tx['token_symbol'],
                    '代币地址': tx['token_address'],
                    '钱包地址': tx['wallet_address'],
                    '钱包名称': self.name_map.get(
                        tx['wallet_address'], ''
                    ),
                    '交易方向': (
                        '买入' if tx['side'] == 'buy' else '卖出'
                    ),
                    '交易时间': tx['block_time'],
                    'SOL金额': round(abs(tx['sol_amount']), 6),
                    'Token数量': abs(tx['token_amount']),
                    '成交价(SOL)': f"{tx['price_sol']:.12g}",
                })

        if tx_rows:
            tx_df = pd.DataFrame(tx_rows)
            self.results['社区共买交易记录'] = tx_df
            print(f"  社区共买交易记录: {len(tx_df)} 条")

        print(f"  社区Token详细分析完成")

    # ============================================================
    # Helpers
    # ============================================================

    def _summarize_labels(self, wallets):
        """统计钱包列表中各标签数量"""
        counts = {
            '聪明钱数': 0, 'KOL数': 0, '巨鲸数': 0,
            '狙击手数': 0, '热门追踪数': 0, '热门备注数': 0,
        }
        label_keys = [
            ('is_smart_money', '聪明钱数'),
            ('is_kol', 'KOL数'),
            ('is_whale', '巨鲸数'),
            ('is_sniper', '狙击手数'),
            ('is_hot_followed', '热门追踪数'),
            ('is_hot_remarked', '热门备注数'),
        ]
        for w in wallets:
            labels = self.wallet_labels.get(w, {})
            for lk, ck in label_keys:
                if labels.get(lk):
                    counts[ck] += 1
        return counts

    def _format_wallet_list(self, wallets, max_show=20):
        """格式化钱包列表显示（地址+名称+标签）"""
        display = []
        for w in wallets[:max_show]:
            wname = self.name_map.get(w)
            labels = self.wallet_labels.get(w, {})
            tags = []
            if labels.get('is_smart_money'):
                tags.append('SM')
            if labels.get('is_kol'):
                tags.append('KOL')
            if labels.get('is_whale'):
                tags.append('鲸')
            if labels.get('is_sniper'):
                tags.append('狙')
            if labels.get('is_hot_followed'):
                tags.append('热追')
            if labels.get('is_hot_remarked'):
                tags.append('热备')
            tag_str = f"[{'|'.join(tags)}]" if tags else ''

            if wname:
                display.append(f"{w[:6]}..({wname}){tag_str}")
            else:
                display.append(f"{w[:8]}..{tag_str}")

        if len(wallets) > max_show:
            display.append(f"...等共{len(wallets)}个")
        return ', '.join(display)

    # ============================================================
    # Report
    # ============================================================

    def _save_report(self):
        """保存Excel报表"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'potential_coins_report_{timestamp}.xlsx'

        print(f"\n{'=' * 60}")
        print(f"保存报表: {filename}")
        print(f"{'=' * 60}")

        # 仅输出以下 6 个 sheet，其余已注释
        sheet_order = [
            '钱包社区',
            '社区钱包明细',
            '社区共买明细',
            '社区共买亏损币明细',
            '社区Token钱包收益',
            '社区共买交易记录',
            # '集中买入信号',
            # '买入钱包明细',
            # '盈利钱包列表',
        ]

        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            sheet_count = 0
            for name in sheet_order:
                df = self.results.get(name)
                if df is not None and not df.empty:
                    sname = name[:31]
                    df.to_excel(writer, sheet_name=sname, index=False)
                    print(f"  [{sname}] {len(df)} 行")
                    sheet_count += 1

        print(f"\n文件已保存: {os.path.abspath(filename)}")
        print(f"共 {sheet_count} 个工作表")
        return filename

    # ============================================================
    # Main
    # ============================================================

    def run(self):
        """执行分析"""
        print("\n" + "=" * 60)
        print("潜力币筛选 - 盈利钱包集中买入分析")
        print(f"筛选条件: 30D盈利钱包（pnl_30d > 0，非高频）")
        print(f"集中买入: >= {self.min_wallets} 个钱包在 "
              f"{self.buy_window_hours}h 窗口内首次买入同一Token")
        print(f"计价单位: SOL")
        print("=" * 60)

        self._load_profitable_wallets()

        if self.wallets_df is None or self.wallets_df.empty:
            print("\n无30D盈利钱包，退出")
            return

        self._load_transactions()

        if self.trades_df is None or self.trades_df.empty:
            print("\n无交易数据，退出")
            return

        self._detect_concentrated_buying()
        self._detect_wallet_communities()
        self._analyze_community_token_details()
        self._save_report()

        print("\n分析完成!")


if __name__ == '__main__':
    analyzer = PotentialCoinAnalyzer(
        min_wallets=3,
        buy_window_hours=1,
    )
    analyzer.run()
