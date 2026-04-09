"""bvc_scraper — minimal scraper for the Casablanca Stock Exchange."""

from .scraper import (
    get_all_stocks,
    get_stock,
    get_market_summary,
    get_historical_data,
    resolve_symbol_id,
    get_build_id,
)

__version__ = "0.1.0"

__all__ = [
    "get_all_stocks",
    "get_stock",
    "get_market_summary",
    "get_historical_data",
    "resolve_symbol_id",
    "get_build_id",
    "__version__",
]
