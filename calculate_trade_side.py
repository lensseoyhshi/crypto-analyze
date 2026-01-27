"""
计算交易方向（buy/sell）脚本
根据 balance_change 判断交易是买入还是卖出
"""

import json
from typing import Optional, Dict, List, Tuple
from sqlalchemy import select, and_, or_
from dao.birdeye_transaction_dao import BirdeyeWalletTransactionDAO
from models.birdeye_transaction import BirdeyeWalletTransaction
from config.database import db_config


# 定义 Quote Token（钱）
QUOTE_TOKENS = {'SOL', 'USDC', 'USDT', 'Wrapped SOL', 'WSOL'}


def calculate_side(balance_change_str: str) -> Tuple[Optional[str], str]:
    """
    根据 balance_change 计算交易方向
    
    :param balance_change_str: balance_change JSON 字符串
    :return: (side, reason) - side 为 'buy'/'sell'/None, reason 为判断原因说明
    """
    if not balance_change_str:
        return None, "balance_change 为空"
    
    try:
        balance_change = json.loads(balance_change_str)
    except json.JSONDecodeError as e:
        return None, f"balance_change JSON 解析失败: {str(e)}"
    
    # 检查长度
    if len(balance_change) < 2:
        return None, f"balance_change 长度不足2，实际长度: {len(balance_change)}"
    
    # 分类：Quote Token 和 其他 Token
    quote_token_changes = []
    other_token_changes = []
    
    for change in balance_change:
        symbol = change.get('symbol', '')
        name = change.get('name', '')
        amount = change.get('amount', 0)
        
        # 判断是否是 Quote Token
        is_quote = (symbol in QUOTE_TOKENS or name in QUOTE_TOKENS)
        
        if is_quote:
            quote_token_changes.append({
                'symbol': symbol,
                'name': name,
                'amount': amount
            })
        else:
            other_token_changes.append({
                'symbol': symbol,
                'name': name,
                'amount': amount
            })
    
    # 需要至少有一个 Quote Token 和一个其他 Token
    if len(quote_token_changes) == 0:
        return None, "没有找到 Quote Token (SOL/USDC/USDT)"
    
    if len(other_token_changes) == 0:
        return None, "没有找到其他 Token"
    
    # 获取 Quote Token 的变动（通常只有一个，如果有多个取总和）
    quote_amount = sum(token['amount'] for token in quote_token_changes)
    
    # 获取其他 Token 的变动（通常只有一个，如果有多个取总和）
    other_amount = sum(token['amount'] for token in other_token_changes)
    
    # 判断方向
    if quote_amount < 0 and other_amount > 0:
        # Quote Token 减少，其他 Token 增加 -> 买入
        quote_info = ', '.join([f"{t['symbol']}({t['amount']})" for t in quote_token_changes])
        other_info = ', '.join([f"{t['symbol']}({t['amount']})" for t in other_token_changes])
        return 'buy', f"Quote Token 减少 ({quote_info}), 其他 Token 增加 ({other_info})"
    
    elif quote_amount > 0 and other_amount < 0:
        # Quote Token 增加，其他 Token 减少 -> 卖出
        quote_info = ', '.join([f"{t['symbol']}({t['amount']})" for t in quote_token_changes])
        other_info = ', '.join([f"{t['symbol']}({t['amount']})" for t in other_token_changes])
        return 'sell', f"Quote Token 增加 ({quote_info}), 其他 Token 减少 ({other_info})"
    
    else:
        # 其他情况（可能是两个方向相同，或者金额为0）
        return None, f"无法判断方向: Quote Token 变动={quote_amount}, 其他 Token 变动={other_amount}"


def analyze_transactions(limit: int = 100, offset: int = 0, show_detail: bool = True) -> Dict:
    """
    分析交易记录，计算交易方向
    
    :param limit: 查询数量限制
    :param offset: 偏移量
    :param show_detail: 是否显示详细信息
    :return: 统计结果字典
    """
    print(f"\n{'='*80}")
    print(f"开始分析交易记录 (limit={limit}, offset={offset})")
    print(f"{'='*80}\n")
    
    # 创建 DAO
    with BirdeyeWalletTransactionDAO() as dao:
        # 构建查询条件
        session = dao.session
        stmt = (
            select(BirdeyeWalletTransaction)
            .where(
                and_(
                    BirdeyeWalletTransaction.to != '11111111111111111111111111111111',
                    or_(
                        BirdeyeWalletTransaction.main_action == 'swap',
                        BirdeyeWalletTransaction.main_action == 'unknown'
                    )
                )
            )
            .limit(limit)
            .offset(offset)
        )
        
        transactions = list(session.execute(stmt).scalars())
        
        print(f"查询到 {len(transactions)} 条交易记录\n")
        
        # 统计结果
        stats = {
            'total': len(transactions),
            'buy': 0,
            'sell': 0,
            'unknown': 0,
            'reasons': {}
        }
        
        # 逐条分析
        for i, tx in enumerate(transactions, 1):
            side, reason = calculate_side(tx.balance_change)
            
            # 更新统计
            if side == 'buy':
                stats['buy'] += 1
            elif side == 'sell':
                stats['sell'] += 1
            else:
                stats['unknown'] += 1
                # 统计无法判断的原因
                if reason not in stats['reasons']:
                    stats['reasons'][reason] = 0
                stats['reasons'][reason] += 1
            
            # 显示详细信息
            if show_detail:
                print(f"[{i}/{len(transactions)}] ID: {tx.id}, TX: {tx.tx_hash[:16]}...")
                print(f"  时间: {tx.block_time}")
                print(f"  钱包: {tx.from_address[:16]}...")
                print(f"  动作: {tx.main_action}")
                print(f"  方向: {side or '无法判断'}")
                print(f"  原因: {reason}")
                
                # 显示 balance_change
                if tx.balance_change:
                    try:
                        bc = json.loads(tx.balance_change)
                        print(f"  Balance Change:")
                        for change in bc:
                            symbol = change.get('symbol', 'N/A')
                            amount = change.get('amount', 0)
                            print(f"    - {symbol}: {amount:,}")
                    except:
                        pass
                
                print()
        
        return stats


def print_statistics(stats: Dict):
    """打印统计结果"""
    print(f"\n{'='*80}")
    print("统计结果")
    print(f"{'='*80}\n")
    
    print(f"总计: {stats['total']} 条交易")
    print(f"  - 买入 (Buy):  {stats['buy']:>6} 条 ({stats['buy']/stats['total']*100:>5.1f}%)" if stats['total'] > 0 else "  - 买入 (Buy):  0 条")
    print(f"  - 卖出 (Sell): {stats['sell']:>6} 条 ({stats['sell']/stats['total']*100:>5.1f}%)" if stats['total'] > 0 else "  - 卖出 (Sell): 0 条")
    print(f"  - 无法判断:     {stats['unknown']:>6} 条 ({stats['unknown']/stats['total']*100:>5.1f}%)" if stats['total'] > 0 else "  - 无法判断:     0 条")
    
    if stats['reasons']:
        print(f"\n无法判断的原因分布:")
        for reason, count in sorted(stats['reasons'].items(), key=lambda x: x[1], reverse=True):
            print(f"  - {reason}: {count} 条")
    
    print()


def main():
    """主函数"""
    print("\n" + "="*80)
    print("交易方向计算工具")
    print("="*80)
    
    # 配置参数
    limit = 50  # 每次查询条数
    show_detail = True  # 是否显示详细信息
    
    # 分析交易
    stats = analyze_transactions(limit=limit, offset=0, show_detail=show_detail)
    
    # 打印统计结果
    print_statistics(stats)
    
    print("\n提示: 如果需要更新数据库，请使用 update_trade_side.py 脚本")


if __name__ == "__main__":
    main()
