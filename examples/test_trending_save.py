"""Test script to verify token trending data saving to database."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api.clients.birdeye import BirdeyeClient
from app.db.session import get_async_session
from app.repositories.birdeye_repository import BirdeyeRepository


async def main():
	"""Test token trending fetch and save."""
	client = BirdeyeClient()
	
	try:
		print("=" * 60)
		print("Testing Token Trending Fetch and Save")
		print("=" * 60)
		
		# Fetch trending tokens
		print("\n1. Fetching trending tokens from Birdeye API...")
		response = await client.get_token_trending(
			sort_by="rank",
			sort_type="asc",
			interval="24h",
			offset=0,
			limit=20
		)
		
		if not response.success:
			print(f"✗ Failed to fetch trending tokens: {response}")
			return
		
		print(f"✓ Successfully fetched {len(response.data.tokens)} trending tokens")
		print(f"  Total available: {response.data.total}")
		print(f"  Update time: {response.data.updateTime}")
		
		# Display first few tokens
		print("\n2. Sample of trending tokens:")
		for i, token in enumerate(response.data.tokens[:5], 1):
			print(f"   {i}. Rank #{token.rank}: {token.symbol} ({token.name})")
			print(f"      Address: {token.address}")
			print(f"      Price: ${token.price:.8f}")
			print(f"      Market Cap: ${token.marketcap:,.2f}")
			print(f"      24h Volume: ${token.volume24hUSD:,.2f}")
			if token.price24hChangePercent:
				print(f"      24h Change: {token.price24hChangePercent:.2f}%")
		
		# Save to database
		print(f"\n3. Saving {len(response.data.tokens)} tokens to database...")
		
		async for session in get_async_session():
			repo = BirdeyeRepository(session)
			count = await repo.save_or_update_token_trending_batch(response.data.tokens)
			print(f"✓ Successfully saved/updated {count} tokens to birdeye_token_trending table")
			break
		
		# Verify data in database
		print("\n4. Verifying data in database...")
		async for session in get_async_session():
			from sqlalchemy import select, func
			from app.db.models import BirdeyeTokenTrending
			
			# Count total records
			count_query = select(func.count()).select_from(BirdeyeTokenTrending)
			result = await session.execute(count_query)
			total_count = result.scalar()
			print(f"✓ Total records in birdeye_token_trending: {total_count}")
			
			# Get top 5 by rank
			query = select(BirdeyeTokenTrending).order_by(BirdeyeTokenTrending.rank).limit(5)
			result = await session.execute(query)
			top_tokens = result.scalars().all()
			
			print(f"\n5. Top 5 tokens from database:")
			for token in top_tokens:
				print(f"   Rank #{token.rank}: {token.symbol} ({token.name})")
				print(f"      Price: ${token.price:.8f}")
				print(f"      Market Cap: ${token.marketcap:,.2f}")
				print(f"      Created at: {token.created_at}")
			
			break
		
		print("\n" + "=" * 60)
		print("Test completed successfully!")
		print("=" * 60)
		
	except Exception as e:
		print(f"\n✗ Error: {str(e)}")
		import traceback
		traceback.print_exc()
	finally:
		await client.close()


if __name__ == "__main__":
	asyncio.run(main())

