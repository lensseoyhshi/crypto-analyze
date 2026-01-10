#!/usr/bin/env python3
"""
Dexscreener API 请求示例（正确且安全的方式）
"""

import httpx
import asyncio
import ssl
import certifi


async def simple_request():
    """
    正确的异步请求示例
    - 启用 SSL 验证（安全）
    - 遵循系统代理设置
    - 使用正确的证书配置
    """
    url = "https://api.dexscreener.com/token-boosts/top/v1"
    
    try:
        # 创建客户端（使用安全的配置）
        async with httpx.AsyncClient(
            verify=True,      # ✅ 启用 SSL 验证（安全）
            timeout=30.0,     # 30 秒超时
            # trust_env=True 是默认值，会使用系统代理设置（如果有）
        ) as client:
            print(f"正在请求: {url}")
            
            # 发送请求
            response = await client.get(url)
            
            # 检查状态
            response.raise_for_status()
            
            # 解析 JSON
            data = response.json()
            
            # 打印结果
            print(f"\n✅ 成功获取 {len(data)} 个代币")
            
            # 打印前 3 个
            for i, item in enumerate(data[:3], 1):
                print(f"\n{i}. {item['description']}")
                print(f"   链: {item['chainId']}")
                print(f"   地址: {item['tokenAddress']}")
                print(f"   Boost: {item['totalAmount']}")
                print(f"   链接: {item['url']}")
            
            return data
            
    except ssl.SSLError as e:
        print(f"\n❌ SSL 证书错误: {e}")
        print("\n💡 解决方案:")
        print("   1. 运行: pip install --upgrade certifi")
        print("   2. 运行证书安装脚本:")
        print("      /Applications/Python\\ 3.10/Install\\ Certificates.command")
        print(f"\n当前证书路径: {certifi.where()}")
        
    except httpx.ConnectTimeout:
        print(f"\n❌ 连接超时")
        print("\n💡 可能原因:")
        print("   1. 网络不稳定")
        print("   2. 防火墙阻止连接")
        print("   3. 如果使用代理，检查代理配置")
        
    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP 错误: {e.response.status_code}")
        print(f"响应内容: {e.response.text}")
        
    except Exception as e:
        print(f"\n❌ 未知错误: {e}")
        print(f"错误类型: {type(e).__name__}")


# 运行
if __name__ == "__main__":
    print("🔒 Dexscreener API 请求示例（安全模式）")
    print("=" * 60)
    asyncio.run(simple_request())
    print("\n" + "=" * 60)
    print("✅ 完成!")

