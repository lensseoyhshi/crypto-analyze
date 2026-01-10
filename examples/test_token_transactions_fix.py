"""Test script to verify the token transactions API fix."""
import asyncio
import time
from app.api.clients.birdeye import BirdeyeClient


async def main():
	"""Test token transactions endpoint with proper parameters."""
	client = BirdeyeClient()
	
	try:
		# Test token address from your curl example
		token_address = "7bHqvoRYbkKPJXoEngC7p4EXzXq2dQNkwBopGbNEpx1y"
		
		# Get current time for before_time (fetch recent transactions)
		current_time = int(time.time())
		
		print(f"Testing token transactions for: {token_address}")
		print(f"Current timestamp: {current_time}\n")
		
		# Test 1: Basic request with before_time (like your curl)
		print("=" * 60)
		print("Test 1: Fetching transactions with before_time parameter")
		print("=" * 60)
		
		response = await client.get_token_transactions(
			token_address=token_address,
			offset=0,
			limit=20,
			tx_type="swap",
			before_time=current_time,
			ui_amount_mode="scaled"
		)
		
		if response.success:
			print(f"✓ Success! Fetched {len(response.data.items)} transactions")
			print(f"  Total items: {response.data.total}")
			
			# Display first transaction
			if response.data.items:
				first_tx = response.data.items[0]
				print(f"\nFirst transaction:")
				print(f"  - Tx Hash: {first_tx.txHash}")
				print(f"  - Block Time: {first_tx.blockUnixTime}")
				print(f"  - Owner: {first_tx.owner[:20]}...")
				if hasattr(first_tx, 'source') and first_tx.source:
					print(f"  - Source: {first_tx.source}")
		else:
			print(f"✗ Failed: {response}")
		
		# Test 2: Request without time parameters (should auto-use current time)
		print("\n" + "=" * 60)
		print("Test 2: Fetching transactions without time parameters")
		print("       (Should automatically use current time as before_time)")
		print("=" * 60)
		
		response2 = await client.get_token_transactions(
			token_address=token_address,
			offset=0,
			limit=10,
			tx_type="swap"
		)
		
		if response2.success:
			print(f"✓ Success! Fetched {len(response2.data.items)} transactions")
			print(f"  Total items: {response2.data.total}")
		else:
			print(f"✗ Failed: {response2}")
		
		# Test 3: Different token (DezXAZ8z7... from your error log)
		print("\n" + "=" * 60)
		print("Test 3: Fetching transactions for another token")
		print("=" * 60)
		
		token_address2 = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
		response3 = await client.get_token_transactions(
			token_address=token_address2,
			offset=0,
			limit=20,
			tx_type="swap",
			before_time=current_time
		)
		
		if response3.success:
			print(f"✓ Success! Fetched {len(response3.data.items)} transactions")
			print(f"  Total items: {response3.data.total}")
		else:
			print(f"✗ Failed: {response3}")
		
		print("\n" + "=" * 60)
		print("All tests completed!")
		print("=" * 60)
		
	except Exception as e:
		print(f"Error: {str(e)}")
		import traceback
		traceback.print_exc()
	finally:
		await client.close()


if __name__ == "__main__":
	asyncio.run(main())

