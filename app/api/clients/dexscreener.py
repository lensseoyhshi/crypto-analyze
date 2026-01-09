"""Dexscreener API client."""
import logging
from .base_client import BaseApiClient
from ..schemas.dexscreener import TopTokenBoostsResponse

logger = logging.getLogger(__name__)


class DexscreenerClient(BaseApiClient):
	"""Client for Dexscreener endpoints."""

	def __init__(self):
		super().__init__(base_url="https://api.dexscreener.com", timeout=30)

	async def fetch_top_boosts(self) -> TopTokenBoostsResponse:
		"""
		Fetch top token boosts from Dexscreener.
		
		Returns:
			TopTokenBoostsResponse: Parsed response with list of token boosts
		"""
		logger.info("Fetching top token boosts from Dexscreener")
		data = await self.get("/token-boosts/top/v1")
		return TopTokenBoostsResponse.from_list(data)


