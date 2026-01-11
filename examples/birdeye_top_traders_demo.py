"""
Birdeye Top Traders API Demo

This script demonstrates how to fetch top traders for a specific token from Birdeye API.
演示如何获取代币的 top traders 数据，包括分页获取。
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.api.clients.birdeye import BirdeyeClient


async def fetch_all_top_traders(client: BirdeyeClient, token_address: str, time_frame: str = "24h", max_traders: int = 50):
    """
    Fetch all top traders with pagination.
    
    Args:
        client: BirdeyeClient instance
        token_address: Token address to query
        time_frame: Time frame for analysis
        max_traders: Maximum number of traders to fetch
        
    Returns:
        List of all traders
    """
    all_traders = []
    offset = 0
    limit = 10  # API max limit per request
    max_pages = (max_traders + limit - 1) // limit
    
    print(f"📊 Fetching up to {max_traders} top traders with pagination...")
    
    for page in range(max_pages):
        print(f"   Fetching page {page + 1}... (offset={offset})")
        
        response = await client.get_top_traders(
            token_address=token_address,
            time_frame=time_frame,
            sort_by="volume",
            sort_type="desc",
            offset=offset,
            limit=limit
        )
        
        if response.success and response.data.items:
            all_traders.extend(response.data.items)
            print(f"   ✅ Got {len(response.data.items)} traders")
            
            # 如果返回的数量少于 limit，说明已经到最后一页了
            if len(response.data.items) < limit:
                print(f"   ℹ️  Reached last page")
                break
            
            offset += limit
            await asyncio.sleep(0.3)  # Rate limiting
        else:
            print(f"   ⚠️  No more traders at offset {offset}")
            break
    
    print(f"✅ Total fetched: {len(all_traders)} traders\n")
    return all_traders


async def main():
    """Main demo function."""
    client = BirdeyeClient()
    
    # 示例：SOL 代币地址
    token_address = "So11111111111111111111111111111111111111112"
    
    try:
        print("=" * 80)
        print("Birdeye Top Traders API Demo - With Pagination Support")
        print("获取代币 Top Traders 数据演示 - 支持分页")
        print("=" * 80)
        print()
        
        # 示例 1: 单页获取前 10 个交易者
        print("📊 Example 1: Single page - Top 10 traders by volume (24h)...")
        print("-" * 80)
        response = await client.get_top_traders(
            token_address=token_address,
            time_frame="24h",
            sort_by="volume",
            sort_type="desc",
            limit=10
        )
        
        if response.success:
            print(f"✅ Success! Found {len(response.data.items)} top traders")
            print()
            
            for i, trader in enumerate(response.data.items[:5], 1):  # Show top 5
                print(f"\n🏆 Rank #{i}: {trader.owner}")
                print(f"   Type: {trader.type}")
                print(f"   Total Volume: ${trader.volume:,.2f}")
                print(f"   Total Trades: {trader.trade}")
                print(f"   Buy Trades: {trader.tradeBuy} (${trader.volumeBuy:,.2f})")
                print(f"   Sell Trades: {trader.tradeSell} (${trader.volumeSell:,.2f})")
                
                if trader.tags:
                    print(f"   Tags: {trader.tags}")
        else:
            print("❌ Failed to fetch top traders")
        
        print()
        print("=" * 80)
        
        # 示例 2: 分页获取多个交易者
        print("\n📊 Example 2: Pagination - Fetching up to 30 traders...")
        print("-" * 80)
        
        all_traders = await fetch_all_top_traders(
            client, 
            token_address, 
            time_frame="24h", 
            max_traders=30
        )
        
        if all_traders:
            print(f"📈 Statistics from {len(all_traders)} traders:")
            print(f"   Total Volume: ${sum(t.volume for t in all_traders):,.2f}")
            print(f"   Total Trades: {sum(t.trade for t in all_traders):,}")
            print(f"   Average Volume per Trader: ${sum(t.volume for t in all_traders) / len(all_traders):,.2f}")
            
            # 显示前 3 名和后 3 名
            print(f"\n   Top 3:")
            for i, trader in enumerate(all_traders[:3], 1):
                print(f"   #{i}: ${trader.volume:,.2f} ({trader.trade} trades)")
            
            print(f"\n   Bottom 3:")
            for i, trader in enumerate(all_traders[-3:], len(all_traders) - 2):
                print(f"   #{i}: ${trader.volume:,.2f} ({trader.trade} trades)")
        
        print()
        print("=" * 80)
        
        # 示例 3: 按交易次数排序并分页
        print("\n📊 Example 3: Pagination by trade count (24h)...")
        print("-" * 80)
        
        traders_by_trade = []
        offset = 0
        limit = 10
        
        for page in range(2):  # 获取 2 页
            response = await client.get_top_traders(
                token_address=token_address,
                time_frame="24h",
                sort_by="trade",  # 按交易次数排序
                sort_type="desc",
                offset=offset,
                limit=limit
            )
            
            if response.success and response.data.items:
                traders_by_trade.extend(response.data.items)
                print(f"   Page {page + 1}: Got {len(response.data.items)} traders")
                offset += limit
                await asyncio.sleep(0.3)
            else:
                break
        
        if traders_by_trade:
            print(f"\n✅ Total: {len(traders_by_trade)} traders sorted by trade count")
            print(f"\n   Top 5 by trade count:")
            for i, trader in enumerate(traders_by_trade[:5], 1):
                avg_per_trade = trader.volume / trader.trade if trader.trade > 0 else 0
                print(f"   #{i}: {trader.trade} trades, ${trader.volume:,.2f} volume (avg ${avg_per_trade:,.2f}/trade)")
        
        print()
        print("=" * 80)
        print("✨ Demo completed successfully!")
        print("=" * 80)
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

