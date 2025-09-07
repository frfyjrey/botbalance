"""
Trading strategy constants and choices.

These constants define supported assets and currencies for trading strategies.
They serve as the single source of truth for both backend validation
and frontend UI choices.
"""

# Supported quote assets (base currencies) that can be selected for strategies
SUPPORTED_QUOTE_ASSETS = [
    ("USDT", "USDT"),
    ("USDC", "USDC"),
    ("BTC", "BTC"),
]

# Additional assets available for portfolio allocations
ADDITIONAL_ALLOCATION_ASSETS = [
    "ETH",
    "BNB",
    "ADA",
    "SOL",
]

# Extract quote asset symbols for convenience
QUOTE_ASSET_SYMBOLS = [choice[0] for choice in SUPPORTED_QUOTE_ASSETS]

# All assets that can be used in allocations = quote assets + additional assets
ALL_ALLOCATION_ASSETS = QUOTE_ASSET_SYMBOLS + ADDITIONAL_ALLOCATION_ASSETS


# Helper function to validate if an asset is supported for allocations
def is_valid_allocation_asset(asset: str) -> bool:
    """Check if an asset symbol is valid for strategy allocations."""
    return asset.upper() in [symbol.upper() for symbol in ALL_ALLOCATION_ASSETS]


# Helper function to validate if an asset is a supported quote asset
def is_valid_quote_asset(asset: str) -> bool:
    """Check if an asset symbol is valid as a quote asset."""
    return asset.upper() in [symbol.upper() for symbol in QUOTE_ASSET_SYMBOLS]
