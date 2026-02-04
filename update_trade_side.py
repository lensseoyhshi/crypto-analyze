"""
批量更新数据库中交易记录的 side 字段
根据 balance_change 计算交易方向（buy/sell）
"""

import json
from typing import Optional, Tuple
from sqlalchemy import select, update, and_, or_
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
        return 'buy', "买入"
    elif quote_amount > 0 and other_amount < 0:
        # Quote Token 增加，其他 Token 减少 -> 卖出
        return 'sell', "卖出"
    else:
        # 其他情况（可能是两个方向相同，或者金额为0）
        return None, f"无法判断方向: Quote Token 变动={quote_amount}, 其他 Token 变动={other_amount}"


def update_trade_sides(batch_size: int = 1000, limit: Optional[int] = None, dry_run: bool = False):
    """
    批量更新交易记录的 side 字段
    
    :param batch_size: 每批处理的记录数
    :param limit: 总共处理的记录数限制（None 表示处理所有）
    :param dry_run: 是否为试运行模式（不实际更新数据库）
    """
    print("\n" + "="*80)
    print(f"批量更新交易方向 (side) 字段")
    print(f"批次大小: {batch_size}")
    print(f"处理限制: {limit if limit else '无限制'}")
    print(f"模式: {'试运行（不更新数据库）' if dry_run else '正式运行'}")
    print("="*80 + "\n")
    
    # 统计信息
    stats = {
        'total': 0,
        'updated_buy': 0,
        'updated_sell': 0,
        'skipped': 0,
        'errors': 0
    }
    
    with BirdeyeWalletTransactionDAO() as dao:
        session = dao.session
        
        # 查询需要更新的记录（side 为 NULL 且 main_action 为 swap 或 unknown）
        offset = 0
        processed = 0
        
        while True:
            # 构建查询
            stmt = (
                select(BirdeyeWalletTransaction)
                .where(
                    and_(
                        or_(
                            BirdeyeWalletTransaction.main_action == 'swap',
                            BirdeyeWalletTransaction.main_action == 'unknown'
                        ),
                        BirdeyeWalletTransaction.side.is_(None)  # 只更新 side 为 NULL 的记录
                    )
                )
                .limit(batch_size)
                .offset(offset)
            )
            
            transactions = list(session.execute(stmt).scalars())
            
            if not transactions:
                print("\n没有更多需要更新的记录")
                break
            
            print(f"\n处理批次 (offset={offset}, count={len(transactions)})")
            print("-" * 80)
            
            # 处理每条记录
            batch_updates = []
            for tx in transactions:
                stats['total'] += 1
                processed += 1
                
                # 计算 side
                side, reason = calculate_side(tx.balance_change)
                
                if side:
                    batch_updates.append({
                        'id': tx.id,
                        'side': side,
                        'tx_hash': tx.tx_hash[:16]
                    })
                    
                    if side == 'buy':
                        stats['updated_buy'] += 1
                    elif side == 'sell':
                        stats['updated_sell'] += 1
                else:
                    stats['skipped'] += 1
                
                # 每100条显示一次进度
                if stats['total'] % 100 == 0:
                    print(f"已处理: {stats['total']} 条 "
                          f"(买入: {stats['updated_buy']}, 卖出: {stats['updated_sell']}, "
                          f"跳过: {stats['skipped']})")
            
            # 批量更新数据库
            if batch_updates :
                try:
                    for item in batch_updates:
                        update_stmt = (
                            update(BirdeyeWalletTransaction)
                            .where(BirdeyeWalletTransaction.id == item['id'])
                            .values(side=item['side'])
                        )
                        session.execute(update_stmt)
                    
                    session.commit()
                    print(f"✓ 成功更新 {len(batch_updates)} 条记录")
                except Exception as e:
                    session.rollback()
                    stats['errors'] += len(batch_updates)
                    print(f"✗ 批量更新失败: {str(e)}")
            elif batch_updates and dry_run:
                print(f"[试运行] 将更新 {len(batch_updates)} 条记录")
                # 显示前5条示例
                for i, item in enumerate(batch_updates[:5]):
                    print(f"  - ID: {item['id']}, TX: {item['tx_hash']}..., Side: {item['side']}")
                if len(batch_updates) > 5:
                    print(f"  ... 还有 {len(batch_updates) - 5} 条")
            
            # 检查是否达到限制
            if limit and processed >= limit:
                print(f"\n已达到处理限制 ({limit} 条)")
                break
            
            offset += batch_size
    
    # 打印最终统计
    print("\n" + "="*80)
    print("更新完成 - 统计结果")
    print("="*80)
    print(f"总处理记录数: {stats['total']}")
    print(f"  - 更新为 buy:  {stats['updated_buy']:>6} 条 ({stats['updated_buy']/stats['total']*100:>5.1f}%)" if stats['total'] > 0 else "  - 更新为 buy:  0 条")
    print(f"  - 更新为 sell: {stats['updated_sell']:>6} 条 ({stats['updated_sell']/stats['total']*100:>5.1f}%)" if stats['total'] > 0 else "  - 更新为 sell: 0 条")
    print(f"  - 跳过:         {stats['skipped']:>6} 条 ({stats['skipped']/stats['total']*100:>5.1f}%)" if stats['total'] > 0 else "  - 跳过:         0 条")
    print(f"  - 错误:         {stats['errors']:>6} 条" if stats['errors'] > 0 else "")
    print()
    
    if dry_run:
        print("注意: 这是试运行模式，数据库未被修改")
        print("要正式更新数据库，请设置 dry_run=False")
    
    return stats


def main():
    """主函数"""
    import sys
    
    print("\n" + "="*80)
    print("交易方向批量更新工具")
    print("="*80)
    
    # 解析命令行参数
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv
    
    print(f"\n当前模式: {'试运行（不修改数据库）' if dry_run else '正式运行（将修改数据库）'}")
    print(f"命令行参数: {sys.argv}")
    
    # 询问用户确认
    if not dry_run:
        print("\n警告: 这将修改数据库中的数据！")
        print("建议先使用 --dry-run 参数进行试运行")
        confirm = input("\n确认要继续吗？(yes/no): ")
        if confirm.lower() not in ['yes', 'y']:
            print("操作已取消")
            return
    
    # 执行更新
    try:
        stats = update_trade_sides(
            batch_size=1000,  # 每批处理1000条
            limit=None,       # 处理所有记录
            dry_run=dry_run
        )
        
        print("\n操作完成！")
        
    except KeyboardInterrupt:
        print("\n\n操作被用户中断")
    except Exception as e:
        print(f"\n\n错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
