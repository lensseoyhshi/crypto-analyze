#!/usr/bin/env python3
"""
测试标签映射逻辑
验证GMGN API返回的tags能正确映射到数据库字段
"""

def test_tag_mapping():
    """测试标签映射"""
    
    # 模拟GMGN API返回的不同tags
    test_cases = [
        {
            'name': 'Smart Degen (聪明钱)',
            'tags': ['smart_degen'],
            'expected': {
                'is_smart_money': 1,
                'is_kol': 0,
                'is_hot_followed': 0,
                'is_hot_remarked': 0
            }
        },
        {
            'name': 'Renowned (知名KOL)',
            'tags': ['renowned'],
            'expected': {
                'is_smart_money': 0,
                'is_kol': 1,
                'is_hot_followed': 0,
                'is_hot_remarked': 0
            }
        },
        {
            'name': 'Top Followed (热门追踪)',
            'tags': ['top_followed'],
            'expected': {
                'is_smart_money': 0,
                'is_kol': 0,
                'is_hot_followed': 1,
                'is_hot_remarked': 0
            }
        },
        {
            'name': 'Top Renamed (热门备注)',
            'tags': ['top_renamed'],
            'expected': {
                'is_smart_money': 0,
                'is_kol': 0,
                'is_hot_followed': 0,
                'is_hot_remarked': 1
            }
        },
        {
            'name': '多标签组合',
            'tags': ['smart_degen', 'renowned', 'trojan', 'bullx'],
            'expected': {
                'is_smart_money': 1,
                'is_kol': 1,
                'is_hot_followed': 0,
                'is_hot_remarked': 0,
                'uses_trojan': 1,
                'uses_bullx': 1
            }
        }
    ]
    
    print("=" * 70)
    print("🧪 标签映射测试")
    print("=" * 70)
    
    for test in test_cases:
        print(f"\n测试用例: {test['name']}")
        print(f"输入tags: {test['tags']}")
        
        # 执行映射逻辑（与gmgn_server.py中的逻辑一致）
        tags = test['tags']
        result = {
            'is_smart_money': 1 if 'smart_degen' in tags or 'smart_money' in tags else 0,
            'is_kol': 1 if 'kol' in tags or 'renowned' in tags else 0,
            'is_whale': 1 if 'whale' in tags else 0,
            'is_sniper': 1 if 'sniper' in tags else 0,
            'is_hot_followed': 1 if 'hot_followed' in tags or 'top_followed' in tags else 0,
            'is_hot_remarked': 1 if 'hot_remarked' in tags or 'top_renamed' in tags else 0,
            'uses_trojan': 1 if 'trojan' in tags else 0,
            'uses_bullx': 1 if 'bullx' in tags else 0,
            'uses_photon': 1 if 'photon' in tags else 0,
            'uses_axiom': 1 if 'axiom' in tags else 0,
            'uses_bot': 1 if 'bot' in tags else 0,
        }
        
        # 验证结果
        passed = True
        for key, expected_value in test['expected'].items():
            actual_value = result.get(key, 0)
            if actual_value != expected_value:
                passed = False
                print(f"  ❌ {key}: 期望={expected_value}, 实际={actual_value}")
        
        if passed:
            print(f"  ✅ 测试通过")
            # 打印映射结果
            mapped_fields = [k for k, v in result.items() if v == 1]
            print(f"  📝 映射字段: {', '.join(mapped_fields)}")
        else:
            print(f"  ❌ 测试失败")
    
    print("\n" + "=" * 70)
    print("🎯 API URL 映射说明：")
    print("=" * 70)
    print("1. https://gmgn.ai/defi/quotation/v1/rank/sol/wallets/7d?tag=smart_degen")
    print("   → is_smart_money = 1")
    print()
    print("2. https://gmgn.ai/defi/quotation/v1/rank/sol/wallets/7d?tag=renowned")
    print("   → is_kol = 1")
    print()
    print("3. https://gmgn.ai/defi/quotation/v1/rank/sol/wallets/7d?tag=top_followed")
    print("   → is_hot_followed = 1")
    print()
    print("4. https://gmgn.ai/defi/quotation/v1/rank/sol/wallets/7d?tag=top_renamed")
    print("   → is_hot_remarked = 1")
    print("=" * 70)


if __name__ == '__main__':
    test_tag_mapping()
