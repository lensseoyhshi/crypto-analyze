"""Tests for repository layer."""
import pytest
import json
from datetime import datetime
from app.repositories.raw_api_repository import RawApiRepository
from app.db.models import RawApiResponse


class TestRawApiRepository:
	"""Test suite for RawApiRepository."""
	
	@pytest.mark.asyncio
	async def test_save_response(self, db_session):
		"""Test saving API response to database."""
		repository = RawApiRepository(db_session)
		
		response_data = {
			"test": "data",
			"items": [1, 2, 3]
		}
		
		result = await repository.save_response(
			endpoint="/test/endpoint",
			source="test_source",
			response_data=response_data,
			status_code=200
		)
		
		assert result.id is not None
		assert result.source == "test_source"
		assert result.endpoint == "/test/endpoint"
		assert result.status_code == 200
		assert result.error_message is None
		
		# Verify JSON is stored correctly
		stored_data = json.loads(result.response_json)
		assert stored_data == response_data
	
	@pytest.mark.asyncio
	async def test_get_latest_by_source(self, db_session):
		"""Test retrieving latest responses by source."""
		repository = RawApiRepository(db_session)
		
		# Save multiple responses
		for i in range(3):
			await repository.save_response(
				endpoint=f"/test/endpoint/{i}",
				source="test_source",
				response_data={"index": i},
				status_code=200
			)
		
		# Get latest
		results = await repository.get_latest_by_source("test_source", limit=2)
		
		assert len(results) == 2
		# Should be in descending order by created_at
		assert results[0].endpoint == "/test/endpoint/2"
		assert results[1].endpoint == "/test/endpoint/1"
	
	@pytest.mark.asyncio
	async def test_count_by_source(self, db_session):
		"""Test counting responses by source."""
		repository = RawApiRepository(db_session)
		
		# Save responses for different sources
		await repository.save_response(
			endpoint="/test1",
			source="source1",
			response_data={"test": 1},
			status_code=200
		)
		await repository.save_response(
			endpoint="/test2",
			source="source1",
			response_data={"test": 2},
			status_code=200
		)
		await repository.save_response(
			endpoint="/test3",
			source="source2",
			response_data={"test": 3},
			status_code=200
		)
		
		count1 = await repository.count_by_source("source1")
		count2 = await repository.count_by_source("source2")
		
		assert count1 == 2
		assert count2 == 1
	
	@pytest.mark.asyncio
	async def test_save_response_with_error(self, db_session):
		"""Test saving failed API response."""
		repository = RawApiRepository(db_session)
		
		result = await repository.save_response(
			endpoint="/test/error",
			source="test_source",
			response_data={},
			status_code=500,
			error_message="Internal Server Error"
		)
		
		assert result.status_code == 500
		assert result.error_message == "Internal Server Error"

