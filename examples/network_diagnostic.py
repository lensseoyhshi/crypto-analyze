#!/usr/bin/env python3
"""
网络诊断工具 - 帮助排查网络连接问题
"""

import asyncio
import httpx
import socket
import os
from urllib.parse import urlparse


def check_system_proxy():
    """检查系统代理设置"""
    print("=" * 60)
    print("1. 检查系统代理设置")
    print("=" * 60)
    
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY']
    
    has_proxy = False
    for var in proxy_vars:
        value = os.environ.get(var)
        if value:
            print(f"⚠️  发现代理: {var} = {value}")
            has_proxy = True
    
    if not has_proxy:
        print("✅ 未发现系统代理设置")
    else:
        print("\n💡 建议: 如果代理不可用，需要禁用它们")
    
    return has_proxy


def check_dns():
    """检查 DNS 解析"""
    print("\n" + "=" * 60)
    print("2. 检查 DNS 解析")
    print("=" * 60)
    
    hostname = "api.dexscreener.com"
    
    try:
        ip = socket.gethostbyname(hostname)
        print(f"✅ DNS 解析成功: {hostname} -> {ip}")
        return True
    except socket.gaierror as e:
        print(f"❌ DNS 解析失败: {e}")
        print("💡 建议: 检查网络连接或 DNS 设置")
        return False


def check_socket_connection():
    """检查 Socket 连接"""
    print("\n" + "=" * 60)
    print("3. 检查 Socket 连接")
    print("=" * 60)
    
    hostname = "api.dexscreener.com"
    port = 443
    
    try:
        sock = socket.create_connection((hostname, port), timeout=10)
        sock.close()
        print(f"✅ Socket 连接成功: {hostname}:{port}")
        return True
    except socket.timeout:
        print(f"❌ 连接超时")
        return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False


async def test_httpx_without_proxy():
    """测试不使用代理的 httpx 请求"""
    print("\n" + "=" * 60)
    print("4. 测试 HTTPX 请求（不使用代理）")
    print("=" * 60)
    
    url = "https://api.dexscreener.com/token-boosts/top/v1"
    
    # 清除代理环境变量
    os.environ['HTTP_PROXY'] = ''
    os.environ['HTTPS_PROXY'] = ''
    os.environ['http_proxy'] = ''
    os.environ['https_proxy'] = ''
    
    try:
        async with httpx.AsyncClient(
            verify=False,
            timeout=30.0,
            proxies=None,
            trust_env=False
        ) as client:
            print("发送请求...")
            response = await client.get(url)
            response.raise_for_status()
            
            data = response.json()
            print(f"✅ 请求成功! 获取到 {len(data)} 个代币")
            
            # 显示第一个
            if data:
                first = data[0]
                print(f"\n第一个代币:")
                print(f"  描述: {first.get('description')}")
                print(f"  链: {first.get('chainId')}")
                print(f"  地址: {first.get('tokenAddress')[:20]}...")
            
            return True
            
    except httpx.ConnectTimeout:
        print("❌ 连接超时")
        print("💡 可能原因:")
        print("   1. 网络不稳定")
        print("   2. 防火墙阻止")
        print("   3. 代理问题")
        return False
    except httpx.HTTPError as e:
        print(f"❌ HTTP 错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False


async def test_with_different_timeout():
    """测试不同的超时时间"""
    print("\n" + "=" * 60)
    print("5. 测试不同超时时间")
    print("=" * 60)
    
    url = "https://api.dexscreener.com/token-boosts/top/v1"
    
    # 清除代理
    os.environ['HTTP_PROXY'] = ''
    os.environ['HTTPS_PROXY'] = ''
    os.environ['http_proxy'] = ''
    os.environ['https_proxy'] = ''
    
    for timeout in [10, 30, 60]:
        print(f"\n尝试超时时间: {timeout} 秒...")
        try:
            async with httpx.AsyncClient(
                verify=False,
                timeout=timeout,
                proxies=None,
                trust_env=False
            ) as client:
                response = await client.get(url)
                data = response.json()
                print(f"✅ 成功! (超时: {timeout}s, 数据量: {len(data)})")
                return True
        except httpx.ConnectTimeout:
            print(f"❌ 超时 ({timeout}s)")
        except Exception as e:
            print(f"❌ 错误: {e}")
    
    return False


def show_system_info():
    """显示系统信息"""
    print("\n" + "=" * 60)
    print("6. 系统信息")
    print("=" * 60)
    
    import platform
    import sys
    
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"Python 版本: {sys.version}")
    print(f"HTTPX 版本: {httpx.__version__}")
    
    # 检查网络接口
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"主机名: {hostname}")
        print(f"本地 IP: {local_ip}")
    except:
        pass


async def main():
    """运行所有诊断"""
    print("🔍 网络诊断工具")
    print("=" * 60)
    print("诊断目标: https://api.dexscreener.com")
    print()
    
    # 1. 检查代理
    has_proxy = check_system_proxy()
    
    # 2. 检查 DNS
    dns_ok = check_dns()
    
    # 3. 检查 Socket
    socket_ok = check_socket_connection()
    
    # 4. 测试 HTTP 请求
    if dns_ok and socket_ok:
        http_ok = await test_httpx_without_proxy()
        
        if not http_ok:
            await test_with_different_timeout()
    
    # 5. 显示系统信息
    show_system_info()
    
    # 总结
    print("\n" + "=" * 60)
    print("📋 诊断总结")
    print("=" * 60)
    
    if has_proxy:
        print("⚠️  检测到系统代理设置")
        print("   解决方案:")
        print("   1. 在 macOS 系统偏好设置中关闭代理")
        print("   2. 或在代码中添加: trust_env=False")
    
    if not dns_ok:
        print("❌ DNS 解析失败")
        print("   解决方案: 检查网络连接和 DNS 设置")
    
    if dns_ok and not socket_ok:
        print("❌ Socket 连接失败但 DNS 正常")
        print("   解决方案: 可能是防火墙或网络限制")
    
    if dns_ok and socket_ok:
        print("✅ 基础连接正常")
        print("   如果仍然超时，尝试:")
        print("   1. 增加超时时间")
        print("   2. 检查代理设置")
        print("   3. 暂时禁用 VPN")
    
    print("\n" + "=" * 60)
    print("💡 快速修复方案")
    print("=" * 60)
    print("""
在你的代码中使用以下设置:

import os

# 禁用代理
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

async with httpx.AsyncClient(
    verify=False,          # 禁用 SSL 验证
    timeout=60.0,          # 增加超时时间
    proxies=None,          # 禁用代理
    trust_env=False        # 不信任环境变量
) as client:
    response = await client.get(url)
""")


if __name__ == "__main__":
    asyncio.run(main())

