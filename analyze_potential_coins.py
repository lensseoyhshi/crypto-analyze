#!/usr/bin/env python3
"""
潜力币筛选 - 聪明钱集中买入信号分析

基于 birdeye_wallet_transactions 交易数据，识别多个钱包集中买入同一Token的模式，
计算买入后的收益表现，对钱包进行分组和可信度分析。

分析维度: 1D, 7D, 30D
计价单位: SOL
数据来源: 完全依赖交易记录

输出 Excel Sheet:
  1. 交易信号         - 综合置信度+持仓周期建议的最终信号
  2. 潜力币置信度     - 每个Token的社区加权置信度得分
  3. 潜力币排行(1D)  - 近24h被集中买入的Token，按收益倍数排序
  4. 潜力币排行(7D)  - 近7天被集中买入的Token
  5. 潜力币排行(30D) - 近30天被集中买入的Token
  6. 集中买入明细     - 每个信号Token的买入钱包、时间、金额详情
  7. 钱包评分明细     - 每个钱包的综合评分(收益/频率/胜率/集中度/平台/可疑)
  8. 钱包画像分组     - 按交易频次、币种偏好、盈利能力分组
  9. 社区质量评估     - 每个图社区的质量分、钱包分布、等级
  10. 社区买卖行为    - 社区买卖时间特征、持仓周期、行为分类
  11. 钱包关联图谱    - 共买图指标(PageRank/社区/聚类)
  12. 可信度分析      - 标记可疑钱包（同步交易、刷量、只买不卖）
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sqlalchemy import text
from config.database import get_session

# ============================================================
# Constants
# ============================================================

SOL_TOKENS = {'SOL', 'Wrapped SOL', 'WSOL'}
STABLECOINS = {'USDC', 'USDT', 'USD Coin'}
QUOTE_TOKENS = SOL_TOKENS | STABLECOINS

SOL_TOKEN_ADDRESSES = {
    'So11111111111111111111111111111111111111112',  # Wrapped SOL
    'So11111111111111111111111111111111111111111',  # Native SOL
}

DEFAULT_SOL_PRICE_USD = 200


# ============================================================
# Union-Find for sync trading group detection
# ============================================================

class UnionFind:
    """并查集 - 用于同步交易钱包分组"""

    def __init__(self):
        self.parent = {}
        self.rank = {}

    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1

    def get_groups(self):
        """获取所有连通分量（成员数>=2）"""
        groups = defaultdict(set)
        for x in self.parent:
            groups[self.find(x)].add(x)
        return [g for g in groups.values() if len(g) > 1]


# ============================================================
# Main Analyzer
# ============================================================

class PotentialCoinAnalyzer:
    """
    潜力币筛选分析器

    核心算法:
      1. 加载所有 buy/sell 交易记录（30D 覆盖 1D/7D/30D 三个窗口）
      2. 解析 balance_change，提取币种、SOL金额、隐含价格(SOL/Token)
      3. 检测可疑钱包（先于排行分析，用于可信度标记）
      4. 检测集中买入信号（>= N 个不同钱包在时间窗口内买入同一Token）
      5. 计算每个 Token 被集中买入后的收益倍数（最新价 / 平均买入价）
      6. 对钱包按交易频次、多样性、盈利能力分组
      7. 输出 Excel 多 Sheet 报表
    """

    def __init__(self, min_wallets=2, sol_price_usd=DEFAULT_SOL_PRICE_USD):
        """
        Args:
            min_wallets: 集中买入最低钱包数阈值（默认2，可调）
            sol_price_usd: SOL参考价格（仅用于稳定币→SOL折算）
        """
        self.min_wallets = min_wallets
        self.sol_price_usd = sol_price_usd

        # Data containers
        self.wallets_df = None
        self.trades_df = None
        self.name_map = {}                 # address -> name
        self.wallet_labels = {}            # address -> {is_smart_money, is_kol, ...}
        self.suspicious_wallets = set()    # 可疑钱包地址集合
        self.suspicious_types = {}         # wallet -> '只买不卖'/'疑似刷量'/'同步交易'
        self.hf_wallets = set()            # 高频钱包（Step3后过滤）
        self.wallet_community = {}         # wallet -> community_id (图社区)
        self.wallet_scores = {}            # wallet -> score (0-100)
        self.community_quality = {}        # community_id -> quality dict
        self.results = {}                  # sheet_name -> DataFrame

    # ============================================================
    # 1. Data Loading
    # ============================================================

    def _load_wallets(self):
        """加载钱包元数据（smart_wallets表）"""
        print("\n[Step 1] 加载钱包信息...")
        session = get_session()
        try:
            sql = text("""
                SELECT address, name,
                       is_smart_money, is_kol, is_whale, is_sniper,
                       is_hot_followed, is_hot_remarked,
                       is_high_frequency,
                       uses_trojan, uses_bullx, uses_photon, uses_axiom, uses_bot,
                       pnl_1d, pnl_7d, pnl_30d,
                       win_rate_1d, win_rate_7d, win_rate_30d,
                       tx_count_1d, tx_count_7d, tx_count_30d,
                       avg_hold_time_30d
                FROM smart_wallets
            """)
            result = session.execute(sql)
            columns = list(result.keys())
            rows = result.fetchall()
            self.wallets_df = pd.DataFrame(rows, columns=columns)

            # Numeric conversion
            for col in ['pnl_1d', 'pnl_7d', 'pnl_30d',
                        'win_rate_1d', 'win_rate_7d', 'win_rate_30d']:
                if col in self.wallets_df.columns:
                    self.wallets_df[col] = pd.to_numeric(
                        self.wallets_df[col], errors='coerce'
                    ).fillna(0)

            for col in ['tx_count_1d', 'tx_count_7d', 'tx_count_30d',
                        'avg_hold_time_30d']:
                if col in self.wallets_df.columns:
                    self.wallets_df[col] = pd.to_numeric(
                        self.wallets_df[col], errors='coerce'
                    ).fillna(0).astype(int)

            # is_high_frequency 转数值
            if 'is_high_frequency' in self.wallets_df.columns:
                self.wallets_df['is_high_frequency'] = pd.to_numeric(
                    self.wallets_df['is_high_frequency'], errors='coerce'
                ).fillna(0).astype(int)

            # Build lookup maps
            self.hf_wallets = set()  # 高频钱包地址集合
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
                if int(row.get('is_high_frequency', 0) or 0):
                    self.hf_wallets.add(addr)

            n_hf = len(self.hf_wallets)
            print(f"  加载 {len(self.wallets_df)} 个钱包"
                  f"（其中高频 {n_hf} 个，后续分析将过滤）")
        except Exception as e:
            print(f"  加载钱包失败: {e}")
            self.wallets_df = pd.DataFrame()
        finally:
            session.close()

    def _parse_balance_change(self, bc_str):
        """
        解析 balance_change JSON

        从 balance_change 中提取:
          - SOL 等值金额（买入为负，卖出为正）
          - 目标 Token 信息（符号、名称、地址、数量）
          - 隐含价格 = abs(SOL等值) / abs(Token数量)

        Returns:
            dict 或 None（解析失败时）
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

        for item in bc:
            symbol = item.get('symbol', '')
            name = item.get('name', '')
            raw_amount = item.get('amount', 0)
            decimals = item.get('decimals', 0)
            address = item.get('address', '')

            # Convert to human-readable amount
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
                # Keep the token with largest absolute amount as target
                if token_info is None or abs(amount) > abs(token_info['amount']):
                    token_info = {
                        'symbol': symbol or name or 'UNKNOWN',
                        'name': name,
                        'address': address,
                        'amount': amount,
                    }

        if token_info is None:
            return None

        # Unified SOL equivalent (stablecoins converted to SOL)
        sol_equivalent = sol_total + stable_total / self.sol_price_usd

        # Skip token-to-token swaps (SOL change is negligible, only gas)
        if abs(sol_equivalent) < 0.001:
            return None

        # Implicit price: SOL per token
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
        """加载30D内所有 buy/sell 交易并解析 balance_change"""
        print("\n[Step 2] 加载交易数据（30D）...")

        session = get_session()
        cutoff = datetime.now() - timedelta(days=30)
        cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:%S')

        try:
            sql = text("""
                SELECT `from`, block_time, block_time_unix, side, balance_change
                FROM birdeye_wallet_transactions
                WHERE side IN ('buy', 'sell')
                  AND block_time >= :cutoff
                ORDER BY block_time ASC
            """)

            result = session.execute(sql, {'cutoff': cutoff_str})
            rows = result.fetchall()
            print(f"  查询到 {len(rows)} 条原始 buy/sell 交易")

            trades = []
            skipped = 0

            for i, row in enumerate(rows):
                # row: (from, block_time, block_time_unix, side, balance_change)
                parsed = self._parse_balance_change(row[4])
                if parsed is None:
                    skipped += 1
                    continue

                if parsed['price_sol'] <= 0:
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

                if (i + 1) % 50000 == 0:
                    print(f"    已解析 {i + 1}/{len(rows)}，有效 {len(trades)}")

            if trades:
                self.trades_df = pd.DataFrame(trades)
                self.trades_df['block_time'] = pd.to_datetime(
                    self.trades_df['block_time']
                )
                self.trades_df['block_time_unix'] = pd.to_numeric(
                    self.trades_df['block_time_unix'], errors='coerce'
                ).fillna(0).astype(np.int64)

                print(f"  共 {len(self.trades_df)} 条有效交易（跳过 {skipped} 条）")
                print(f"  涉及 {self.trades_df['wallet_address'].nunique()} 个钱包、"
                      f"{self.trades_df['token_address'].nunique()} 个Token")
            else:
                self.trades_df = pd.DataFrame()
                print("  无有效交易数据")

        except Exception as e:
            print(f"  加载交易失败: {e}")
            import traceback
            traceback.print_exc()
            self.trades_df = pd.DataFrame()
        finally:
            session.close()

    # ============================================================
    # 2. Credibility Analysis (先于排行分析运行)
    # ============================================================

    def _detect_suspicious_wallets(self):
        """
        可信度分析 - 检测三类可疑钱包:

        (a) 只买不卖: 30D内只有买入无卖出，>=3笔（疑似项目方）
        (b) 疑似刷量: 高频交易(>=50笔)但收益率<=5%
        (c) 同步交易: 多钱包在5分钟窗口内买入相同Token（>=3次，关联地址/机器人组）
             使用并查集将同步钱包聚合为关联组
        """
        print("\n[Step 3] 可信度分析...")

        if self.trades_df is None or self.trades_df.empty:
            return

        suspicious_records = []
        buys_all = self.trades_df[self.trades_df['side'] == 'buy']
        sells_all = self.trades_df[self.trades_df['side'] == 'sell']

        # ----------------------------------------------------------
        # (a) 只买不卖
        # ----------------------------------------------------------
        print("  [3a] 检测只买不卖钱包...")
        wallet_sides = self.trades_df.groupby('wallet_address')['side'].apply(set)

        buy_only_wallets = set()
        for wallet, sides in wallet_sides.items():
            if sides == {'buy'}:
                buy_only_wallets.add(wallet)
                w_buys = buys_all[buys_all['wallet_address'] == wallet]
                n_buys = len(w_buys)
                n_tokens = w_buys['token_address'].nunique()

                if n_buys >= 3:
                    self.suspicious_wallets.add(wallet)
                    self.suspicious_types[wallet] = '只买不卖(疑似项目方)'
                    severity = '高' if n_buys >= 10 else '中'
                    suspicious_records.append({
                        '钱包地址': wallet,
                        '钱包名称': self.name_map.get(wallet, ''),
                        '可疑类型': '只买不卖',
                        '可疑原因': '30D内只有买入无卖出，疑似项目方自买拉盘',
                        '严重程度': severity,
                        '严重程度说明': '高=>=10笔买入; 中=3~9笔买入',
                        '说明': f'30D内{n_buys}笔买入、0笔卖出，涉及{n_tokens}个Token',
                        '交易笔数': n_buys,
                        '关联组ID': '',
                    })

        n_buy_only = len([r for r in suspicious_records
                          if r['可疑类型'] == '只买不卖'])
        print(f"    只买不卖(>=3笔): {n_buy_only} 个")

        # ----------------------------------------------------------
        # (b) 疑似刷量
        # ----------------------------------------------------------
        print("  [3b] 检测疑似刷量...")
        wallet_trade_counts = (
            self.trades_df.groupby('wallet_address')['side']
            .count()
            .reset_index(name='n_trades')
        )
        # Only check wallets with >= 50 trades
        high_freq_wallets = wallet_trade_counts[
            wallet_trade_counts['n_trades'] >= 50
        ]['wallet_address'].tolist()

        wash_count = 0
        for wallet in high_freq_wallets:
            if wallet in self.suspicious_wallets:
                continue

            w_buys = buys_all[buys_all['wallet_address'] == wallet]
            w_sells = sells_all[sells_all['wallet_address'] == wallet]

            total_cost = abs(w_buys['sol_amount'].sum()) if not w_buys.empty else 0
            total_revenue = w_sells['sol_amount'].sum() if not w_sells.empty else 0

            if total_cost <= 0:
                continue

            pnl_ratio = (total_revenue - total_cost) / total_cost
            n_trades = len(self.trades_df[
                self.trades_df['wallet_address'] == wallet
            ])

            if pnl_ratio <= 0.05:
                self.suspicious_wallets.add(wallet)
                self.suspicious_types[wallet] = '疑似刷量(高频低收益)'
                wash_count += 1
                suspicious_records.append({
                    '钱包地址': wallet,
                    '钱包名称': self.name_map.get(wallet, ''),
                    '可疑类型': '疑似刷量',
                    '可疑原因': '高频交易但收益极低，疑似制造虚假交易量',
                    '严重程度': '高' if n_trades >= 200 else '中',
                    '严重程度说明': '高=>=200笔交易; 中=50~199笔交易',
                    '说明': f'{n_trades}笔交易，收益率仅{pnl_ratio * 100:.1f}%',
                    '交易笔数': n_trades,
                    '关联组ID': '',
                })

        print(f"    疑似刷量(>=50笔, 收益<=5%): {wash_count} 个")

        # ----------------------------------------------------------
        # (c) 同步交易 (5分钟窗口 + 并查集分组)
        # ----------------------------------------------------------
        print("  [3c] 检测同步交易钱包组...")

        # 构建5分钟时间桶
        buys_with_time = buys_all[buys_all['block_time_unix'] > 0].copy()
        buys_with_time = buys_with_time.assign(
            time_bucket=buys_with_time['block_time_unix'] // 300
        )

        # 每个 (token, bucket) 内的唯一钱包列表
        bucket_wallets = (
            buys_with_time
            .groupby(['token_address', 'time_bucket'])['wallet_address']
            .apply(lambda x: list(set(x)))
        )

        # 统计同步买入对的出现次数
        sync_pairs = Counter()
        for wallets in bucket_wallets:
            if len(wallets) < 2 or len(wallets) > 50:
                # 跳过超大桶（热门币大量钱包同时买入是正常的）
                continue
            wallets_sorted = sorted(wallets)
            for i in range(len(wallets_sorted)):
                for j in range(i + 1, len(wallets_sorted)):
                    sync_pairs[(wallets_sorted[i], wallets_sorted[j])] += 1

        # 用并查集合并同步次数 >= 3 的钱包对
        uf = UnionFind()
        for (w1, w2), count in sync_pairs.items():
            if count >= 3:
                uf.union(w1, w2)

        # 获取关联组
        sync_groups = uf.get_groups()

        # 为每个组内钱包分配组ID
        wallet_group_id = {}
        for gid, group in enumerate(sync_groups, 1):
            for wallet in group:
                wallet_group_id[wallet] = f'同步组{gid}'
                self.suspicious_wallets.add(wallet)

        # 写入可疑记录（同步伙伴显示完整地址）
        for wallet, group_id in wallet_group_id.items():
            # 查找该钱包的同步伙伴（完整地址+同步次数）
            partners = []
            for (w1, w2), cnt in sync_pairs.items():
                if cnt >= 3:
                    if w1 == wallet:
                        partners.append(f'{w2}({cnt}次)')
                    elif w2 == wallet:
                        partners.append(f'{w1}({cnt}次)')

            n_trades = len(self.trades_df[
                self.trades_df['wallet_address'] == wallet
            ])

            # Track suspicious type
            if wallet not in self.suspicious_types:
                self.suspicious_types[wallet] = '同步交易(关联地址组)'

            suspicious_records.append({
                '钱包地址': wallet,
                '钱包名称': self.name_map.get(wallet, ''),
                '可疑类型': '同步交易',
                '可疑原因': '与其他钱包在5分钟内买入相同Token>=3次，'
                           '疑似同一人/团队控制的关联地址',
                '严重程度': '高' if len(partners) >= 3 else '中',
                '严重程度说明': '高=同步伙伴>=3个; 中=1~2个',
                '说明': f'同步伙伴: {"; ".join(partners[:10])}'
                        + (f' 等共{len(partners)}个'
                           if len(partners) > 10 else ''),
                '交易笔数': n_trades,
                '关联组ID': group_id,
                '关联组说明': f'同一{group_id}内的钱包互相有同步买入行为，'
                            f'可能由同一人/团队控制',
            })

        print(f"    同步交易钱包: {len(wallet_group_id)} 个，"
              f"分为 {len(sync_groups)} 个关联组")

        # ----------------------------------------------------------
        # 保存结果
        # ----------------------------------------------------------
        if suspicious_records:
            susp_df = pd.DataFrame(suspicious_records)
            susp_df = susp_df.sort_values(
                ['可疑类型', '严重程度', '交易笔数'],
                ascending=[True, True, False]
            ).reset_index(drop=True)
            self.results['可信度分析'] = susp_df

        print(f"\n  可疑钱包汇总: {len(self.suspicious_wallets)} 个")

    # ============================================================
    # 3. Concentrated Buying Detection
    # ============================================================

    def _detect_concentrated_buying(self):
        """
        检测集中买入信号

        对每个时间窗口 (1D/7D/30D):
          1. 筛选窗口内的 buy 交易
          2. 按 token_address 聚合，统计买入钱包数
          3. 过滤: 买入钱包数 >= min_wallets
          4. 计算:
             - 加权平均买入价 (VWAP) = 总SOL成本 / 总Token数量
             - 最新价格 = 窗口内最近一笔交易的隐含价格
             - 当前收益倍数 = 最新价格 / 平均买入价
             - 最高收益倍数 = 最高价格 / 平均买入价
          5. 按当前收益倍数降序排列
        """
        print("\n[Step 4] 检测集中买入信号...")

        if self.trades_df is None or self.trades_df.empty:
            return

        now = datetime.now()
        windows = {
            # '1D': now - timedelta(days=1),
            # '7D': now - timedelta(days=7),
            '30D': now - timedelta(days=30),
        }

        for window_name, cutoff_time in windows.items():
            print(f"\n  --- {window_name} 窗口 ---")

            window_trades = self.trades_df[
                self.trades_df['block_time'] >= cutoff_time
            ]

            if window_trades.empty:
                print(f"    无交易数据")
                continue

            buys = window_trades[window_trades['side'] == 'buy']
            sells = window_trades[window_trades['side'] == 'sell']

            rankings = []

            for token_address, token_buys in buys.groupby('token_address'):
                buy_wallets = token_buys['wallet_address'].unique()
                n_buy_wallets = len(buy_wallets)

                if n_buy_wallets < self.min_wallets:
                    continue

                token_symbol = token_buys.iloc[0]['token_symbol']
                token_name = token_buys.iloc[0]['token_name']

                # --- Buy metrics ---
                total_sol_cost = abs(token_buys['sol_amount'].sum())
                total_tokens_bought = abs(token_buys['token_amount'].sum())
                avg_buy_price = (
                    total_sol_cost / total_tokens_bought
                    if total_tokens_bought > 0 else 0
                )

                buy_count = len(token_buys)
                first_buy_time = token_buys['block_time'].min()
                last_buy_time = token_buys['block_time'].max()

                # --- Price metrics (from all trades in window) ---
                token_all = window_trades[
                    window_trades['token_address'] == token_address
                ].sort_values('block_time')

                latest_price = token_all.iloc[-1]['price_sol']
                latest_trade_time = token_all.iloc[-1]['block_time']
                max_price = token_all['price_sol'].max()

                # --- Return metrics ---
                current_return = (
                    latest_price / avg_buy_price if avg_buy_price > 0 else 0
                )
                max_return = (
                    max_price / avg_buy_price if avg_buy_price > 0 else 0
                )

                # --- Sell metrics ---
                token_sells = sells[sells['token_address'] == token_address]
                n_sell_wallets = (
                    token_sells['wallet_address'].nunique()
                    if not token_sells.empty else 0
                )
                total_sol_revenue = (
                    token_sells['sol_amount'].sum()
                    if not token_sells.empty else 0
                )
                total_tokens_sold = (
                    abs(token_sells['token_amount'].sum())
                    if not token_sells.empty else 0
                )

                sell_ratio = (
                    total_tokens_sold / total_tokens_bought * 100
                    if total_tokens_bought > 0 else 0
                )

                # PnL
                realized_pnl = total_sol_revenue - total_sol_cost

                # --- Buy time concentration (std dev in hours) ---
                if len(token_buys) > 1:
                    timestamps = token_buys['block_time_unix'].values.astype(
                        np.float64
                    )
                    time_std_hours = np.std(timestamps) / 3600
                else:
                    time_std_hours = 0

                # --- Wallet quality ---
                credible_wallets = [
                    w for w in buy_wallets
                    if w not in self.suspicious_wallets
                ]
                n_credible = len(credible_wallets)
                credible_ratio = n_credible / n_buy_wallets * 100

                smart_count = sum(
                    1 for w in buy_wallets
                    if self.wallet_labels.get(w, {}).get('is_smart_money')
                )
                kol_count = sum(
                    1 for w in buy_wallets
                    if self.wallet_labels.get(w, {}).get('is_kol')
                )
                whale_count = sum(
                    1 for w in buy_wallets
                    if self.wallet_labels.get(w, {}).get('is_whale')
                )
                hot_followed_count = sum(
                    1 for w in buy_wallets
                    if self.wallet_labels.get(w, {}).get('is_hot_followed')
                )
                hot_remarked_count = sum(
                    1 for w in buy_wallets
                    if self.wallet_labels.get(w, {}).get('is_hot_remarked')
                )
                sniper_count = sum(
                    1 for w in buy_wallets
                    if self.wallet_labels.get(w, {}).get('is_sniper')
                )

                # --- Wallet list (display up to 15, with labels) ---
                wallet_display = []
                for w in list(buy_wallets)[:15]:
                    wname = self.name_map.get(w)
                    wlabels = self.wallet_labels.get(w, {})
                    # Build label tags
                    tags = []
                    if wlabels.get('is_smart_money'):
                        tags.append('SM')
                    if wlabels.get('is_kol'):
                        tags.append('KOL')
                    if wlabels.get('is_whale'):
                        tags.append('鲸')
                    if wlabels.get('is_sniper'):
                        tags.append('狙')
                    if wlabels.get('is_hot_followed'):
                        tags.append('热追')
                    if wlabels.get('is_hot_remarked'):
                        tags.append('热备')
                    tag_str = f"[{'|'.join(tags)}]" if tags else ''
                    if wname:
                        wallet_display.append(
                            f"{w[:6]}..({wname}){tag_str}"
                        )
                    else:
                        wallet_display.append(f"{w[:8]}..{tag_str}")

                rankings.append({
                    '代币符号': token_symbol,
                    '代币名称': token_name,
                    '代币地址': token_address,
                    '买入钱包数': n_buy_wallets,
                    '可信钱包数': n_credible,
                    '可信比例(%)': round(credible_ratio, 1),
                    '买入笔数': buy_count,
                    '总买入(SOL)': round(total_sol_cost, 4),
                    '平均买入价(SOL)': avg_buy_price,
                    '最新价格(SOL)': latest_price,
                    '当前收益倍数': round(current_return, 4),
                    '最高价格(SOL)': max_price,
                    '最高收益倍数': round(max_return, 4),
                    '卖出钱包数': n_sell_wallets,
                    '卖出比例(%)': round(min(sell_ratio, 100), 1),
                    '总卖出(SOL)': round(total_sol_revenue, 4),
                    '已实现PnL(SOL)': round(realized_pnl, 4),
                    '聪明钱数': smart_count,
                    'KOL数': kol_count,
                    '巨鲸数': whale_count,
                    '热门追踪数': hot_followed_count,
                    '热门备注数': hot_remarked_count,
                    '狙击手数': sniper_count,
                    '首次买入': first_buy_time,
                    '最后买入': last_buy_time,
                    '最新交易': latest_trade_time,
                    '买入时间离散度(h)': round(time_std_hours, 2),
                    '买入钱包列表': ', '.join(wallet_display),
                })

            if rankings:
                df = pd.DataFrame(rankings)
                # Sort by current return multiplier descending
                df = df.sort_values(
                    '当前收益倍数', ascending=False
                ).reset_index(drop=True)
                df.insert(0, '排名', range(1, len(df) + 1))

                # Format tiny price values to avoid scientific notation
                for col in ['平均买入价(SOL)', '最新价格(SOL)', '最高价格(SOL)']:
                    df[col] = df[col].apply(lambda x: f'{x:.12g}')

                self.results[f'潜力币排行({window_name})'] = df
                print(f"    {len(df)} 个Token有集中买入信号")

                if len(df) > 0:
                    top = df.iloc[0]
                    print(f"    最高收益: {top['代币符号']} "
                          f"当前{top['当前收益倍数']}x "
                          f"({top['买入钱包数']}个钱包)")
            else:
                print(f"    无集中买入信号")

    # ============================================================
    # 4. Concentrated Buying Details
    # ============================================================

    def _analyze_buying_details(self):
        """
        集中买入明细

        展示所有信号 Token 的具体买入交易记录:
          钱包信息、买入时间、金额、价格、钱包标签、可疑标记
        """
        print("\n[Step 5] 生成集中买入明细...")

        if self.trades_df is None or self.trades_df.empty:
            return

        # Collect all ranked token addresses from all windows
        target_tokens = set()
        for key in self.results:
            if key.startswith('潜力币排行'):
                df = self.results[key]
                if '代币地址' in df.columns:
                    target_tokens.update(df['代币地址'].tolist())

        if not target_tokens:
            print("  无集中买入Token")
            return

        # All buy trades for target tokens
        buys = self.trades_df[
            (self.trades_df['token_address'].isin(target_tokens))
            & (self.trades_df['side'] == 'buy')
        ].sort_values(['token_symbol', 'block_time'])

        if buys.empty:
            return

        details = []
        for _, row in buys.iterrows():
            wallet = row['wallet_address']
            labels = self.wallet_labels.get(wallet, {})
            is_suspicious = wallet in self.suspicious_wallets

            details.append({
                '代币符号': row['token_symbol'],
                '代币地址': row['token_address'],
                '钱包地址': wallet,
                '钱包名称': self.name_map.get(wallet, ''),
                '买入时间': row['block_time'],
                '买入金额(SOL)': round(abs(row['sol_amount']), 6),
                '买入数量': abs(row['token_amount']),
                '买入价格(SOL)': f"{row['price_sol']:.12g}",
                '聪明钱': '是' if labels.get('is_smart_money') else '',
                'KOL': '是' if labels.get('is_kol') else '',
                '巨鲸': '是' if labels.get('is_whale') else '',
                '狙击手': '是' if labels.get('is_sniper') else '',
                '热门追踪': '是' if labels.get('is_hot_followed') else '',
                '热门备注': '是' if labels.get('is_hot_remarked') else '',
                '可疑': self.suspicious_types.get(wallet, ''),
            })

        if details:
            details_df = pd.DataFrame(details)
            self.results['集中买入明细'] = details_df
            print(f"  集中买入明细: {len(details_df)} 条记录，"
                  f"涉及 {details_df['代币地址'].nunique()} 个Token")

    # ============================================================
    # 5. Wallet Grouping
    # ============================================================

    def _analyze_wallet_groups(self):
        """
        钱包画像分组

        按以下维度对每个活跃钱包生成画像:
          - 交易统计: 总交易数、买入/卖出次数、买入币种数
          - 盈利指标: 总花费、总收入、PnL、收益率、交易胜率
          - 频率指标: 日均交易频次
          - 分组标签: 频率分组、多样性分组、盈利分组
          - 身份标签: 聪明钱/KOL/巨鲸/狙击手/可疑
        """
        print("\n[Step 6] 钱包画像分组...")

        if self.trades_df is None or self.trades_df.empty:
            return

        buys_all = self.trades_df[self.trades_df['side'] == 'buy']
        sells_all = self.trades_df[self.trades_df['side'] == 'sell']

        features = []

        for wallet_addr, wallet_trades in self.trades_df.groupby('wallet_address'):
            w_buys = wallet_trades[wallet_trades['side'] == 'buy']
            w_sells = wallet_trades[wallet_trades['side'] == 'sell']

            n_trades = len(wallet_trades)
            n_buys = len(w_buys)
            n_sells = len(w_sells)
            n_tokens_bought = (
                w_buys['token_address'].nunique() if not w_buys.empty else 0
            )

            # --- SOL metrics ---
            total_cost = (
                abs(w_buys['sol_amount'].sum()) if not w_buys.empty else 0
            )
            total_revenue = (
                w_sells['sol_amount'].sum() if not w_sells.empty else 0
            )
            pnl_sol = total_revenue - total_cost
            pnl_pct = pnl_sol / total_cost * 100 if total_cost > 0 else 0

            # --- Per-token win rate ---
            profitable = 0
            total_closed = 0
            if not w_buys.empty:
                for token_addr in w_buys['token_address'].unique():
                    t_cost = abs(
                        w_buys[w_buys['token_address'] == token_addr]
                        ['sol_amount'].sum()
                    )
                    if not w_sells.empty:
                        t_sells = w_sells[
                            w_sells['token_address'] == token_addr
                        ]
                        if not t_sells.empty:
                            t_rev = t_sells['sol_amount'].sum()
                            total_closed += 1
                            if t_rev > t_cost:
                                profitable += 1

            win_rate = (
                profitable / total_closed * 100 if total_closed > 0 else 0
            )

            # --- Trading frequency ---
            time_span_days = max(
                (wallet_trades['block_time'].max()
                 - wallet_trades['block_time'].min()).total_seconds() / 86400,
                1
            )
            freq_per_day = n_trades / time_span_days

            # --- Buy-only ratio ---
            buy_only_tokens = set(
                w_buys['token_address'].unique() if not w_buys.empty else []
            )
            if not w_sells.empty:
                buy_only_tokens -= set(w_sells['token_address'].unique())
            buy_only_ratio = (
                len(buy_only_tokens) / n_tokens_bought * 100
                if n_tokens_bought > 0 else 0
            )

            # --- Grouping ---
            if freq_per_day > 20:
                freq_group = '高频(>20/天)'
            elif freq_per_day > 5:
                freq_group = '中频(5-20/天)'
            else:
                freq_group = '低频(<5/天)'

            if n_tokens_bought > 20:
                div_group = '广撒网(>20币种)'
            elif n_tokens_bought > 5:
                div_group = '适中(5-20币种)'
            else:
                div_group = '集中(<5币种)'

            if pnl_pct > 100:
                profit_group = '高收益(>100%)'
            elif pnl_pct > 0:
                profit_group = '盈利(0-100%)'
            elif pnl_pct > -50:
                profit_group = '小亏(-50%~0)'
            else:
                profit_group = '大亏(<-50%)'

            # --- Labels ---
            labels = self.wallet_labels.get(wallet_addr, {})
            is_suspicious = wallet_addr in self.suspicious_wallets

            features.append({
                '钱包地址': wallet_addr,
                '钱包名称': self.name_map.get(wallet_addr, ''),
                '总交易数': n_trades,
                '买入次数': n_buys,
                '卖出次数': n_sells,
                '买入币种数': n_tokens_bought,
                '只买未卖比例(%)': round(buy_only_ratio, 1),
                '总花费(SOL)': round(total_cost, 4),
                '总收入(SOL)': round(total_revenue, 4),
                'PnL(SOL)': round(pnl_sol, 4),
                '收益率(%)': round(pnl_pct, 2),
                '交易胜率(%)': round(win_rate, 1),
                '日均频次': round(freq_per_day, 1),
                '频率分组': freq_group,
                '多样性分组': div_group,
                '盈利分组': profit_group,
                '聪明钱': '是' if labels.get('is_smart_money') else '',
                'KOL': '是' if labels.get('is_kol') else '',
                '巨鲸': '是' if labels.get('is_whale') else '',
                '狙击手': '是' if labels.get('is_sniper') else '',
                '热门追踪': '是' if labels.get('is_hot_followed') else '',
                '热门备注': '是' if labels.get('is_hot_remarked') else '',
                '可疑': self.suspicious_types.get(wallet_addr, ''),
            })

        if features:
            wallet_df = pd.DataFrame(features)
            wallet_df = wallet_df.sort_values(
                'PnL(SOL)', ascending=False
            ).reset_index(drop=True)
            self.results['钱包画像分组'] = wallet_df

            print(f"  钱包画像: {len(wallet_df)} 个活跃钱包")
            for group_col in ['频率分组', '盈利分组']:
                counts = wallet_df[group_col].value_counts()
                for g, c in counts.items():
                    print(f"    {g}: {c}")

    # ============================================================
    # 6. Wallet Scoring (钱包评分)
    # ============================================================

    def _score_wallets(self):
        """
        钱包综合评分

        评分维度 (总分 0-100):
          - 收益分(35%): PnL收益率，盈利越高分越高
          - 频率分(25%): 日均频次，低频高分、高频低分
          - 胜率分(15%): 交易胜率
          - 集中度分(10%): 币种集中度适中为佳
          - 平台分(10%): 聪明钱/KOL等身份加分
          - 可疑惩罚(5%): 被标记可疑则扣分

        目的: 明确区分高频负收益钱包 vs 低频高收益钱包
        """
        print("\n[Step 7] 钱包综合评分...")

        if self.trades_df is None or self.trades_df.empty:
            return

        score_records = []

        for wallet_addr, wallet_trades in self.trades_df.groupby(
            'wallet_address'
        ):
            w_buys = wallet_trades[wallet_trades['side'] == 'buy']
            w_sells = wallet_trades[wallet_trades['side'] == 'sell']

            n_trades = len(wallet_trades)
            n_tokens_bought = (
                w_buys['token_address'].nunique()
                if not w_buys.empty else 0
            )
            total_cost = (
                abs(w_buys['sol_amount'].sum())
                if not w_buys.empty else 0
            )
            total_revenue = (
                w_sells['sol_amount'].sum()
                if not w_sells.empty else 0
            )
            pnl_pct = (
                (total_revenue - total_cost) / total_cost * 100
                if total_cost > 0 else 0
            )

            time_span_days = max(
                (wallet_trades['block_time'].max()
                 - wallet_trades['block_time'].min()
                 ).total_seconds() / 86400, 1
            )
            freq_per_day = n_trades / time_span_days

            profitable = 0
            total_closed = 0
            if not w_buys.empty:
                for token_addr in w_buys['token_address'].unique():
                    t_cost = abs(
                        w_buys[w_buys['token_address'] == token_addr]
                        ['sol_amount'].sum()
                    )
                    if not w_sells.empty:
                        t_sells = w_sells[
                            w_sells['token_address'] == token_addr
                        ]
                        if not t_sells.empty:
                            total_closed += 1
                            if t_sells['sol_amount'].sum() > t_cost:
                                profitable += 1

            win_rate = (
                profitable / total_closed * 100
                if total_closed > 0 else 0
            )
            concentration = (
                n_trades / n_tokens_bought
                if n_tokens_bought > 0 else 0
            )

            # --- 各维度评分 (0-100) ---

            # 收益分 (35%): 盈利越高分越高，亏损明确低分
            if pnl_pct >= 200:
                profit_score = 100
            elif pnl_pct >= 100:
                profit_score = 80
            elif pnl_pct >= 50:
                profit_score = 65
            elif pnl_pct >= 0:
                profit_score = 40 + pnl_pct * 0.5
            elif pnl_pct >= -50:
                profit_score = 20 + (pnl_pct + 50) * 0.4
            else:
                profit_score = max(0, 20 + pnl_pct * 0.2)

            # 频率分 (25%): 低频高分, 高频低分
            if freq_per_day <= 3:
                freq_score = 100
            elif freq_per_day <= 5:
                freq_score = 80
            elif freq_per_day <= 10:
                freq_score = 60
            elif freq_per_day <= 20:
                freq_score = 30
            else:
                freq_score = max(0, 30 - (freq_per_day - 20) * 1.5)

            # 胜率分 (15%)
            if total_closed == 0:
                wr_score = 30
            elif win_rate >= 70:
                wr_score = 100
            elif win_rate >= 50:
                wr_score = 60 + (win_rate - 50) * 2
            elif win_rate >= 30:
                wr_score = 30 + (win_rate - 30) * 1.5
            else:
                wr_score = max(0, win_rate)

            # 集中度分 (10%): 适中为佳
            if 2 <= concentration <= 8:
                conc_score = 80
            elif 1 <= concentration < 2 or 8 < concentration <= 15:
                conc_score = 50
            else:
                conc_score = 20

            # 平台/身份分 (10%)
            labels = self.wallet_labels.get(wallet_addr, {})
            platform_score = 30
            if labels.get('is_smart_money'):
                platform_score += 30
            if labels.get('is_kol'):
                platform_score += 20
            if labels.get('is_whale'):
                platform_score += 10
            if labels.get('is_hot_followed'):
                platform_score += 10
            platform_score = min(100, platform_score)

            # 可疑惩罚 (5%)
            if wallet_addr in self.suspicious_wallets:
                sus_type = self.suspicious_types.get(wallet_addr, '')
                if '刷量' in sus_type:
                    suspicious_score = 0
                elif '同步' in sus_type:
                    suspicious_score = 20
                elif '只买不卖' in sus_type:
                    suspicious_score = 30
                else:
                    suspicious_score = 10
            else:
                suspicious_score = 100

            # --- 加权综合分 ---
            total_score = (
                profit_score * 0.35
                + freq_score * 0.25
                + wr_score * 0.15
                + conc_score * 0.10
                + platform_score * 0.10
                + suspicious_score * 0.05
            )
            total_score = round(max(0, min(100, total_score)), 2)

            self.wallet_scores[wallet_addr] = total_score

            score_records.append({
                '钱包地址': wallet_addr,
                '钱包名称': self.name_map.get(wallet_addr, ''),
                '综合评分': total_score,
                '收益分(35%)': round(profit_score, 1),
                '频率分(25%)': round(freq_score, 1),
                '胜率分(15%)': round(wr_score, 1),
                '集中度分(10%)': round(conc_score, 1),
                '平台分(10%)': round(platform_score, 1),
                '可疑分(5%)': round(suspicious_score, 1),
                '收益率(%)': round(pnl_pct, 2),
                '日均频次': round(freq_per_day, 1),
                '交易胜率(%)': round(win_rate, 1),
                '交易集中度': round(concentration, 1),
                '总交易数': n_trades,
                '买入币种数': n_tokens_bought,
                'PnL(SOL)': round(total_revenue - total_cost, 4),
                '频率分组': (
                    '高频(>20/天)' if freq_per_day > 20
                    else '中频(5-20/天)' if freq_per_day > 5
                    else '低频(<5/天)'
                ),
                '可疑标记': self.suspicious_types.get(wallet_addr, ''),
            })

        if score_records:
            score_df = pd.DataFrame(score_records)
            score_df = score_df.sort_values(
                '综合评分', ascending=False
            ).reset_index(drop=True)
            self.results['钱包评分明细'] = score_df

            high = len(score_df[score_df['综合评分'] >= 70])
            mid = len(score_df[
                (score_df['综合评分'] >= 40)
                & (score_df['综合评分'] < 70)
            ])
            low = len(score_df[score_df['综合评分'] < 40])
            print(f"  钱包评分完成: {len(score_df)} 个钱包")
            print(f"    高分(>=70): {high}  "
                  f"中分(40-70): {mid}  "
                  f"低分(<40): {low}")
            print(f"    平均分: {score_df['综合评分'].mean():.1f}  "
                  f"中位数: {score_df['综合评分'].median():.1f}")

    # ============================================================
    # 7. Graph Analysis (钱包关联图谱)
    # ============================================================

    def _analyze_wallet_graph(self):
        """
        钱包关联图谱分析 (Graph-based)

        构建钱包共买图（Wallet Co-buying Graph）:
          - 节点: 所有买入过 Token 的钱包
          - 边: 两个钱包买过相同 Token → 连边
          - 边权重: 共买 Token 数量（越多越相关）

        图算法:
          - 社区检测 (Louvain):  发现钱包社群（交易行为相似的钱包聚为一组）
          - PageRank:            衡量钱包在共买网络中的影响力/核心程度
          - 度中心性:            钱包与多少个其他钱包有共买关系
          - 聚类系数:            钱包的邻居之间是否也互相关联（越高=越抱团）

        输出:
          - 钱包关联图谱 Sheet: 每个钱包的图指标
          - 为潜力币排行增加"买入社区数"列（独立社区越多，信号越可靠）
        """
        print("\n[Step 8] 钱包关联图谱分析（图算法）...")

        try:
            import networkx as nx
        except ImportError:
            print("  跳过图分析（需安装: pip install networkx）")
            self.wallet_community = {}
            return

        if self.trades_df is None or self.trades_df.empty:
            self.wallet_community = {}
            return

        buys = self.trades_df[self.trades_df['side'] == 'buy']

        # ----------------------------------------------------------
        # 1. 构建钱包共买图
        # ----------------------------------------------------------
        print("  [8a] 构建钱包共买图（时间加权）...")
        G = nx.Graph()
        all_buy_wallets = buys['wallet_address'].unique()
        G.add_nodes_from(all_buy_wallets)

        # 每个 Token 的买入钱包列表 + 时间集中度
        # 跳过买入钱包数 > 50 的热门 Token（太多人买，连边无意义）
        edge_tokens = defaultdict(set)
        edge_time_scores = defaultdict(float)

        for token_addr, token_buys in buys.groupby('token_address'):
            buy_wallets_list = sorted(
                token_buys['wallet_address'].unique()
            )
            if len(buy_wallets_list) < 2 or len(buy_wallets_list) > 50:
                continue

            wallet_buy_time = {}
            for w in buy_wallets_list:
                w_tb = token_buys[token_buys['wallet_address'] == w]
                wallet_buy_time[w] = w_tb['block_time'].min()

            for i in range(len(buy_wallets_list)):
                for j in range(i + 1, len(buy_wallets_list)):
                    w1, w2 = buy_wallets_list[i], buy_wallets_list[j]
                    pair = (w1, w2)
                    edge_tokens[pair].add(token_addr)

                    t1, t2 = wallet_buy_time[w1], wallet_buy_time[w2]
                    hours_diff = abs(
                        (t1 - t2).total_seconds()
                    ) / 3600
                    time_factor = 1 / (1 + hours_diff / 48)
                    edge_time_scores[pair] += time_factor

        # 添加边: 权重 = 共买Token数(0.5) + 时间集中度(0.5)
        for (w1, w2), tokens in edge_tokens.items():
            co_buy_count = len(tokens)
            time_score = edge_time_scores.get((w1, w2), 0)
            weight = co_buy_count * 0.5 + time_score * 0.5
            G.add_edge(
                w1, w2,
                weight=weight,
                co_buy_count=co_buy_count,
                time_score=round(time_score, 4),
            )

        n_nodes = G.number_of_nodes()
        n_edges = G.number_of_edges()
        print(f"  共买图: {n_nodes} 个钱包节点, {n_edges} 条边")

        if n_edges == 0:
            print("  图无边，跳过图分析")
            self.wallet_community = {}
            return

        # ----------------------------------------------------------
        # 2. 社区检测 (Louvain)
        # ----------------------------------------------------------
        print("  [8b] 社区检测 (Louvain)...")
        communities = nx.community.louvain_communities(
            G, weight='weight', seed=42
        )
        self.wallet_community = {}
        community_sizes = {}
        for cid, community in enumerate(communities, 1):
            community_sizes[cid] = len(community)
            for wallet in community:
                self.wallet_community[wallet] = cid

        # 统计社区大小分布
        size_counts = Counter(community_sizes.values())
        print(f"  检测到 {len(communities)} 个社区")
        for size, cnt in sorted(size_counts.items(), reverse=True):
            if cnt <= 3:
                print(f"    {size}人社区: {cnt}个")

        # ----------------------------------------------------------
        # 3. PageRank
        # ----------------------------------------------------------
        print("  [8c] 计算 PageRank...")
        pagerank = nx.pagerank(G, weight='weight', alpha=0.85)

        # ----------------------------------------------------------
        # 4. 度中心性 + 聚类系数
        # ----------------------------------------------------------
        print("  [8d] 计算度中心性 & 聚类系数...")
        weighted_degree = dict(G.degree(weight='weight'))
        simple_degree = dict(G.degree())
        clustering = nx.clustering(G, weight='weight')

        # ----------------------------------------------------------
        # 5. 输出: 钱包关联图谱 Sheet
        # ----------------------------------------------------------
        rows = []
        for wallet in all_buy_wallets:
            cid = self.wallet_community.get(wallet, 0)
            labels = self.wallet_labels.get(wallet, {})

            # Top 5 共买伙伴（按共买Token数排序，显示完整地址）
            neighbors_info = []
            if wallet in G and simple_degree.get(wallet, 0) > 0:
                sorted_neighbors = sorted(
                    G.neighbors(wallet),
                    key=lambda n: G[wallet][n]['weight'],
                    reverse=True
                )
                for neighbor in sorted_neighbors[:5]:
                    co = G[wallet][neighbor].get('co_buy_count',
                                                  int(G[wallet][neighbor]['weight']))
                    ts = G[wallet][neighbor].get('time_score', 0)
                    neighbors_info.append(
                        f"{neighbor}({co}币,时间{ts:.2f})"
                    )

            rows.append({
                '钱包地址': wallet,
                '钱包名称': self.name_map.get(wallet, ''),
                '关联钱包数': simple_degree.get(wallet, 0),
                '加权关联度': weighted_degree.get(wallet, 0),
                'PageRank': round(pagerank.get(wallet, 0), 8),
                '聚类系数': round(clustering.get(wallet, 0), 4),
                '所属社区': f'社区{cid}' if cid > 0 else '孤立节点',
                '社区钱包数': community_sizes.get(cid, 1),
                'Top5共买伙伴': '; '.join(neighbors_info),
                '聪明钱': '是' if labels.get('is_smart_money') else '',
                'KOL': '是' if labels.get('is_kol') else '',
                '巨鲸': '是' if labels.get('is_whale') else '',
                '热门追踪': '是' if labels.get('is_hot_followed') else '',
                '热门备注': '是' if labels.get('is_hot_remarked') else '',
                '可疑': self.suspicious_types.get(wallet, ''),
            })

        if rows:
            graph_df = pd.DataFrame(rows)
            graph_df = graph_df.sort_values(
                'PageRank', ascending=False
            ).reset_index(drop=True)
            self.results['钱包关联图谱'] = graph_df
            print(f"\n  钱包关联图谱: {len(graph_df)} 个钱包")

            # Show top 5 by PageRank
            print("  PageRank Top5:")
            for idx, r in graph_df.head(5).iterrows():
                print(f"    PR={r['PageRank']:.8f}  "
                      f"关联={r['关联钱包数']}  "
                      f"{r['所属社区']}  "
                      f"{r['钱包地址'][:10]}.. "
                      f"{r['钱包名称']}")

        # ----------------------------------------------------------
        # 6. 增强潜力币排行: 添加"买入社区数"列
        # ----------------------------------------------------------
        self._enhance_rankings_with_communities(buys)

    def _enhance_rankings_with_communities(self, buys):
        """
        为潜力币排行增加"买入社区数"列

        含义: 买入该 Token 的钱包来自多少个不同的图社区。
              社区数越多 → 多个独立群体都在买 → 信号越可靠
              社区数=1   → 所有买入钱包来自同一群体 → 可能是协调操作
        """
        if not self.wallet_community:
            return

        for key in list(self.results.keys()):
            if not key.startswith('潜力币排行'):
                continue

            df = self.results[key]
            if '代币地址' not in df.columns:
                continue

            community_counts = []
            community_details = []
            for _, row in df.iterrows():
                token_addr = row['代币地址']
                token_buys = buys[buys['token_address'] == token_addr]
                buy_wallets_arr = token_buys['wallet_address'].unique()

                # Count distinct communities
                communities_set = set()
                for w in buy_wallets_arr:
                    cid = self.wallet_community.get(w, 0)
                    if cid > 0:
                        communities_set.add(cid)

                community_counts.append(len(communities_set))
                # Detail: community ID list
                if communities_set:
                    detail = ', '.join(
                        [f'社区{c}' for c in sorted(communities_set)]
                    )
                else:
                    detail = '无社区归属'
                community_details.append(detail)

            # Insert columns after '买入钱包数'
            if '买入钱包数' in df.columns:
                col_idx = df.columns.get_loc('买入钱包数') + 1
                df.insert(col_idx, '买入社区数', community_counts)
                df.insert(col_idx + 1, '社区分布', community_details)
            else:
                df['买入社区数'] = community_counts
                df['社区分布'] = community_details

            self.results[key] = df

        print("  已为潜力币排行添加「买入社区数」和「社区分布」列")

    # ============================================================
    # 8. Community Quality Assessment (社区质量评估)
    # ============================================================

    def _analyze_community_quality(self):
        """
        社区质量评估

        对每个图社区:
          1. 统计社区内钱包评分分布(均值/中位数/高分占比)
          2. 剔除高频负收益钱包后的净质量分
          3. 分析社区内钱包的频率类型分布
          4. 社区质量等级: A(优质)/B(一般)/C(低质)
        """
        print("\n[Step 9] 社区质量评估...")

        if not self.wallet_community or not self.wallet_scores:
            print("  需要先完成图社区检测和钱包评分")
            return

        community_wallets = defaultdict(list)
        for wallet, cid in self.wallet_community.items():
            community_wallets[cid].append(wallet)

        wallet_profile = self.results.get('钱包画像分组')
        quality_records = []

        for cid, wallets in community_wallets.items():
            n_wallets = len(wallets)
            if n_wallets < 2:
                continue

            scores = [self.wallet_scores.get(w, 0) for w in wallets]
            avg_score = np.mean(scores)
            median_score = np.median(scores)
            high_ratio = (
                sum(1 for s in scores if s >= 70) / n_wallets * 100
            )
            low_ratio = (
                sum(1 for s in scores if s < 40) / n_wallets * 100
            )

            low_freq = mid_freq = high_freq = 0
            if wallet_profile is not None:
                for w in wallets:
                    w_row = wallet_profile[
                        wallet_profile['钱包地址'] == w
                    ]
                    if not w_row.empty:
                        fg = str(w_row.iloc[0].get('频率分组', ''))
                        if '高频' in fg:
                            high_freq += 1
                        elif '中频' in fg:
                            mid_freq += 1
                        else:
                            low_freq += 1

            quality_wallets = [
                w for w in wallets
                if self.wallet_scores.get(w, 0) >= 30
            ]
            quality_scores = [
                self.wallet_scores.get(w, 0) for w in quality_wallets
            ]
            net_quality = (
                np.mean(quality_scores) if quality_scores else 0
            )

            suspicious_count = sum(
                1 for w in wallets if w in self.suspicious_wallets
            )

            if net_quality >= 65 and high_ratio >= 30:
                grade = 'A(优质)'
            elif net_quality >= 45:
                grade = 'B(一般)'
            else:
                grade = 'C(低质)'

            self.community_quality[cid] = {
                'quality_score': net_quality,
                'grade': grade,
                'n_wallets': n_wallets,
                'n_quality_wallets': len(quality_wallets),
            }

            quality_records.append({
                '社区ID': f'社区{cid}',
                '钱包数': n_wallets,
                '平均钱包分': round(avg_score, 1),
                '中位钱包分': round(median_score, 1),
                '高分钱包占比(%)': round(high_ratio, 1),
                '低分钱包占比(%)': round(low_ratio, 1),
                '低频钱包数': low_freq,
                '中频钱包数': mid_freq,
                '高频钱包数': high_freq,
                '可疑钱包数': suspicious_count,
                '净质量钱包数': len(quality_wallets),
                '净质量分': round(net_quality, 1),
                '质量等级': grade,
            })

        if quality_records:
            quality_df = pd.DataFrame(quality_records)
            quality_df = quality_df.sort_values(
                '净质量分', ascending=False
            ).reset_index(drop=True)
            self.results['社区质量评估'] = quality_df

            grade_counts = quality_df['质量等级'].value_counts()
            print(f"  {len(quality_df)} 个社区完成质量评估")
            for g, c in grade_counts.items():
                print(f"    {g}: {c} 个社区")

    # ============================================================
    # 9. Community Behavior Analysis (社区买卖行为分析)
    # ============================================================

    def _analyze_community_behavior(self):
        """
        社区买卖行为分析

        对每个社区交易过的每个币种（>=2钱包买入）:
          1. 买入时间跨度与离散度
          2. 卖出时间集中度
          3. 持仓周期
          4. 起涨延迟: 社区首次买入→价格最高点
          5. 社区内钱包收益分布
          6. 行为分类: 快进快出/波段/中长线
        """
        print("\n[Step 10] 社区买卖行为分析...")

        if not self.wallet_community or self.trades_df is None:
            return

        buys = self.trades_df[self.trades_df['side'] == 'buy']
        sells = self.trades_df[self.trades_df['side'] == 'sell']

        community_wallets = defaultdict(set)
        for wallet, cid in self.wallet_community.items():
            community_wallets[cid].add(wallet)

        behavior_records = []

        for cid, wallets in community_wallets.items():
            if len(wallets) < 2:
                continue

            community_buys = buys[buys['wallet_address'].isin(wallets)]
            community_sells = sells[sells['wallet_address'].isin(wallets)]

            for token_addr, token_buys in community_buys.groupby(
                'token_address'
            ):
                buy_wallets = set(token_buys['wallet_address'].unique())
                if len(buy_wallets) < 2:
                    continue

                token_symbol = token_buys.iloc[0]['token_symbol']

                first_buy = token_buys['block_time'].min()
                last_buy = token_buys['block_time'].max()
                buy_span_h = (
                    (last_buy - first_buy).total_seconds() / 3600
                )

                wallet_first_buys = token_buys.groupby(
                    'wallet_address'
                )['block_time'].min()
                buy_std_h = (
                    wallet_first_buys.apply(
                        lambda x: x.timestamp()
                    ).std() / 3600
                    if len(wallet_first_buys) > 1 else 0
                )

                token_sells = community_sells[
                    community_sells['token_address'] == token_addr
                ]
                sell_wallets = set(
                    token_sells['wallet_address'].unique()
                ) if not token_sells.empty else set()

                if not token_sells.empty:
                    wallet_last_sells = token_sells.groupby(
                        'wallet_address'
                    )['block_time'].max()
                    sell_std_h = (
                        wallet_last_sells.apply(
                            lambda x: x.timestamp()
                        ).std() / 3600
                        if len(wallet_last_sells) > 1 else 0
                    )

                    # 每个卖出钱包的持仓时长 = 最后卖出 - 首次买入
                    per_wallet_hold = []
                    for w in sell_wallets:
                        w_first_buy = wallet_first_buys.get(w)
                        w_last_sell = wallet_last_sells.get(w)
                        if w_first_buy is not None and w_last_sell is not None:
                            h = (w_last_sell - w_first_buy
                                 ).total_seconds() / 3600
                            per_wallet_hold.append(h)
                    hold_h = (
                        np.median(per_wallet_hold)
                        if per_wallet_hold else None
                    )
                else:
                    hold_h = None
                    sell_std_h = None

                wallet_pnls = []
                for w in buy_wallets:
                    w_cost = abs(
                        token_buys[
                            token_buys['wallet_address'] == w
                        ]['sol_amount'].sum()
                    )
                    w_rev = 0
                    if not token_sells.empty:
                        w_s = token_sells[
                            token_sells['wallet_address'] == w
                        ]
                        if not w_s.empty:
                            w_rev = w_s['sol_amount'].sum()
                    if w_cost > 0:
                        wallet_pnls.append(
                            (w_rev - w_cost) / w_cost * 100
                        )

                avg_pnl = np.mean(wallet_pnls) if wallet_pnls else 0
                pnl_std = (
                    np.std(wallet_pnls)
                    if len(wallet_pnls) > 1 else 0
                )

                if hold_h is not None:
                    if hold_h < 24:
                        behavior_type = '快进快出(<24h)'
                    elif hold_h < 168:
                        behavior_type = '波段(1-7天)'
                    else:
                        behavior_type = '中长线(>7天)'
                else:
                    behavior_type = '未卖出'

                all_token_trades = self.trades_df[
                    self.trades_df['token_address'] == token_addr
                ]
                max_price = all_token_trades['price_sol'].max()
                total_token_amt = abs(token_buys['token_amount'].sum())
                avg_buy_price = (
                    abs(token_buys['sol_amount'].sum()) / total_token_amt
                    if total_token_amt > 0 else 0
                )
                max_return = (
                    max_price / avg_buy_price if avg_buy_price > 0 else 0
                )

                rise_delay_h = None
                if avg_buy_price > 0 and not all_token_trades.empty:
                    max_row = all_token_trades.loc[
                        all_token_trades['price_sol'].idxmax()
                    ]
                    rise_delay_h = (
                        (max_row['block_time'] - first_buy
                         ).total_seconds() / 3600
                    )

                behavior_records.append({
                    '社区ID': f'社区{cid}',
                    '社区质量': self.community_quality.get(
                        cid, {}
                    ).get('grade', '未评'),
                    '代币符号': token_symbol,
                    '代币地址': token_addr,
                    '买入钱包数': len(buy_wallets),
                    '卖出钱包数': len(sell_wallets),
                    '首次买入': first_buy,
                    '买入时间跨度(h)': round(buy_span_h, 1),
                    '买入时间离散度(h)': round(buy_std_h, 1),
                    '持仓周期(h)': (
                        round(hold_h, 1) if hold_h is not None
                        else None
                    ),
                    '卖出时间离散度(h)': (
                        round(sell_std_h, 1) if sell_std_h is not None
                        else None
                    ),
                    '起涨延迟(h)': (
                        round(rise_delay_h, 1)
                        if rise_delay_h is not None else None
                    ),
                    '最高收益倍数': round(max_return, 2),
                    '平均收益率(%)': round(avg_pnl, 1),
                    '收益率标准差(%)': round(pnl_std, 1),
                    '行为类型': behavior_type,
                })

        if behavior_records:
            behavior_df = pd.DataFrame(behavior_records)
            behavior_df = behavior_df.sort_values(
                ['社区ID', '买入钱包数'], ascending=[True, False]
            ).reset_index(drop=True)
            self.results['社区买卖行为'] = behavior_df

            type_counts = behavior_df['行为类型'].value_counts()
            print(f"  社区买卖行为: {len(behavior_df)} 条记录")
            for t, c in type_counts.items():
                print(f"    {t}: {c}")

    # ============================================================
    # 10. Confidence Calculation (置信度计算)
    # ============================================================

    def _calculate_confidence(self):
        """
        置信度计算

        对每个被集中买入的 Token:
          置信度 = Σ(社区k贡献)
          社区k贡献 = 社区质量分 × 买入比例 × 钱包加权分

          买入比例 = 社区k中买入该币的钱包数 / 社区k总钱包数
          钱包加权分 = 买入钱包的平均评分 / 100

        同时计算卖出信号:
          监控社区内已卖出钱包占比
        """
        print("\n[Step 11] 置信度计算...")

        if self.trades_df is None or self.trades_df.empty:
            return
        if not self.wallet_community or not self.wallet_scores:
            print("  需要先完成社区检测和钱包评分")
            return

        buys = self.trades_df[self.trades_df['side'] == 'buy']
        sells = self.trades_df[self.trades_df['side'] == 'sell']

        community_wallets = defaultdict(set)
        for wallet, cid in self.wallet_community.items():
            community_wallets[cid].add(wallet)

        token_buy_wallets = buys.groupby(
            'token_address'
        )['wallet_address'].apply(set)
        candidate_tokens = {
            t: ws for t, ws in token_buy_wallets.items()
            if len(ws) >= self.min_wallets
        }

        if not candidate_tokens:
            print("  无候选Token")
            return

        confidence_records = []

        for token_addr, all_buy_ws in candidate_tokens.items():
            token_buys = buys[buys['token_address'] == token_addr]
            token_symbol = token_buys.iloc[0]['token_symbol']
            token_name = token_buys.iloc[0]['token_name']

            total_sol_cost = abs(token_buys['sol_amount'].sum())
            n_buy_wallets = len(all_buy_ws)

            community_contribs = []
            total_confidence = 0
            n_communities = 0

            for cid, cwallets in community_wallets.items():
                if len(cwallets) < 2:
                    continue

                buying_ws = all_buy_ws & cwallets
                if not buying_ws:
                    continue

                n_communities += 1

                buy_ratio = len(buying_ws) / len(cwallets)

                buying_scores = [
                    self.wallet_scores.get(w, 0) for w in buying_ws
                ]
                avg_score_norm = np.mean(buying_scores) / 100

                cq = self.community_quality.get(cid, {})
                cq_norm = cq.get('quality_score', 30) / 100

                contrib = cq_norm * buy_ratio * avg_score_norm * 100
                total_confidence += contrib

                community_contribs.append({
                    'cid': cid,
                    'buy_ratio': buy_ratio,
                    'n_buying': len(buying_ws),
                    'n_total': len(cwallets),
                    'avg_score': np.mean(buying_scores),
                    'quality': cq.get('quality_score', 30),
                    'contribution': contrib,
                })

            orphan_buyers = all_buy_ws - set(
                self.wallet_community.keys()
            )
            if orphan_buyers:
                orphan_scores = [
                    self.wallet_scores.get(w, 0) for w in orphan_buyers
                ]
                orphan_contrib = (
                    np.mean(orphan_scores) / 100
                    * len(orphan_buyers) / max(n_buy_wallets, 1)
                    * 30
                )
                total_confidence += orphan_contrib

            token_sells = sells[
                sells['token_address'] == token_addr
            ]
            sell_ws = set(
                token_sells['wallet_address'].unique()
            ) if not token_sells.empty else set()
            sell_ratio = (
                len(sell_ws) / n_buy_wallets * 100
                if n_buy_wallets > 0 else 0
            )

            selling_communities = 0
            for cid, cwallets in community_wallets.items():
                if sell_ws & cwallets:
                    selling_communities += 1

            all_token_trades = self.trades_df[
                self.trades_df['token_address'] == token_addr
            ].sort_values('block_time')
            total_token_amt = abs(token_buys['token_amount'].sum())
            avg_buy_price = (
                total_sol_cost / total_token_amt
                if total_token_amt > 0 else 0
            )

            # 最新价格 = 该Token在数据中最后一笔交易的隐含价格
            if not all_token_trades.empty:
                latest_price = all_token_trades.iloc[-1]['price_sol']
                latest_trade_time = all_token_trades.iloc[-1]['block_time']
            else:
                latest_price = 0
                latest_trade_time = None

            current_return = (
                latest_price / avg_buy_price
                if avg_buy_price > 0 else 0
            )

            # 已实现收益: 用实际卖出收入 vs 买入成本
            total_sell_revenue = (
                token_sells['sol_amount'].sum()
                if not token_sells.empty else 0
            )
            realized_pnl = total_sell_revenue - total_sol_cost

            if total_confidence >= 50:
                signal = '强买入'
            elif total_confidence >= 25:
                signal = '中买入'
            elif total_confidence >= 10:
                signal = '弱买入'
            else:
                signal = '观望'

            if sell_ratio >= 60:
                sell_signal = '强卖出'
            elif sell_ratio >= 30:
                sell_signal = '部分卖出'
            else:
                sell_signal = '持有'

            contrib_strs = []
            for cc in sorted(
                community_contribs,
                key=lambda x: x['contribution'],
                reverse=True
            )[:5]:
                contrib_strs.append(
                    f"社区{cc['cid']}"
                    f"({cc['n_buying']}/{cc['n_total']},"
                    f"质量{cc['quality']:.0f},"
                    f"贡献{cc['contribution']:.1f})"
                )

            confidence_records.append({
                '代币符号': token_symbol,
                '代币名称': token_name,
                '代币地址': token_addr,
                '置信度': round(total_confidence, 2),
                '买入信号': signal,
                '买入钱包数': n_buy_wallets,
                '参与社区数': n_communities,
                '当前收益倍数(末笔价)': round(current_return, 4),
                '末笔交易时间': latest_trade_time,
                '已实现PnL(SOL)': round(realized_pnl, 4),
                '卖出钱包比例(%)': round(sell_ratio, 1),
                '卖出社区数': selling_communities,
                '卖出信号': sell_signal,
                '总买入(SOL)': round(total_sol_cost, 4),
                '社区贡献明细': '; '.join(contrib_strs),
            })

        if confidence_records:
            conf_df = pd.DataFrame(confidence_records)
            conf_df = conf_df.sort_values(
                '置信度', ascending=False
            ).reset_index(drop=True)
            conf_df.insert(0, '排名', range(1, len(conf_df) + 1))
            self.results['潜力币置信度'] = conf_df

            strong = len(conf_df[conf_df['买入信号'] == '强买入'])
            medium = len(conf_df[conf_df['买入信号'] == '中买入'])
            weak = len(conf_df[conf_df['买入信号'] == '弱买入'])
            print(f"  置信度计算完成: {len(conf_df)} 个Token")
            print(f"    强买入: {strong}  中买入: {medium}  "
                  f"弱买入: {weak}")

            if strong > 0:
                top = conf_df[conf_df['买入信号'] == '强买入'].iloc[0]
                print(f"    最高置信度: {top['代币符号']} "
                      f"置信度={top['置信度']} "
                      f"({top['买入钱包数']}钱包, "
                      f"{top['参与社区数']}社区)")

    # ============================================================
    # 11. Signal Generation (交易信号生成)
    # ============================================================

    def _generate_signals(self):
        """
        生成交易信号

        综合置信度和社区行为分析:
          - 买入信号: 置信度 + 建议持仓周期
          - 卖出信号: 社区卖出比例 + 持仓时间参考
        """
        print("\n[Step 12] 生成交易信号...")

        conf_df = self.results.get('潜力币置信度')
        behavior_df = self.results.get('社区买卖行为')

        if conf_df is None or conf_df.empty:
            print("  无置信度数据")
            return

        signal_records = []

        for _, row in conf_df.iterrows():
            if row['买入信号'] == '观望':
                continue

            token_addr = row['代币地址']

            avg_hold = None
            avg_rise_delay = None
            dominant_behavior = None

            if behavior_df is not None and not behavior_df.empty:
                token_beh = behavior_df[
                    behavior_df['代币地址'] == token_addr
                ]
                if not token_beh.empty:
                    hold_vals = token_beh['持仓周期(h)'].dropna()
                    if not hold_vals.empty:
                        avg_hold = hold_vals.mean()

                    rise_vals = token_beh['起涨延迟(h)'].dropna()
                    if not rise_vals.empty:
                        avg_rise_delay = rise_vals.mean()

                    bt = token_beh['行为类型'].value_counts()
                    if not bt.empty:
                        dominant_behavior = bt.index[0]

            if avg_hold is not None:
                if avg_hold < 24:
                    hold_sug = f'短线(<24h, 均{avg_hold:.0f}h)'
                elif avg_hold < 168:
                    hold_sug = f'波段({avg_hold / 24:.1f}天)'
                else:
                    hold_sug = f'中长线({avg_hold / 24:.0f}天)'
            else:
                hold_sug = '数据不足'

            signal_records.append({
                '代币符号': row['代币符号'],
                '代币名称': row['代币名称'],
                '代币地址': token_addr,
                '买入信号': row['买入信号'],
                '置信度': row['置信度'],
                '买入钱包数': row['买入钱包数'],
                '参与社区数': row['参与社区数'],
                '当前收益倍数(末笔价)': row.get(
                    '当前收益倍数(末笔价)', 0
                ),
                '已实现PnL(SOL)': row.get('已实现PnL(SOL)', 0),
                '建议持仓周期': hold_sug,
                '社区行为类型': dominant_behavior or '未知',
                '平均起涨延迟(h)': (
                    round(avg_rise_delay, 1)
                    if avg_rise_delay is not None else None
                ),
                '卖出信号': row['卖出信号'],
                '卖出钱包比例(%)': row['卖出钱包比例(%)'],
                '社区贡献明细': row['社区贡献明细'],
            })

        if signal_records:
            signal_df = pd.DataFrame(signal_records)
            signal_df = signal_df.sort_values(
                '置信度', ascending=False
            ).reset_index(drop=True)
            signal_df.insert(0, '排名', range(1, len(signal_df) + 1))
            self.results['交易信号'] = signal_df

            print(f"  生成 {len(signal_df)} 个交易信号")
            for _, s in signal_df.head(5).iterrows():
                print(f"    [{s['买入信号']}] {s['代币符号']} "
                      f"置信度={s['置信度']} "
                      f"建议: {s['建议持仓周期']}")

    # ============================================================
    # 12. Report
    # ============================================================

    def _save_report(self):
        """保存所有分析结果到 Excel"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'potential_coins_report_{timestamp}.xlsx'

        print(f"\n{'=' * 60}")
        print(f"保存报表: {filename}")
        print(f"{'=' * 60}")

        sheet_order = [
            '交易信号',
            '潜力币置信度',
            # '潜力币排行(1D)',
            # '潜力币排行(7D)',
            '潜力币排行(30D)',
            '集中买入明细',
            '钱包评分明细',
            '钱包画像分组',
            '社区质量评估',
            '社区买卖行为',
            '钱包关联图谱',
            '可信度分析',
        ]

        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            sheet_count = 0
            for name in sheet_order:
                df = self.results.get(name)
                if df is not None and not df.empty:
                    sname = name[:31]  # Excel sheet name max 31 chars
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
        """执行完整分析流程"""
        print("\n" + "=" * 60)
        print("潜力币筛选 - 聪明钱集中买入信号分析")
        print(f"集中买入阈值: >= {self.min_wallets} 个钱包")
        print(f"分析维度: 1D / 7D / 30D")
        print(f"计价单位: SOL（稳定币按 ${self.sol_price_usd}/SOL 折算）")
        print("=" * 60)

        # Step 1-2: 加载数据
        self._load_wallets()
        self._load_transactions()

        if self.trades_df is None or self.trades_df.empty:
            print("\n没有交易数据，退出")
            return

        # Step 3: 可信度分析（用全量数据检测同步交易/刷量/只买不卖）
        self._detect_suspicious_wallets()

        # Step 3.5: 过滤高频钱包（可信度检测需要全量，后续分析不需要）
        if hasattr(self, 'hf_wallets') and self.hf_wallets:
            before = len(self.trades_df)
            self.trades_df = self.trades_df[
                ~self.trades_df['wallet_address'].isin(self.hf_wallets)
            ].reset_index(drop=True)
            removed = before - len(self.trades_df)
            print(f"\n  已过滤高频钱包交易: 移除 {removed} 条"
                  f"（剩余 {len(self.trades_df)} 条，"
                  f"涉及 {self.trades_df['wallet_address'].nunique()} 个钱包）")

            if self.trades_df.empty:
                print("\n过滤后无交易数据，退出")
                return

        # Step 4: 集中买入检测（含收益倍数计算）
        self._detect_concentrated_buying()

        # Step 5: 集中买入明细
        self._analyze_buying_details()

        # Step 6: 钱包画像分组
        self._analyze_wallet_groups()

        # Step 7: 钱包评分（收益 + 频率 + 胜率 + 集中度 + 平台 + 可疑惩罚）
        self._score_wallets()

        # Step 8: 钱包关联图谱（时间加权共买图 + Louvain社区 + PageRank）
        self._analyze_wallet_graph()

        # Step 9: 社区质量评估（钱包评分分布 + 频率类型 + 质量等级）
        self._analyze_community_quality()

        # Step 10: 社区买卖行为分析（持仓周期 + 起涨延迟 + 卖出集中度）
        self._analyze_community_behavior()

        # Step 11: 置信度计算（社区质量 × 买入比例 × 钱包加权分）
        self._calculate_confidence()

        # Step 12: 交易信号生成（置信度 + 建议持仓周期 + 卖出信号）
        self._generate_signals()

        # 保存报表
        self._save_report()

        print("\n分析完成!")


if __name__ == '__main__':
    analyzer = PotentialCoinAnalyzer(min_wallets=2, sol_price_usd=200)
    analyzer.run()
