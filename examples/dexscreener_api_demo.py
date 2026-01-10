#!/usr/bin/env python3
"""
Dexscreener API 请求示例
API 文档: https://docs.dexscreener.com/api/reference
"""

import asyncio
import httpx
import requests
from pprint import pprint


# ============================================================================
# 方式 1: 使用 httpx 异步（推荐 - 项目使用的方式）
# ============================================================================

async def fetch_with_httpx_async():
    """使用 httpx 异步请求"""
    print("=" * 60)
    print("方式 1: httpx 异步请求")
    print("=" * 60)
    
    url = "https://api.dexscreener.com/token-boosts/top/v1"
    
    async with httpx.AsyncClient(verify=False) as client:  # verify=False 临时禁用SSL
        try:
            response = await client.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            print(f"✅ 请求成功!")
            print(f"状态码: {response.status_code}")
            print(f"返回数据数量: {len(data)}")
            print(f"\n前 3 个代币:")
            
            for i, item in enumerate(data[:3], 1):
                print(f"\n{i}. {item.get('description', 'No description')}")
                print(f"   Token: {item.get('tokenAddress')}")
                print(f"   Chain: {item.get('chainId')}")
                print(f"   Total Amount: {item.get('totalAmount')}")
                print(f"   URL: {item.get('url')}")
            
            return data
            
        except httpx.HTTPError as e:
            print(f"❌ HTTP 错误: {e}")
        except Exception as e:
            print(f"❌ 其他错误: {e}")


# ============================================================================
# 方式 2: 使用 httpx 同步（简单但阻塞）
# ============================================================================

def fetch_with_httpx_sync():
    """使用 httpx 同步请求"""
    print("\n" + "=" * 60)
    print("方式 2: httpx 同步请求")
    print("=" * 60)
    
    url = "https://api.dexscreener.com/token-boosts/top/v1"
    
    try:
        response = httpx.get(url, verify=False, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        print(f"✅ 请求成功!")
        print(f"状态码: {response.status_code}")
        print(f"返回数据数量: {len(data)}")
        
        return data
        
    except httpx.HTTPError as e:
        print(f"❌ HTTP 错误: {e}")
    except Exception as e:
        print(f"❌ 其他错误: {e}")


# ============================================================================
# 方式 3: 使用 requests（最常见的库）
# ============================================================================

def fetch_with_requests():
    """使用 requests 请求"""
    print("\n" + "=" * 60)
    print("方式 3: requests 请求")
    print("=" * 60)
    
    url = "https://api.dexscreener.com/token-boosts/top/v1"
    
    try:
        response = requests.get(url, verify=False, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        print(f"✅ 请求成功!")
        print(f"状态码: {response.status_code}")
        print(f"返回数据数量: {len(data)}")
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求错误: {e}")
    except Exception as e:
        print(f"❌ 其他错误: {e}")


# ============================================================================
# 方式 4: 使用项目中的 DexscreenerClient（最佳实践）
# ============================================================================

async def fetch_with_project_client():
    """使用项目中的 DexscreenerClient"""
    print("\n" + "=" * 60)
    print("方式 4: 使用项目的 DexscreenerClient")
    print("=" * 60)
    
    # 需要在项目目录中运行
    try:
        import sys
        from pathlib import Path
        
        # 添加项目路径
        project_root = Path(__file__).parent
        sys.path.insert(0, str(project_root))
        
        from app.api.clients.dexscreener import DexscreenerClient
        
        client = DexscreenerClient()
        
        try:
            response = await client.fetch_top_boosts()
            
            print(f"✅ 请求成功!")
            print(f"返回数据数量: {len(response.items)}")
            
            print(f"\n前 3 个代币:")
            for i, item in enumerate(response.items[:3], 1):
                print(f"\n{i}. {item.description}")
                print(f"   Token: {item.tokenAddress}")
                print(f"   Chain: {item.chainId}")
                print(f"   Total Amount: {item.totalAmount}")
            
            return response
            
        finally:
            await client.close()
            
    except ImportError:
        print("❌ 无法导入项目模块，请在项目目录中运行")
    except Exception as e:
        print(f"❌ 错误: {e}")


# ============================================================================
# 方式 5: 使用 curl 命令（终端）
# ============================================================================

def show_curl_command():
    """显示 curl 命令"""
    print("\n" + "=" * 60)
    print("方式 5: 使用 curl 命令（在终端运行）")
    print("=" * 60)
    
    curl_cmd = """
# 基本请求
curl "https://api.dexscreener.com/token-boosts/top/v1"

# 格式化输出（需要安装 jq）
curl "https://api.dexscreener.com/token-boosts/top/v1" | jq '.[0:3]'

# 保存到文件
curl "https://api.dexscreener.com/token-boosts/top/v1" -o output.json

# 显示请求头
curl -v "https://api.dexscreener.com/token-boosts/top/v1"

# 忽略 SSL 证书验证（临时）
curl -k "https://api.dexscreener.com/token-boosts/top/v1"
"""
    
    print(curl_cmd)


# ============================================================================
# 完整示例：带错误处理和重试
# ============================================================================

async def fetch_with_retry():
    """带重试机制的请求"""
    print("\n" + "=" * 60)
    print("完整示例：带重试机制")
    print("=" * 60)
    
    url = "https://api.dexscreener.com/token-boosts/top/v1"
    max_retries = 3
    
    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                print(f"尝试 {attempt}/{max_retries}...")
                
                response = await client.get(url)
                response.raise_for_status()
                
                data = response.json()
                
                print(f"✅ 成功! 获取到 {len(data)} 个代币")
                
                # 数据结构示例
                if data:
                    print("\n数据结构示例:")
                    print("=" * 40)
                    pprint(data[0], depth=2)
                
                return data
                
        except httpx.TimeoutException:
            print(f"⏱️ 超时，重试中...")
            if attempt == max_retries:
                print("❌ 达到最大重试次数")
                return None
            await asyncio.sleep(2 ** attempt)  # 指数退避
            
        except httpx.HTTPError as e:
            print(f"❌ HTTP 错误: {e}")
            return None
            
        except Exception as e:
            print(f"❌ 未知错误: {e}")
            return None


# ============================================================================
# 数据解析示例
# ============================================================================

async def parse_response_example():
    """解析响应数据的示例"""
    print("\n" + "=" * 60)
    print("数据解析示例")
    print("=" * 60)
    
    url = "https://api.dexscreener.com/token-boosts/top/v1"
    
    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
        response = await client.get(url)
        data = response.json()
        
        if not data:
            print("❌ 没有数据")
            return
        
        print(f"\n📊 统计信息:")
        print(f"   总代币数: {len(data)}")
        
        # 按链分组
        chains = {}
        for item in data:
            chain = item.get('chainId', 'unknown')
            chains[chain] = chains.get(chain, 0) + 1
        
        print(f"\n🔗 链分布:")
        for chain, count in sorted(chains.items(), key=lambda x: x[1], reverse=True):
            print(f"   {chain}: {count} 个代币")
        
        # 找出 totalAmount 最高的
        top_boost = max(data, key=lambda x: x.get('totalAmount', 0))
        print(f"\n🔥 Boost 最高的代币:")
        print(f"   描述: {top_boost.get('description')}")
        print(f"   地址: {top_boost.get('tokenAddress')}")
        print(f"   Total Amount: {top_boost.get('totalAmount')}")
        print(f"   URL: {top_boost.get('url')}")
        
        # 链接统计
        print(f"\n🔗 社交链接统计:")
        link_types = {}
        for item in data:
            for link in item.get('links', []):
                link_type = link.get('type', 'unknown')
                link_types[link_type] = link_types.get(link_type, 0) + 1
        
        for link_type, count in sorted(link_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   {link_type}: {count}")


# ============================================================================
# 主函数
# ============================================================================

async def main():
    """运行所有示例"""
    print("🚀 Dexscreener API 请求示例")
    print("=" * 60)
    
    # 禁用 SSL 警告（仅示例）
    import warnings
    warnings.filterwarnings('ignore')
    
    # 运行示例
    await fetch_with_httpx_async()
    fetch_with_httpx_sync()
    fetch_with_requests()
    show_curl_command()
    await fetch_with_retry()
    await parse_response_example()
    
    # 项目客户端（可选）
    # await fetch_with_project_client()
    
    print("\n" + "=" * 60)
    print("✅ 所有示例运行完成!")
    print("=" * 60)


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())

