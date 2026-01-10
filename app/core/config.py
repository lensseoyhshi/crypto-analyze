"""Application configuration management."""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
	"""Application settings loaded from environment variables."""
	
	# Application
	APP_NAME: str = Field(default="crypto-analyze")
	DEBUG: bool = Field(default=False)
	
	# Database
	DATABASE_URL: str = Field(
		default="mysql+aiomysql://root:12345678@localhost:3306/crypto-analyze"
	)
	
	# API Keys
	BIRDEYE_API_KEY: str = Field(default="9c1c446225f246f69ec5ebd6103f1502")
	
	# Scheduler Intervals (in seconds)
	DEXSCREENER_FETCH_INTERVAL: int = Field(default=6, description="Seconds between Dexscreener fetches")
	BIRDEYE_NEW_LISTINGS_INTERVAL: int = Field(default=60, description="Seconds between new listings fetches")
	BIRDEYE_TOKEN_OVERVIEW_INTERVAL: int = Field(default=300, description="Seconds between token overview fetches")
	BIRDEYE_TOKEN_SECURITY_INTERVAL: int = Field(default=3600, description="Seconds between security checks")
	BIRDEYE_TOKEN_TRANSACTIONS_INTERVAL: int = Field(default=120, description="Seconds between transaction fetches")
	BIRDEYE_TOP_TRADERS_INTERVAL: int = Field(default=300, description="Seconds between top traders fetches")
	BIRDEYE_WALLET_PORTFOLIO_INTERVAL: int = Field(default=600, description="Seconds between wallet portfolio fetches")
	BIRDEYE_TOKEN_TRENDING_INTERVAL: int = Field(default=3600, description="Seconds between token trending fetches (1 hour)")
	
	# Tokens to track (comma-separated list)
	TRACKED_TOKENS: str = Field(
		default="",
		description="Comma-separated list of token addresses to track"
	)
	
	# Wallets to track (comma-separated list)
	TRACKED_WALLETS: str = Field(
		default="",
		description="Comma-separated list of wallet addresses to track"
	)
	
	# Tracking settings
	TRACK_NEW_LISTINGS_SECURITY: bool = Field(
		default=True,
		description="Automatically check security for new listings"
	)
	
	TRACK_NEW_LISTINGS_OVERVIEW: bool = Field(
		default=True,
		description="Automatically fetch overview for new listings"
	)
	
	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		case_sensitive=True,
		extra="ignore"
	)
	
	@property
	def tracked_tokens_list(self) -> List[str]:
		"""Get list of tracked token addresses."""
		if not self.TRACKED_TOKENS:
			return []
		return [t.strip() for t in self.TRACKED_TOKENS.split(",") if t.strip()]
	
	@property
	def tracked_wallets_list(self) -> List[str]:
		"""Get list of tracked wallet addresses."""
		if not self.TRACKED_WALLETS:
			return []
		return [w.strip() for w in self.TRACKED_WALLETS.split(",") if w.strip()]


settings = Settings()

