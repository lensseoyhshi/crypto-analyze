"""Dexscreener API response schemas."""
from typing import List, Optional
from pydantic import BaseModel, Field


class Link(BaseModel):
    """Social media link."""
    type: str
    url: str


class TokenBoost(BaseModel):
    """Token boost item from Dexscreener top boosts API."""
    url: str
    chainId: str = Field(alias="chainId")
    tokenAddress: str = Field(alias="tokenAddress")
    description: Optional[str] = None
    icon: Optional[str] = None
    header: Optional[str] = None
    openGraph: Optional[str] = Field(None, alias="openGraph")
    links: Optional[List[Link]] = None
    totalAmount: int = Field(alias="totalAmount")

    class Config:
        populate_by_name = True


class TopTokenBoostsResponse(BaseModel):
    """Response from Dexscreener top token boosts API."""
    items: List[TokenBoost] = Field(default_factory=list)

    @classmethod
    def from_list(cls, data: List[dict]) -> "TopTokenBoostsResponse":
        """Create response from list of dicts."""
        return cls(items=data)

