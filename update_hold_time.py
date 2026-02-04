"""
计算并更新钱包平均持仓时间
通过分析交易记录计算每个币种的持仓时间，取中位数作为平均持仓时间
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
from statistics import median

from sqlalchemy import select, text
from dao.smart_wallet_dao import SmartWalletDAO
from dao.birdeye_transaction_dao import BirdeyeWalletTransactionDAO
from models.birdeye_transaction import BirdeyeWalletTransaction
from config.database import db_config


class HoldTimeCalculator:
    """持仓时间计算器"""
    
    def __init__(self):
        self.wallet_dao = SmartWalletDAO()
        self.tx_dao = BirdeyeWalletTransactionDAO()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.wallet_dao.__exit__(exc_type, exc_val, exc_tb)
        self.tx_dao.__exit__(exc_type, exc_val, exc_tb)
    
    def get_wallet_transactions(self, address: str, days: int = 7) -> List[BirdeyeWalletTransaction]:
        """
        获取钱包的交易记录（排除系统地址，只查询 swap 和 unknown）
        :param address: 钱包地址
        :param days: 查询最近多少天的数据
        :return: 交易记录列表
        """
        try:
            # 计算时间范围
            cutoff_time = datetime.now() - timedelta(days=days)
            
            # 使用原生 SQL 查询
            sql = text("""
                SELECT * FROM birdeye_wallet_transactions 
                WHERE `from` = :address 
                AND main_action IN ('swap', 'unknown')
                AND block_time >= :cutoff_time
                ORDER BY block_time ASC
            """)
            
            result = self.tx_dao.session.execute(
                sql, 
                {"address": address, "cutoff_time": cutoff_time}
            )
            
            # 将结果转换为 ORM 对象
            transactions = []
            for row in result:
                tx = BirdeyeWalletTransaction()
                tx.id = row.id
                tx.tx_hash = row.tx_hash
                tx.block_number = row.block_number
                tx.block_time = row.block_time
                tx.status = row.status
                tx.from_address = row.__getattribute__('from')  # 'from' 是关键字
                tx.to = row.to
                tx.fee = row.fee
                tx.main_action = row.main_action
                tx.balance_change = row.balance_change
                tx.contract_label = row.contract_label
                tx.token_transfers = row.token_transfers
                tx.block_time_unix = row.block_time_unix
                tx.side = row.side  # 添加 side 字段
                transactions.append(tx)
            
            return transactions
        except Exception as e:
            print(f"查询钱包 {address} 交易记录失败: {str(e)}")
            return []
    
    def extract_token_operations(self, transactions: List[BirdeyeWalletTransaction]) -> Dict[str, List[Dict]]:
        """
        从交易记录中提取每个代币的操作记录（按 to 字段分组）
        :param transactions: 交易记录列表
        :return: {to_address: [{'type': 'buy/sell', 'time': datetime, 'tx_hash': str}]}
        """
        token_operations = defaultdict(list)
        
        for tx in transactions:
            # 检查交易有效性
            if not tx.block_time or not tx.status or not tx.to:
                continue
            
            # 使用 side 字段判断买卖方向
            if not tx.side or tx.side not in ['buy', 'sell']:
                continue
            
            # 直接用 to 字段（代币合约地址）作为分组标识
            token_operations[tx.to].append({
                'type': tx.side,  # buy 或 sell
                'time': tx.block_time,
                'tx_hash': tx.tx_hash
            })
        
        return dict(token_operations)
    
    def calculate_token_hold_time(self, operations: List[Dict]) -> Optional[int]:
        """
        计算单个代币的持仓时间（秒）
        :param operations: 操作记录列表
        :return: 持仓时间（秒），如果无法计算返回 None
        """
        if len(operations) < 2:
            return None
        
        # 按时间排序
        operations.sort(key=lambda x: x['time'])
        
        # 找第一次买入和最后一次卖出
        first_buy = None
        last_sell = None
        
        for op in operations:
            if op['type'] == 'buy' and first_buy is None:
                first_buy = op['time']
            if op['type'] == 'sell':
                last_sell = op['time']
        
        # 计算持仓时间
        if first_buy and last_sell and last_sell > first_buy:
            hold_time = (last_sell - first_buy).total_seconds()
            return int(hold_time)
        
        return None
    
    def calculate_wallet_avg_hold_time(self, address: str, days: int = 7) -> Optional[int]:
        """
        计算钱包的平均持仓时间（中位数）
        :param address: 钱包地址
        :param days: 统计最近多少天
        :return: 平均持仓时间（秒），如果无法计算返回 None
        """
        print(f"  处理钱包: {address[:10]}...")
        
        # 1. 获取交易记录
        transactions = self.get_wallet_transactions(address, days)
        if not transactions:
            print(f"    ⚠️  没有找到交易记录")
            return None
        
        print(f"    找到 {len(transactions)} 笔交易")
        
        # 2. 提取每个代币的操作记录
        token_operations = self.extract_token_operations(transactions)
        if not token_operations:
            print(f"    ⚠️  无法提取代币操作记录")
            return None
        
        print(f"    涉及 {len(token_operations)} 个代币")
        
        # 3. 计算每个代币的持仓时间
        hold_times = []
        for to_address, operations in token_operations.items():
            hold_time = self.calculate_token_hold_time(operations)
            if hold_time:
                hold_times.append(hold_time)
                print(f"      代币 {to_address[:16]}... 持仓时间: {hold_time} 秒 ({hold_time/3600:.2f} 小时)")
        
        # 4. 计算中位数
        if not hold_times:
            print(f"    ⚠️  无法计算持仓时间")
            return None
        
        avg_hold_time = int(median(hold_times))
        print(f"    ✓ 平均持仓时间（中位数）: {avg_hold_time} 秒 ({avg_hold_time/3600:.2f} 小时)")
        
        return avg_hold_time
    
    def update_all_wallets_hold_time(self, days: int = 7, limit: Optional[int] = None):
        """
        更新所有钱包的平均持仓时间
        :param days: 统计最近多少天
        :param limit: 限制处理的钱包数量（用于测试）
        """
        print("=" * 70)
        print(f"开始计算并更新钱包平均持仓时间（最近 {days} 天）")
        print("=" * 70)
        
        # 1. 获取所有钱包
        print(f"\n1. 获取所有钱包...")
        offset = 0
        batch_size = 100
        total_processed = 0
        total_updated = 0
        
        while True:
            wallets = self.wallet_dao.get_all(limit=batch_size, offset=offset)
            if not wallets:
                break
            
            print(f"\n处理第 {offset + 1} 到 {offset + len(wallets)} 个钱包...")
            
            for wallet in wallets:
                total_processed += 1
                
                # 如果设置了限制，检查是否达到限制
                if limit and total_processed > limit:
                    print(f"\n已达到处理限制 ({limit} 个钱包)")
                    break
                
                try:
                    # 2. 计算平均持仓时间
                    avg_hold_time = self.calculate_wallet_avg_hold_time(wallet.address, days)
                    
                    # 3. 更新数据库
                    if avg_hold_time is not None:
                        self.wallet_dao.update(wallet.id, {'avg_hold_time_7d': avg_hold_time})
                        total_updated += 1
                        print(f"    ✓ 已更新到数据库")
                    
                except Exception as e:
                    print(f"    ✗ 处理失败: {str(e)}")
                    continue
            
            # 如果达到限制，退出循环
            if limit and total_processed >= limit:
                break
            
            offset += batch_size
        
        print("\n" + "=" * 70)
        print(f"计算完成！")
        print(f"总处理: {total_processed} 个钱包")
        print(f"成功更新: {total_updated} 个钱包")
        print("=" * 70)
    
    def update_single_wallet_hold_time(self, address: str, days: int = 7):
        """
        更新单个钱包的平均持仓时间
        :param address: 钱包地址
        :param days: 统计最近多少天
        """
        print("=" * 70)
        print(f"计算钱包 {address} 的平均持仓时间（最近 {days} 天）")
        print("=" * 70)
        
        try:
            # 1. 查询钱包
            wallet = self.wallet_dao.get_by_address(address)
            if not wallet:
                print(f"✗ 钱包 {address} 不存在")
                return
            
            # 2. 计算平均持仓时间
            avg_hold_time = self.calculate_wallet_avg_hold_time(address, days)
            
            # 3. 更新数据库
            if avg_hold_time is not None:
                self.wallet_dao.update(wallet.id, {'avg_hold_time_7d': avg_hold_time})
                print(f"\n✓ 成功更新钱包 {address}")
                print(f"  平均持仓时间: {avg_hold_time} 秒 ({avg_hold_time/3600:.2f} 小时)")
            else:
                print(f"\n✗ 无法计算持仓时间")
        
        except Exception as e:
            print(f"✗ 更新失败: {str(e)}")
            import traceback
            traceback.print_exc()


def main():
    """主函数"""
    import sys
    
    print("\n" + "=" * 70)
    print("钱包平均持仓时间计算工具")
    print("=" * 70)
    print("\n使用方式：")
    print("  1. 更新所有钱包: python update_hold_time.py all")
    print("  2. 测试模式（只处理前10个）: python update_hold_time.py test")
    print("  3. 更新单个钱包: python update_hold_time.py <钱包地址>")
    print("\n" + "=" * 70)
    
    with HoldTimeCalculator() as calculator:
        calculator.update_all_wallets_hold_time(days=7)
        # if len(sys.argv) > 1:
        #     command = sys.argv[1]
        #
        #     if command == 'all':
        #         # 更新所有钱包
        #         print("\n开始更新所有钱包...")
        #         calculator.update_all_wallets_hold_time(days=7)
        #
        #     elif command == 'test':
        #         # 测试模式，只处理前10个
        #         print("\n测试模式：只处理前 10 个钱包...")
        #         calculator.update_all_wallets_hold_time(days=7, limit=10)
        #
        #     else:
        #         # 更新单个钱包
        #         address = command
        #         calculator.update_single_wallet_hold_time(address, days=7)
        #
        # else:
        #     # 默认测试模式
        #     print("\n未指定参数，使用测试模式（处理前 10 个钱包）...")
        #     print("使用 'python update_hold_time.py all' 更新所有钱包")
        #     calculator.update_all_wallets_hold_time(days=7, limit=10)


if __name__ == "__main__":
    # 提示：确保数据库连接配置正确
    print("\n⚠️  运行前请确保：")
    print("   1. 数据库连接配置正确（.env 文件）")
    print("   2. 数据表已创建并有数据")
    print("   3. 有足够的交易记录用于计算")
    print("\n按 Enter 继续，Ctrl+C 退出...")
    
    try:
        # input()
        main()
    except KeyboardInterrupt:
        print("\n\n已取消执行")
