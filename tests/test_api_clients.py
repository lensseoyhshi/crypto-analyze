"""Tests for API clients."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.api.clients.dexscreener import DexscreenerClient
from app.api.clients.birdeye import BirdeyeClient
from app.api.schemas.dexscreener import TopTokenBoostsResponse
from app.api.schemas.birdeye import TokenOverviewResponse


class TestDexscreenerClient:
	"""Test suite for Dexscreener client."""
	
	@pytest.mark.asyncio
	async def test_fetch_top_boosts(self):
		"""Test fetching top token boosts."""
		client = DexscreenerClient()
		
		# Mock response data
		mock_data = [
			{
				"url": "https://dexscreener.com/solana/test",
				"chainId": "solana",
				"tokenAddress": "TestToken123",
				"description": "Test token",
				"icon": None,
				"header": None,
				"openGraph": None,
				"links": [],
				"totalAmount": 100
			}
		]
		
		# Mock the get method
		with patch.object(client, 'get', new_callable=AsyncMock) as mock_get:
			mock_get.return_value = mock_data
			
			result = await client.fetch_top_boosts()
			
			assert isinstance(result, TopTokenBoostsResponse)
			assert len(result.items) == 1
			assert result.items[0].chainId == "solana"
			assert result.items[0].tokenAddress == "TestToken123"
			mock_get.assert_called_once_with("/token-boosts/top/v1")
		
		await client.close()


class TestBirdeyeClient:
	"""Test suite for Birdeye client."""
	
	@pytest.mark.asyncio
	async def test_get_token_overview(self):
		"""Test fetching token overview."""
		client = BirdeyeClient(api_key="test_key")
		
		# Mock response data
		mock_data = {
			"data": {
				"address": "TestToken123",
				"marketCap": 1000000.0,
				"liquidity": 500000.0,
				"price": 0.5,
				"v24h": 100000.0,
				"v24hUSD": 50000.0
			},
			"success": True
		}
		
		# Mock the get method
		with patch.object(client, 'get', new_callable=AsyncMock) as mock_get:
			mock_get.return_value = mock_data
			
			result = await client.get_token_overview("TestToken123")
			
			assert isinstance(result, TokenOverviewResponse)
			assert result.success is True
			assert result.data.address == "TestToken123"
			assert result.data.marketCap == 1000000.0
			
			mock_get.assert_called_once()
			call_args = mock_get.call_args
			assert call_args[0][0] == "/defi/token_overview"
		
		await client.close()
	
	@pytest.mark.asyncio
	async def test_birdeye_headers(self):
		"""Test that Birdeye client sends correct headers."""
		client = BirdeyeClient(api_key="test_key_123")
		
		headers = client._get_headers(chain="solana")
		
		assert headers["X-API-KEY"] == "test_key_123"
		assert headers["x-chain"] == "solana"
		assert headers["accept"] == "application/json"
		
		await client.close()

