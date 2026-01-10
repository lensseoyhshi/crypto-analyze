"""
Test Birdeye New Listings API Fix
测试新上币API修复
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.api.clients.birdeye import BirdeyeClient


async def test_new_listings_with_params():
    """Test new listings API with all required parameters."""
    client = BirdeyeClient()
    
    try:
        print("=" * 80)
        print("Testing Birdeye New Listings API (修复后)")
        print("=" * 80)
        print()
        
        # Test 1: With all parameters (like the working curl command)
        print("📊 Test 1: Fetching new listings with all parameters...")
        print("-" * 80)
        response = await client.get_new_listings(
            sort_by="liquidity",
            sort_type="desc",
            offset=0,
            limit=10
        )
        
        if response.success:
            print(f"✅ Success! Found {len(response.data.items)} new listings")
            print()
            
            for i, listing in enumerate(response.data.items[:5], 1):
                print(f"{i}. {listing.symbol} ({listing.name})")
                print(f"   Address: {listing.address}")
                print(f"   Liquidity: ${listing.liquidity:,.2f}")
                print(f"   Source: {listing.source}")
                print(f"   Added At: {listing.liquidityAddedAt}")
                print()
        else:
            print(f"❌ Failed to fetch new listings")
            print(f"Response: {response}")
        
        print("=" * 80)
        print()
        
        # Test 2: Different sorting
        print("📊 Test 2: Fetching new listings sorted by different field...")
        print("-" * 80)
        response2 = await client.get_new_listings(
            sort_by="liquidity",
            sort_type="asc",
            offset=0,
            limit=5
        )
        
        if response2.success:
            print(f"✅ Success! Found {len(response2.data.items)} listings (ascending)")
            for listing in response2.data.items:
                print(f"   - {listing.symbol}: ${listing.liquidity:,.2f}")
        else:
            print(f"❌ Failed")
        
        print()
        print("=" * 80)
        print("✨ All tests completed!")
        print("=" * 80)
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.close()


async def test_original_params():
    """Test with original parameters (should now work)."""
    client = BirdeyeClient()
    
    try:
        print("\n" + "=" * 80)
        print("Testing Original Method Call (应该现在能工作了)")
        print("=" * 80)
        print()
        
        # This is what the scheduler calls
        response = await client.get_new_listings(limit=50)
        
        if response.success:
            print(f"✅ Success! Scheduler call now works properly")
            print(f"   Found {len(response.data.items)} new listings")
        else:
            print(f"❌ Still failing")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    finally:
        await client.close()


async def main():
    """Run all tests."""
    print("\n" + "🚀" * 40)
    print("Birdeye New Listings API Fix Verification")
    print("🚀" * 40 + "\n")
    
    await test_new_listings_with_params()
    await test_original_params()


if __name__ == "__main__":
    asyncio.run(main())

