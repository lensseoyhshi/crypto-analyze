"""Repository for Dexscreener data."""
import json
import logging
from datetime import datetime
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from ..db.models import DexscreenerTokenBoost
from ..api.schemas.dexscreener import TokenBoost

logger = logging.getLogger(__name__)


class DexscreenerRepository:
	"""Repository for managing Dexscreener data."""
	
	def __init__(self, session: AsyncSession):
		self.session = session
	
	async def save_token_boost(self, token_boost: TokenBoost) -> DexscreenerTokenBoost:
		"""Save a single token boost."""
		try:
			# Convert links to JSON string
			links_json = None
			if token_boost.links:
				links_json = json.dumps([link.dict() for link in token_boost.links])
			
			db_boost = DexscreenerTokenBoost(
				chainId=token_boost.chainId,
				tokenAddress=token_boost.tokenAddress,
				url=token_boost.url,
				description=token_boost.description,
				icon=token_boost.icon,
				header=token_boost.header,
				openGraph=token_boost.openGraph,
				links=links_json,
				totalAmount=token_boost.totalAmount,
				created_at=datetime.utcnow()
			)
			
			self.session.add(db_boost)
			await self.session.commit()
			await self.session.refresh(db_boost)
			
			logger.debug(f"Saved token boost: {token_boost.tokenAddress}")
			return db_boost
			
		except Exception as e:
			await self.session.rollback()
			logger.error(f"Error saving token boost: {str(e)}")
			raise
	
	async def save_token_boosts_batch(self, token_boosts: List[TokenBoost]) -> int:
		"""Save multiple token boosts in batch."""
		try:
			saved_count = 0
			for boost in token_boosts:
				await self.save_token_boost(boost)
				saved_count += 1
			
			logger.info(f"Saved {saved_count} token boosts")
			return saved_count
			
		except Exception as e:
			logger.error(f"Error in batch save: {str(e)}")
			raise
	
	async def get_latest_boosts(self, limit: int = 10) -> List[DexscreenerTokenBoost]:
		"""Get latest token boosts."""
		query = select(DexscreenerTokenBoost).order_by(
			desc(DexscreenerTokenBoost.created_at)
		).limit(limit)
		
		result = await self.session.execute(query)
		return list(result.scalars().all())
	
	async def get_boosts_by_token(
		self,
		token_address: str,
		limit: int = 10
	) -> List[DexscreenerTokenBoost]:
		"""Get boosts for a specific token."""
		query = select(DexscreenerTokenBoost).where(
			DexscreenerTokenBoost.tokenAddress == token_address
		).order_by(desc(DexscreenerTokenBoost.created_at)).limit(limit)
		
		result = await self.session.execute(query)
		return list(result.scalars().all())

