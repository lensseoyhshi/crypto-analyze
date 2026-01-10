"""Birdeye API response schemas."""
from typing import List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field


# Schema for transaction token info
class TokenInfo(BaseModel):
    """Token information in a transaction."""
    symbol: str
    decimals: int
    address: str
    amount: Union[str, int, float]  # API可能返回字符串、整数或浮点数
    uiAmount: float
    price: float
    nearestPrice: float
    changeAmount: Any
    uiChangeAmount: float
    isScaledUiToken: bool
    multiplier: Optional[Any] = None


# Schema for token transactions (seek by time)
class TransactionItem(BaseModel):
    """Transaction item from token transactions API."""
    quote: TokenInfo
    base: TokenInfo
    basePrice: float
    quotePrice: float
    txHash: str
    source: str
    blockUnixTime: int
    txType: str
    owner: str
    side: str
    alias: Optional[str] = None
    pricePair: float
    from_token: TokenInfo = Field(alias="from")
    to_token: TokenInfo = Field(alias="to")
    tokenPrice: float
    poolId: str

    class Config:
        populate_by_name = True


class TransactionsData(BaseModel):
    """Data wrapper for transactions."""
    items: List[TransactionItem]
    hasNext: bool


class TransactionsResponse(BaseModel):
    """Response from token transactions API."""
    data: TransactionsData
    success: bool


# Schema for top traders
class TopTraderItem(BaseModel):
    """Top trader item."""
    tokenAddress: str
    owner: str
    tags: List[str] = Field(default_factory=list)
    type: str
    volume: float
    trade: int
    tradeBuy: int
    tradeSell: int
    volumeBuy: float
    volumeSell: float
    isScaledUiToken: bool
    multiplier: Optional[Any] = None


class TopTradersData(BaseModel):
    """Data wrapper for top traders."""
    items: List[TopTraderItem]


class TopTradersResponse(BaseModel):
    """Response from top traders API."""
    success: bool
    data: TopTradersData


# Schema for wallet transactions
class BalanceChange(BaseModel):
    """Balance change in a transaction."""
    amount: int
    symbol: str
    name: str
    decimals: int
    address: str
    logoURI: Optional[str] = None
    tokenAccount: Optional[str] = None
    owner: Optional[str] = None
    programId: Optional[str] = None
    isScaledUiToken: bool
    multiplier: Optional[Any] = None


class ContractLabel(BaseModel):
    """Contract label information."""
    address: str
    name: str
    metadata: dict


class TokenTransfer(BaseModel):
    """Token transfer details."""
    fromTokenAccount: str
    toTokenAccount: str
    fromUserAccount: str
    toUserAccount: str
    tokenAmount: float
    mint: str
    transferNative: bool
    isScaledUiToken: bool
    multiplier: Optional[Any] = None


class WalletTransaction(BaseModel):
    """Wallet transaction item."""
    txHash: str
    blockNumber: int
    blockTime: str
    status: bool
    from_address: str = Field(alias="from")
    to_address: str = Field(alias="to")
    fee: int
    mainAction: str
    balanceChange: List[BalanceChange]
    contractLabel: ContractLabel
    tokenTransfers: List[TokenTransfer]

    class Config:
        populate_by_name = True


class WalletTransactionsData(BaseModel):
    """Data wrapper for wallet transactions."""
    solana: List[WalletTransaction]


class WalletTransactionsResponse(BaseModel):
    """Response from wallet transactions API."""
    success: bool
    data: WalletTransactionsData


# Schema for wallet token list (portfolio)
class WalletTokenItem(BaseModel):
    """Token item in wallet portfolio."""
    address: str
    decimals: int
    balance: int
    uiAmount: float
    chainId: str
    name: str
    symbol: str
    icon: Optional[str] = None
    logoURI: Optional[str] = None
    priceUsd: float
    valueUsd: float
    isScaledUiToken: bool
    multiplier: Optional[Any] = None


class WalletTokenListData(BaseModel):
    """Data wrapper for wallet token list."""
    wallet: str
    totalUsd: float
    items: List[WalletTokenItem]


class WalletTokenListResponse(BaseModel):
    """Response from wallet token list API."""
    success: bool
    data: WalletTokenListData


# Schema for new listings
class NewListingItem(BaseModel):
    """New listing token item."""
    address: str
    symbol: str
    name: str
    decimals: int
    source: str
    liquidityAddedAt: str
    logoURI: Optional[str] = None
    liquidity: float


class NewListingsData(BaseModel):
    """Data wrapper for new listings."""
    items: List[NewListingItem]


class NewListingsResponse(BaseModel):
    """Response from new listings API."""
    success: bool
    data: NewListingsData


# Schema for token security
class TokenSecurityData(BaseModel):
    """Token security data."""
    creatorAddress: Optional[str] = None
    creatorOwnerAddress: Optional[str] = None
    ownerAddress: Optional[str] = None
    ownerOfOwnerAddress: Optional[str] = None
    creationTx: Optional[str] = None
    creationTime: Optional[int] = None
    creationSlot: Optional[int] = None
    mintTx: Optional[str] = None
    mintTime: Optional[int] = None
    mintSlot: Optional[int] = None
    creatorBalance: Optional[float] = None
    ownerBalance: Optional[float] = None
    ownerPercentage: Optional[float] = None
    creatorPercentage: Optional[float] = None
    metaplexUpdateAuthority: Optional[str] = None
    metaplexOwnerUpdateAuthority: Optional[str] = None
    metaplexUpdateAuthorityBalance: Optional[float] = None
    metaplexUpdateAuthorityPercent: Optional[float] = None
    mutableMetadata: Optional[bool] = None
    top10HolderBalance: Optional[float] = None
    top10HolderPercent: Optional[float] = None
    top10UserBalance: Optional[float] = None
    top10UserPercent: Optional[float] = None
    isTrueToken: Optional[bool] = None
    totalSupply: Optional[float] = None
    preMarketHolder: Optional[List[Any]] = None
    lockInfo: Optional[Any] = None
    freezeable: Optional[bool] = None
    freezeAuthority: Optional[str] = None
    transferFeeEnable: Optional[bool] = None
    transferFeeData: Optional[Any] = None
    isToken2022: bool = False
    nonTransferable: Optional[bool] = None


class TokenSecurityResponse(BaseModel):
    """Response from token security API."""
    data: TokenSecurityData
    success: bool
    statusCode: int


# Schema for token overview
class TokenOverviewData(BaseModel):
    """Token overview data with extensive metrics."""
    address: str
    marketCap: Optional[float] = None
    fdv: Optional[float] = None
    extensions: dict = Field(default_factory=dict)
    liquidity: Optional[float] = None
    lastTradeUnixTime: Optional[int] = None
    lastTradeHumanTime: Optional[str] = None
    price: Optional[float] = None
    
    # Price history and changes
    history1mPrice: Optional[float] = None
    priceChange1mPercent: Optional[float] = None
    history5mPrice: Optional[float] = None
    priceChange5mPercent: Optional[float] = None
    history30mPrice: Optional[float] = None
    priceChange30mPercent: Optional[float] = None
    history1hPrice: Optional[float] = None
    priceChange1hPercent: Optional[float] = None
    history2hPrice: Optional[float] = None
    priceChange2hPercent: Optional[float] = None
    history4hPrice: Optional[float] = None
    priceChange4hPercent: Optional[float] = None
    history6hPrice: Optional[float] = None
    priceChange6hPercent: Optional[float] = None
    history8hPrice: Optional[float] = None
    priceChange8hPercent: Optional[float] = None
    history12hPrice: Optional[float] = None
    priceChange12hPercent: Optional[float] = None
    history24hPrice: Optional[float] = None
    priceChange24hPercent: Optional[float] = None
    
    # Unique wallets
    uniqueWallet1m: Optional[int] = None
    uniqueWalletHistory1m: Optional[int] = None
    uniqueWallet1mChangePercent: Optional[float] = None
    uniqueWallet5m: Optional[int] = None
    uniqueWalletHistory5m: Optional[int] = None
    uniqueWallet5mChangePercent: Optional[float] = None
    uniqueWallet30m: Optional[int] = None
    uniqueWalletHistory30m: Optional[int] = None
    uniqueWallet30mChangePercent: Optional[float] = None
    uniqueWallet1h: Optional[int] = None
    uniqueWalletHistory1h: Optional[int] = None
    uniqueWallet1hChangePercent: Optional[float] = None
    uniqueWallet2h: Optional[int] = None
    uniqueWalletHistory2h: Optional[int] = None
    uniqueWallet2hChangePercent: Optional[float] = None
    uniqueWallet4h: Optional[int] = None
    uniqueWalletHistory4h: Optional[int] = None
    uniqueWallet4hChangePercent: Optional[float] = None
    uniqueWallet8h: Optional[int] = None
    uniqueWalletHistory8h: Optional[int] = None
    uniqueWallet8hChangePercent: Optional[float] = None
    uniqueWallet24h: Optional[int] = None
    uniqueWalletHistory24h: Optional[int] = None
    uniqueWallet24hChangePercent: Optional[float] = None
    
    # Supply and holders
    totalSupply: Optional[float] = None
    circulatingSupply: Optional[float] = None
    holder: Optional[int] = None
    
    # Trading metrics (1m, 5m, 30m, 1h, 2h, 4h, 8h, 24h)
    # Just including a few key ones to avoid excessive repetition
    trade1m: Optional[int] = None
    trade5m: Optional[int] = None
    trade30m: Optional[int] = None
    trade1h: Optional[int] = None
    trade24h: Optional[int] = None
    
    buy1m: Optional[int] = None
    buy30m: Optional[int] = None
    buy1h: Optional[int] = None
    buy24h: Optional[int] = None
    
    sell1m: Optional[int] = None
    sell30m: Optional[int] = None
    sell1h: Optional[int] = None
    sell24h: Optional[int] = None
    
    # Volume metrics
    v1m: Optional[float] = None
    v1mUSD: Optional[float] = None
    v5m: Optional[float] = None
    v5mUSD: Optional[float] = None
    v30m: Optional[float] = None
    v30mUSD: Optional[float] = None
    v1h: Optional[float] = None
    v1hUSD: Optional[float] = None
    v24h: Optional[float] = None
    v24hUSD: Optional[float] = None
    
    vBuy30m: Optional[float] = None
    vBuy30mUSD: Optional[float] = None
    vSell30m: Optional[float] = None
    vSell30mUSD: Optional[float] = None
    
    numberMarkets: Optional[int] = None
    isScaledUiToken: bool = False
    multiplier: Optional[Any] = None


class TokenOverviewResponse(BaseModel):
    """Response from token overview API."""
    data: TokenOverviewData
    success: bool


# Schema for token trending
class TokenTrendingItem(BaseModel):
    """Token trending item."""
    address: str
    decimals: int
    fdv: float
    liquidity: float
    logoURI: Optional[str] = None
    marketcap: float
    name: str
    price: float
    rank: int
    symbol: str
    volume24hUSD: float
    volume24hChangePercent: Optional[float] = None
    price24hChangePercent: Optional[float] = None
    isScaledUiToken: bool = False
    multiplier: Optional[Any] = None


class TokenTrendingData(BaseModel):
    """Data wrapper for token trending."""
    updateUnixTime: int
    updateTime: str
    tokens: List[TokenTrendingItem]
    total: int


class TokenTrendingResponse(BaseModel):
    """Response from token trending API."""
    data: TokenTrendingData
    success: bool

