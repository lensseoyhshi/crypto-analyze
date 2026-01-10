#!/usr/bin/env python3
"""
正确的网络连接测试（不禁用 SSL 和代理）
"""

import httpx
import asyncio
import certifi
import ssl
import os


def check_ssl_config():
    """检查 SSL 配置"""
    print("=" * 60)
    print("1. SSL 配置检查")
    print("=" * 60)
    
    # certifi 证书路径
    cert_path = certifi.where()
    print(f"Certifi 证书: {cert_path}")
    print(f"证书文件存在: {os.path.exists(cert_path)}")
    
    # SSL 默认路径
    paths = ssl.get_default_verify_paths()
    print(f"\nSSL CA 文件: {paths.openssl_cafile}")
    print(f"SSL CA 路径: {paths.openssl_capath}")
    
    print()


async def test_with_ssl():
    """使用完整 SSL 验证测试"""
    print("=" * 60)
    print("2. 测试 HTTPS 连接（启用 SSL 验证）")
    print("=" * 60)
    
    url = "https://api.dexscreener.com/token-boosts/top/v1"
    
    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            verify=True  # 启用 SSL 验证
        ) as client:
            print(f"连接: {url}")
            response = await client.get(url)
            response.raise_for_status()
            
            data = response.json()
            print(f"\n✅ 成功!")
            print(f"状态码: {response.status_code}")
            print(f"数据量: {len(data)} 个代币")
            
            if data:
                first = data[0]
                print(f"\n第一个代币:")
                print(f"  {first.get('description')}")
                print(f"  链: {first.get('chainId')}")
                print(f"  地址: {first.get('tokenAddress')[:20]}...")
            
            return True
            
    except ssl.SSLError as e:
        print(f"\n❌ SSL 错误: {e}")
        print("\n💡 解决方案:")
        print("   1. pip install --upgrade certifi")
        print("   2. /Applications/Python\\ 3.10/Install\\ Certificates.command")
        return False
        
    except httpx.ConnectTimeout:
        print("\n❌ 连接超时")
        print("\n💡 可能原因:")
        print("   1. 网络问题")
        print("   2. 防火墙阻止")
        print("   3. 代理配置不正确")
        return False
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        return False


async def main():
    """运行测试"""
    print("🔒 正确的 SSL 和网络测试")
    print()
    
    check_ssl_config()
    success = await test_with_ssl()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 测试通过! SSL 和网络配置正确。")
        print("=" * 60)
        print("\n现在可以启动项目:")
        print("  uvicorn app.main:app --reload")
    else:
        print("❌ 测试失败")
        print("=" * 60)
        print("\n请按照上述提示修复问题。")
        print("详细说明请查看: 正确的SSL和网络配置.md")
    print()


if __name__ == "__main__":
    asyncio.run(main())

