"""Repository for raw API responses."""
import json
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db.models import RawApiResponse

logger = logging.getLogger(__name__)


class RawApiRepository:
	"""Repository for managing raw API responses in the database."""

	def __init__(self, session: AsyncSession):
		"""
		Initialize repository with database session.
		
		Args:
			session: SQLAlchemy async session
		"""
		self.session = session

	async def save_response(
		self,
		endpoint: str,
		source: str,
		response_data: dict,
		status_code: int = 200,
		error_message: Optional[str] = None
	) -> RawApiResponse:
		"""
		Save a raw API response to the database.
		
		Args:
			endpoint: API endpoint path
			source: API source (e.g., "dexscreener", "birdeye")
			response_data: The JSON response data as dict
			status_code: HTTP status code
			error_message: Optional error message if request failed
			
		Returns:
			RawApiResponse: The saved database record
		"""
		try:
			raw_response = RawApiResponse(
				endpoint=endpoint,
				source=source,
				response_json=json.dumps(response_data),
				status_code=status_code,
				error_message=error_message,
				created_at=datetime.utcnow()
			)
			
			self.session.add(raw_response)
			await self.session.commit()
			await self.session.refresh(raw_response)
			
			logger.info(f"Saved API response: source={source}, endpoint={endpoint}, id={raw_response.id}")
			return raw_response
			
		except Exception as e:
			await self.session.rollback()
			logger.error(f"Error saving API response: {str(e)}")
			raise

	async def get_latest_by_source(
		self,
		source: str,
		endpoint: Optional[str] = None,
		limit: int = 1
	) -> list[RawApiResponse]:
		"""
		Get latest responses by source and optionally endpoint.
		
		Args:
			source: API source to filter by
			endpoint: Optional endpoint to filter by
			limit: Maximum number of records to return
			
		Returns:
			List of RawApiResponse records
		"""
		query = select(RawApiResponse).where(RawApiResponse.source == source)
		
		if endpoint:
			query = query.where(RawApiResponse.endpoint == endpoint)
		
		query = query.order_by(RawApiResponse.created_at.desc()).limit(limit)
		
		result = await self.session.execute(query)
		return result.scalars().all()

	async def count_by_source(self, source: str) -> int:
		"""
		Count total responses by source.
		
		Args:
			source: API source to count
			
		Returns:
			Total count of responses
		"""
		from sqlalchemy import func
		query = select(func.count(RawApiResponse.id)).where(RawApiResponse.source == source)
		result = await self.session.execute(query)
		return result.scalar() or 0

