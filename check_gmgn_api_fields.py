#!/usr/bin/env python3
"""
检查GMGN API返回的实际字段名
用于修正字段映射
"""
import requests
import json


def check_gmgn_api():
    """检查GMGN API返回的字段"""
    
    # GMGN API URLs
    apis = [
        ("聪明钱", "https://gmgn.ai/defi/quotation/v1/rank/sol/wallets/7d?tag=smart_degen&limit=5"),
        ("知名KOL", "https://gmgn.ai/defi/quotation/v1/rank/sol/wallets/7d?tag=renowned&limit=5"),
        ("热门追踪", "https://gmgn.ai/defi/quotation/v1/rank/sol/wallets/7d?tag=top_followed&limit=5"),
        ("热门备注", "https://gmgn.ai/defi/quotation/v1/rank/sol/wallets/7d?tag=top_renamed&limit=5"),
    ]
    
    print("=" * 80)
    print("🔍 检查 GMGN API 返回的字段")
    print("=" * 80)
    
    for tag_name, url in apis:
        print(f"\n📡 请求: {tag_name}")
        print(f"   URL: {url}")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"   ❌ 请求失败: HTTP {response.status_code}")
                continue
            
            data = response.json()
            
            if data.get('code') != 0:
                print(f"   ❌ API返回错误: {data.get('msg')}")
                continue
            
            # 获取第一个钱包的数据
            wallets = data.get('data', {}).get('rank', [])
            
            if not wallets:
                print(f"   ❌ 没有返回钱包数据")
                continue
            
            first_wallet = wallets[0]
            
            print(f"   ✅ 成功获取 {len(wallets)} 个钱包")
            print(f"\n   📋 第一个钱包的所有字段:")
            print(f"   " + "-" * 76)
            
            # 打印所有字段
            for key in sorted(first_wallet.keys()):
                value = first_wallet[key]
                
                # 格式化显示
                if isinstance(value, float):
                    value_str = f"{value:.6f}"
                elif isinstance(value, list):
                    value_str = f"[...] ({len(value)} items)"
                elif isinstance(value, dict):
                    value_str = f"{{...}} ({len(value)} keys)"
                else:
                    value_str = str(value)[:50]
                
                print(f"   {key:30s} = {value_str}")
            
            # 重点检查的字段
            print(f"\n   🎯 重点字段检查:")
            important_fields = [
                'win_rate_7d', 'winrate', 'winrate_7d', 'win_rate',
                'avg_hold_time', 'avg_hold_time_7d', 'hold_time',
                'buy_7d', 'sell_7d', 'buy', 'sell',
                'pnl_7d', 'profit_7d', 'realized_profit_7d',
                'tags'
            ]
            
            for field in important_fields:
                if field in first_wallet:
                    value = first_wallet[field]
                    print(f"   ✅ {field:30s} = {value}")
                else:
                    print(f"   ❌ {field:30s} = (不存在)")
            
        except requests.Timeout:
            print(f"   ❌ 请求超时")
        except Exception as e:
            print(f"   ❌ 错误: {e}")
    
    print("\n" + "=" * 80)
    print("💡 提示:")
    print("=" * 80)
    print("1. 检查上面列出的字段名")
    print("2. 如果字段名不匹配，需要修改 gmgn_server.py 中的字段映射")
    print("3. 特别注意：win_rate、hold_time 等关键字段的实际名称")
    print()


if __name__ == '__main__':
    check_gmgn_api()
