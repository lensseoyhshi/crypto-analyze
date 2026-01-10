from typing import Any, Dict, Optional
import httpx
import logging
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class BaseApiClient:
	"""Lightweight wrapper around HTTPX for concrete API clients to extend."""

	def __init__(self, base_url: str, timeout: int = 30, max_retries: int = 3):
		self.base_url = base_url
		self.max_retries = max_retries
		
		# 检查是否禁用 SSL 验证（仅开发环境）
		verify_ssl = os.getenv("VERIFY_SSL", "true").lower() != "false"
		
		if not verify_ssl:
			logger.warning("⚠️  SSL verification is DISABLED. This should only be used in development!")
		
		self._client = httpx.AsyncClient(
			base_url=self.base_url,
			timeout=timeout,
			limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
			verify=verify_ssl  # 添加 SSL 验证控制
		)

	@retry(
		stop=stop_after_attempt(3),
		wait=wait_exponential(multiplier=1, min=2, max=10),
		retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
		reraise=True
	)
	async def get(
		self,
		path: str,
		params: Optional[Dict[str, Any]] = None,
		headers: Optional[Dict[str, str]] = None
	) -> Any:
		"""Execute GET request with retry logic."""
		try:
			resp = await self._client.get(path, params=params, headers=headers)
			resp.raise_for_status()
			return resp.json()
		except httpx.HTTPStatusError as e:
			logger.error(f"HTTP error {e.response.status_code} for {path}: {e.response.text}")
			raise
		except Exception as e:
			logger.error(f"Unexpected error for GET {path}: {str(e)}")
			raise

	@retry(
		stop=stop_after_attempt(3),
		wait=wait_exponential(multiplier=1, min=2, max=10),
		retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
		reraise=True
	)
	async def post(
		self,
		path: str,
		json: Optional[Dict[str, Any]] = None,
		headers: Optional[Dict[str, str]] = None
	) -> Any:
		"""Execute POST request with retry logic."""
		try:
			resp = await self._client.post(path, json=json, headers=headers)
			resp.raise_for_status()
			return resp.json()
		except httpx.HTTPStatusError as e:
			logger.error(f"HTTP error {e.response.status_code} for {path}: {e.response.text}")
			raise
		except Exception as e:
			logger.error(f"Unexpected error for POST {path}: {str(e)}")
			raise

	async def close(self):
		"""Close the HTTP client."""
		await self._client.aclose()


