"""
测试交易方向判断逻辑（不需要数据库）
可以直接运行此脚本来测试 calculate_side 函数
"""

import json
from typing import Optional, Tuple


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


def test_examples():
    """测试示例数据"""
    
    print("\n" + "="*80)
    print("交易方向判断逻辑测试")
    print("="*80 + "\n")
    
    # 测试用例
    test_cases = [
        {
            "name": "买入示例（你提供的例子）",
            "data": [
                {
                    "amount": -105000,
                    "symbol": "SOL",
                    "name": "Wrapped SOL",
                    "decimals": 9,
                    "address": "So11111111111111111111111111111111111111112",
                    "logoURI": "https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/So11111111111111111111111111111111111111112/logo.png",
                    "isScaledUiToken": False,
                    "multiplier": None
                },
                {
                    "amount": 4853956,
                    "symbol": "penguin",
                    "name": "Embrace the trenches",
                    "decimals": 6,
                    "address": "DYWh7eby9K3EVmuZtsZi4dLP4ZpwFddXABWw5m4Bpump",
                    "logoURI": "https://ipfs.io/ipfs/bafkreiea3pjgbc4ij45asbktv6yippagseu45trgfdccvlqgobucwozueq",
                    "isScaledUiToken": False,
                    "multiplier": None
                }
            ]
        },
        {
            "name": "卖出示例",
            "data": [
                {
                    "amount": 200000,
                    "symbol": "SOL",
                    "name": "Wrapped SOL",
                    "decimals": 9
                },
                {
                    "amount": -5000000,
                    "symbol": "TOKEN",
                    "name": "Some Token",
                    "decimals": 6
                }
            ]
        },
        {
            "name": "使用 USDC 买入",
            "data": [
                {
                    "amount": -1000000,
                    "symbol": "USDC",
                    "name": "USD Coin",
                    "decimals": 6
                },
                {
                    "amount": 3000000,
                    "symbol": "TOKEN",
                    "name": "Some Token",
                    "decimals": 6
                }
            ]
        },
        {
            "name": "使用 USDT 卖出",
            "data": [
                {
                    "amount": 500000,
                    "symbol": "USDT",
                    "name": "Tether USD",
                    "decimals": 6
                },
                {
                    "amount": -2000000,
                    "symbol": "TOKEN",
                    "name": "Some Token",
                    "decimals": 6
                }
            ]
        },
        {
            "name": "长度不足（只有1个token）",
            "data": [
                {
                    "amount": -105000,
                    "symbol": "SOL",
                    "name": "Wrapped SOL"
                }
            ]
        },
        {
            "name": "没有 Quote Token",
            "data": [
                {
                    "amount": -100000,
                    "symbol": "TOKEN1",
                    "name": "Token 1"
                },
                {
                    "amount": 200000,
                    "symbol": "TOKEN2",
                    "name": "Token 2"
                }
            ]
        }
    ]
    
    # 执行测试
    for i, test_case in enumerate(test_cases, 1):
        print(f"测试用例 {i}: {test_case['name']}")
        print("-" * 80)
        
        # 转换为 JSON 字符串
        balance_change_str = json.dumps(test_case['data'], ensure_ascii=False)
        
        # 计算方向
        side, reason = calculate_side(balance_change_str)
        
        # 显示结果
        print(f"balance_change:")
        for token in test_case['data']:
            symbol = token.get('symbol', 'N/A')
            amount = token.get('amount', 0)
            name = token.get('name', 'N/A')
            print(f"  - {symbol} ({name}): {amount:,}")
        
        print(f"\n结果:")
        print(f"  方向: {side or '无法判断'}")
        print(f"  原因: {reason}")
        print("\n")


def main():
    """主函数"""
    test_examples()
    
    print("="*80)
    print("测试完成！")
    print("="*80 + "\n")
    
    print("如果需要分析数据库中的实际数据，请：")
    print("1. 确保已安装依赖: pip install -r requirements.txt")
    print("2. 配置好数据库连接（.env 文件）")
    print("3. 运行: python calculate_trade_side.py")
    print()


if __name__ == "__main__":
    main()
