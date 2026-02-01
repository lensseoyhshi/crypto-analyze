#!/usr/bin/env python3
"""
测试 GMGN 服务器 - 手动发送测试数据
"""
import requests
import json

# 模拟钱包数据
test_data = {
    "timestamp": "2026-01-31T22:20:00.000Z",
    "source": "manual_test",
    "chain": "sol",
    "wallets": [
        {
            "address": "TEST123456789ABCDEF",
            "pnl_7d": 50000.00,
            "win_rate_7d": 0.85,
            "tags": ["smart_degen", "kol"],
            "realized_profit_7d": 45000,
            "buy_7d": 20,
            "sell_7d": 18
        },
        {
            "address": "TEST987654321FEDCBA",
            "pnl_7d": 30000.00,
            "win_rate_7d": 0.75,
            "tags": ["smart_degen"],
            "realized_profit_7d": 28000,
            "buy_7d": 15,
            "sell_7d": 12
        }
    ]
}

print("🧪 发送测试数据到服务器...")
print(f"📊 测试钱包数: {len(test_data['wallets'])}")

try:
    response = requests.post(
        'http://localhost:8899/api/wallets',
        json=test_data,
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    
    if response.ok:
        result = response.json()
        print(f"\n✅ 测试成功！")
        print(f"服务器响应: {result}")
    else:
        print(f"\n❌ 测试失败: HTTP {response.status_code}")
        print(f"响应内容: {response.text}")
        
except Exception as e:
    print(f"\n❌ 连接失败: {e}")
    print("请确保 gmgn_server.py 正在运行")
