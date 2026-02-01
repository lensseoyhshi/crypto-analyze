#!/usr/bin/env python3
"""
GMGN 聪明钱监控 - 直接 API 调用版本
绕过浏览器，直接用 HTTP 请求获取数据（需要手动获取 Cookie）
"""
import requests
import json
import time
from datetime import datetime

# ================= 配置区 =================
# GMGN API 地址（你在浏览器中找到的）
API_URL = "https://gmgn.ai/defi/quotation/v1/rank/sol/wallets/7d"

# API 参数
API_PARAMS = {
    "tag": ["smart_degen", "pump_smart"],  # 标签：聪明钱、pump 聪明钱
    "orderby": "pnl_7d",  # 按7日盈亏排序
    "direction": "desc",  # 降序
    "limit": 100  # 获取前100个
}

# 请求头 - 模拟真实浏览器
# ⚠️ 你需要从浏览器中复制 Cookie 和其他必要的头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://gmgn.ai/?chain=sol&tab=smart_degen",
    "Origin": "https://gmgn.ai",
    "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    # ⚠️ 你需要把下面的 Cookie 替换成你自己的
    # 在 Chrome 中：F12 -> Network -> 找到 API 请求 -> Headers -> 复制 Cookie
    "Cookie": "_ga=GA1.1.1365356802.1767079342; __cf_bm=AGXuwyc9_XEO3zaeE.QiJPAJhCeBrB7dXYaHmkjqIvA-1769864461-1.0.1.1-UvDsTs6gHu7djRjCXc0Q3xv6JbRYV7.3xZ9ZYHMHxfr.rxdeOC7TzyU8IH8FTn0XCaNL9hLBvw3G7ojgEZ_HJypUdcCyt6_Pjzlk6i5jJ.c; _ga_0XM0LYXGC8=GS2.1.s1769864459$o255$g1$t1769864473$j46$l0$h0; sid=gmgn%7Cd258bc769593861aa49de8c2705af2c5; _ga_UGLVBMV4Z0=GS1.2.1769864473270415.7fa402c0c3fe219ae4632020ca252b1b.5xxQwy7mDpflaMCTrE4G%2BQ%3D%3D.Kkkw6digGgvW9JVT5UVISg%3D%3D.VTgpnUSUnvxBD3Y%2FGRJ%2Fkw%3D%3D.VmDY%2B5%2BvlZUqaPRIKPSp6Q%3D%3D"
}

# 抓取间隔（秒）
LOOP_INTERVAL = 60
# =========================================


def fetch_smart_wallets():
    """
    直接调用 GMGN API 获取聪明钱数据
    """
    try:
        print(f"🌐 正在请求 API: {API_URL}")
        
        # 发送 GET 请求
        response = requests.get(
            API_URL,
            params=API_PARAMS,
            headers=HEADERS,
            timeout=30
        )
        
        print(f"📡 响应状态码: {response.status_code}")
        
        if response.status_code == 403:
            print("❌ 403 Forbidden - 可能原因：")
            print("   1. Cookie 无效或过期")
            print("   2. 需要人工验证（Cloudflare）")
            print("   3. IP 被限制")
            print("\n💡 解决方案：")
            print("   1. 在浏览器中访问 https://gmgn.ai")
            print("   2. F12 打开开发者工具")
            print("   3. 切换到 Network 标签")
            print("   4. 刷新页面，找到 'rank/sol/wallets/7d' 请求")
            print("   5. 右键 -> Copy -> Copy as cURL")
            print("   6. 把 Cookie 部分粘贴到脚本的 HEADERS['Cookie'] 中")
            return None
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("code") == 0 and "data" in data:
                # 解析钱包数据
                if "rank" in data["data"]:
                    wallets = data["data"]["rank"]
                elif isinstance(data["data"], list):
                    wallets = data["data"]
                else:
                    print(f"⚠️  数据结构异常: {data['data'].keys()}")
                    return None
                
                print(f"✅ 成功获取 {len(wallets)} 个钱包数据")
                return wallets
            else:
                print(f"⚠️  API 返回错误码: {data.get('code')}")
                if "msg" in data:
                    print(f"错误信息: {data['msg']}")
                return None
        else:
            print(f"⚠️  HTTP {response.status_code}")
            print(f"响应内容: {response.text[:500]}")
            return None
            
    except requests.exceptions.Timeout:
        print("⏰ 请求超时")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        print(f"响应内容: {response.text[:500]}")
        return None


def process_wallets(wallets):
    """
    处理钱包数据
    """
    print("\n" + "=" * 70)
    print(f"📊 钱包排行榜 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    for index, wallet in enumerate(wallets[:10], 1):  # 显示前10个
        address = wallet.get('address') or wallet.get('wallet_address')
        pnl_7d = wallet.get('pnl_7d') or wallet.get('profit_7d', 0)
        win_rate = wallet.get('win_rate_7d') or wallet.get('winrate', 0)
        tags = wallet.get('tags', [])
        
        print(f"\n🏆 排名 {index}: {address}")
        print(f"   💰 7日盈亏: ${pnl_7d:,.2f}")
        print(f"   📈 7日胜率: {win_rate*100:.1f}%")
        print(f"   🏷️  标签: {', '.join(tags)}")
        
        # 显示其他可用数据
        if wallet.get('realized_profit_7d'):
            print(f"   💵 已实现利润: ${wallet.get('realized_profit_7d'):,.2f}")
        if wallet.get('buy_7d') or wallet.get('sell_7d'):
            print(f"   📊 交易次数: {wallet.get('buy_7d', 0)}买 / {wallet.get('sell_7d', 0)}卖")
    
    print("\n" + "=" * 70)
    print(f"✅ 共 {len(wallets)} 个钱包")
    print("=" * 70)
    
    # TODO: 在这里添加数据库插入逻辑
    # from dao.smart_wallet_dao import SmartWalletDAO
    # ...


def main():
    """
    主函数 - 循环监控
    """
    print("🚀 GMGN 聪明钱监控系统 (直接 API 版本)")
    print("=" * 70)
    
    # 检查 Cookie 是否配置
    if HEADERS["Cookie"] == "YOUR_COOKIE_HERE":
        print("⚠️  警告：Cookie 未配置！")
        print("\n📖 配置步骤：")
        print("1. 在 Chrome 中访问 https://gmgn.ai")
        print("2. F12 打开开发者工具 -> Network 标签")
        print("3. 刷新页面，找到 'rank/sol/wallets/7d' 请求")
        print("4. 点击该请求 -> Headers -> 找到 'Cookie' 字段")
        print("5. 复制完整的 Cookie 值")
        print("6. 粘贴到脚本的 HEADERS['Cookie'] 中")
        print("\n继续运行将使用空 Cookie（大概率失败）...")
        input("\n按 Enter 继续，或 Ctrl+C 退出...")
    
    print(f"\n⏰ 监控间隔: {LOOP_INTERVAL} 秒")
    print("🔄 开始监控...\n")
    
    while True:
        try:
            wallets = fetch_smart_wallets()
            
            if wallets:
                process_wallets(wallets)
            else:
                print("❌ 本轮抓取失败")
            
            print(f"\n⏸️  休息 {LOOP_INTERVAL} 秒...\n")
            time.sleep(LOOP_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n\n👋 程序已手动停止")
            break
        except Exception as e:
            print(f"\n❌ 意外错误: {e}")
            import traceback
            traceback.print_exc()
            print(f"\n10秒后重试...")
            time.sleep(10)


if __name__ == "__main__":
    main()
