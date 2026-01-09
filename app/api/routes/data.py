"""API routes for querying collected data."""
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.session import get_async_session
from ...repositories.raw_api_repository import RawApiRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/responses")
async def get_responses(
	source: Optional[str] = Query(None, description="Filter by API source (e.g., 'dexscreener', 'birdeye')"),
	endpoint: Optional[str] = Query(None, description="Filter by endpoint path"),
	limit: int = Query(10, ge=1, le=100, description="Number of results to return"),
	session: AsyncSession = Depends(get_async_session)
):
	"""
	Get collected API responses.
	
	Returns the latest API responses stored in the database.
	"""
	repository = RawApiRepository(session)
	
	if source:
		responses = await repository.get_latest_by_source(
			source=source,
			endpoint=endpoint,
			limit=limit
		)
	else:
		# If no source specified, get latest from all sources
		from sqlalchemy import select
		from ...db.models import RawApiResponse
		
		query = select(RawApiResponse).order_by(
			RawApiResponse.created_at.desc()
		).limit(limit)
		
		result = await session.execute(query)
		responses = result.scalars().all()
	
	# Format response
	return {
		"count": len(responses),
		"items": [
			{
				"id": r.id,
				"source": r.source,
				"endpoint": r.endpoint,
				"status_code": r.status_code,
				"error_message": r.error_message,
				"created_at": r.created_at.isoformat(),
				"data": json.loads(r.response_json) if r.response_json else None
			}
			for r in responses
		]
	}


@router.get("/stats")
async def get_stats(
	session: AsyncSession = Depends(get_async_session)
):
	"""
	Get statistics about collected data.
	
	Returns counts and summary information for all collected API responses.
	"""
	repository = RawApiRepository(session)
	
	# Get counts by source
	from sqlalchemy import select, func
	from ...db.models import RawApiResponse
	
	# Total count
	total_query = select(func.count(RawApiResponse.id))
	total_result = await session.execute(total_query)
	total_count = total_result.scalar() or 0
	
	# Count by source
	source_query = select(
		RawApiResponse.source,
		func.count(RawApiResponse.id).label('count')
	).group_by(RawApiResponse.source)
	source_result = await session.execute(source_query)
	by_source = {row[0]: row[1] for row in source_result}
	
	# Latest response time
	latest_query = select(RawApiResponse.created_at).order_by(
		RawApiResponse.created_at.desc()
	).limit(1)
	latest_result = await session.execute(latest_query)
	latest_time = latest_result.scalar()
	
	return {
		"total_responses": total_count,
		"by_source": by_source,
		"latest_response_at": latest_time.isoformat() if latest_time else None
	}


@router.get("/sources")
async def get_sources(
	session: AsyncSession = Depends(get_async_session)
):
	"""
	Get list of available data sources.
	
	Returns unique API sources that have been collected.
	"""
	from sqlalchemy import select, distinct
	from ...db.models import RawApiResponse
	
	query = select(distinct(RawApiResponse.source))
	result = await session.execute(query)
	sources = [row[0] for row in result]
	
	return {
		"sources": sources,
		"count": len(sources)
	}

