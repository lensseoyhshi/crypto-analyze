"""
Birdeye Token Trending API Demo

This script demonstrates how to fetch trending/hot tokens from Birdeye API.
获取热门/趋势代币数据的演示脚本。

新增功能：测试数据库插入操作
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.api.clients.birdeye import BirdeyeClient
from app.db.session import AsyncSessionLocal
from app.repositories.birdeye_repository import BirdeyeRepository


async def main():
    """Main demo function."""
    client = BirdeyeClient()
    
    try:
        print("=" * 80)
        print("Birdeye Token Trending API Demo - 带数据库插入测试")
        print("获取Birdeye热门代币趋势数据并测试数据入库")
        print("=" * 80)
        print()
        
        # Fetch first page of trending tokens
        print("📊 Fetching trending tokens (first 20)...")
        print("-" * 80)
        response = await client.get_token_trending(
            sort_by="rank",
            sort_type="asc",
            interval="24h",
            offset=0,
            limit=20
        )
        
        if response.success:
            print(f"✅ Success! Found {response.data.total} total trending tokens")
            print(f"📅 Update Time: {response.data.updateTime}")
            print(f"⏰ Unix Time: {response.data.updateUnixTime}")
            print()
            
            print(f"Showing top {len(response.data.tokens)} tokens:")
            print("-" * 80)
            
            for token in response.data.tokens[:10]:  # Show top 10
                print(f"\n🏆 Rank #{token.rank}: {token.symbol} ({token.name})")
                print(f"   Address: {token.address}")
                print(f"   Price: ${token.price:,.10f}")
                print(f"   Market Cap: ${token.marketcap:,.2f}")
                print(f"   FDV: ${token.fdv:,.2f}")
                print(f"   Liquidity: ${token.liquidity:,.2f}")
                print(f"   24h Volume: ${token.volume24hUSD:,.2f}")
                print(f"   24h Price Change: {token.price24hChangePercent:+.2f}%")
                print(f"   24h Volume Change: {token.volume24hChangePercent:+.2f}%")
                
                if token.logoURI:
                    print(f"   Logo: {token.logoURI[:60]}...")
            
            print()
            print("=" * 80)
            
            # 新增：测试数据库插入操作
            print("\n💾 Testing database insertion...")
            print("-" * 80)
            
            async with AsyncSessionLocal() as session:
                repository = BirdeyeRepository(session)
                
                # 保存前 10 条数据到数据库
                saved_count = await repository.save_or_update_token_trending_batch(
                    response.data.tokens[:10]
                )
                
                print(f"✅ Successfully saved {saved_count}/{len(response.data.tokens[:10])} trending tokens to database!")
            
            print()
            print("=" * 80)
            
            # Example: Fetch second page
            print("\n📊 Fetching next page (offset=20)...")
            print("-" * 80)
            response2 = await client.get_token_trending(
                sort_by="rank",
                sort_type="asc",
                interval="24h",
                offset=20,
                limit=20
            )
            
            if response2.success:
                print(f"✅ Got {len(response2.data.tokens)} more tokens")
                for token in response2.data.tokens[:5]:  # Show first 5
                    print(f"   Rank #{token.rank}: {token.symbol} - ${token.price:,.10f}")
                
                # 新增：测试保存第二页数据
                print("\n💾 Saving second page to database...")
                async with AsyncSessionLocal() as session:
                    repository = BirdeyeRepository(session)
                    saved_count2 = await repository.save_or_update_token_trending_batch(
                        response2.data.tokens[:5]
                    )
                    print(f"✅ Successfully saved {saved_count2}/{len(response2.data.tokens[:5])} tokens from second page!")
            
            print()
            print("=" * 80)
            print("✨ Demo completed successfully! 数据已成功入库！")
            print("=" * 80)
            
        else:
            print("❌ Failed to fetch trending tokens")
            print(f"Response: {response}")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

