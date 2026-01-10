"""
Test Token Trending Functionality
测试 Token Trending 功能
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.api.clients.birdeye import BirdeyeClient
from app.db.session import get_async_session
from app.repositories.birdeye_repository import BirdeyeRepository


async def test_api_client():
    """Test API client."""
    print("=" * 80)
    print("Test 1: API Client")
    print("=" * 80)
    
    client = BirdeyeClient()
    try:
        response = await client.get_token_trending(offset=0, limit=5)
        
        if response.success:
            print(f"✅ API Call Success")
            print(f"   Total tokens: {response.data.total}")
            print(f"   Fetched: {len(response.data.tokens)}")
            print(f"   Update time: {response.data.updateTime}")
            return True
        else:
            print(f"❌ API Call Failed")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    finally:
        await client.close()


async def test_repository():
    """Test repository save/update."""
    print("\n" + "=" * 80)
    print("Test 2: Repository Save/Update")
    print("=" * 80)
    
    client = BirdeyeClient()
    try:
        # Fetch data
        response = await client.get_token_trending(offset=0, limit=5)
        
        if not response.success:
            print("❌ Failed to fetch data")
            return False
        
        # Save to database
        async for session in get_async_session():
            repo = BirdeyeRepository(session)
            
            # Test save/update
            count = await repo.save_or_update_token_trending_batch(
                response.data.tokens
            )
            
            print(f"✅ Saved/Updated {count} tokens")
            
            # Verify data
            for token in response.data.tokens[:3]:
                print(f"   - {token.symbol} (Rank #{token.rank}): ${token.price:.10f}")
            
            return True
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.close()


async def test_pagination():
    """Test pagination logic."""
    print("\n" + "=" * 80)
    print("Test 3: Pagination")
    print("=" * 80)
    
    client = BirdeyeClient()
    try:
        total_fetched = 0
        
        for page in range(3):  # Test 3 pages
            offset = page * 20
            response = await client.get_token_trending(offset=offset, limit=20)
            
            if response.success and response.data.tokens:
                fetched = len(response.data.tokens)
                total_fetched += fetched
                print(f"✅ Page {page + 1}: Fetched {fetched} tokens (offset={offset})")
                
                # Show first token of each page
                if response.data.tokens:
                    first = response.data.tokens[0]
                    print(f"   First: Rank #{first.rank} - {first.symbol}")
            else:
                print(f"⚠️  Page {page + 1}: No more data")
                break
            
            await asyncio.sleep(0.5)  # Rate limiting
        
        print(f"\n📊 Total fetched across {page + 1} pages: {total_fetched} tokens")
        return True
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    finally:
        await client.close()


async def main():
    """Run all tests."""
    print("\n" + "🚀" * 40)
    print("Token Trending Functionality Tests")
    print("🚀" * 40 + "\n")
    
    results = []
    
    # Test 1: API Client
    results.append(await test_api_client())
    
    # Test 2: Repository
    results.append(await test_repository())
    
    # Test 3: Pagination
    results.append(await test_pagination())
    
    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed!")
    else:
        print(f"❌ {total - passed} test(s) failed")
    
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

