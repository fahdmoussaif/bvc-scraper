# bvc-scraper

A minimal, dependency-light Python scraper for the **Casablanca Stock Exchange** (Bourse de Casablanca / BVC). Returns plain Python types — no pandas, no surprises — ready for JSON serialization or database storage.

> Originally built as the data layer for an Android investing simulator. Extracted into a library so others can use it.

## Why?

The BVC has no official free public API. Existing Python solutions either return French-formatted strings, depend on heavy libraries like pandas, or only return a partial slice of the listed stocks. This library:

- Returns **all ~113 listed equity instruments** in a single HTTP request
- Returns clean `float` values and English `snake_case` keys, ready for JSON
- Has only two runtime dependencies: `requests` and `urllib3`
- Is easy to cache: every record carries a `fetched_at` timestamp

## Installation

Install directly from GitHub:

```bash
pip install git+https://github.com/YOUR-USERNAME/bvc-scraper.git
```

Or, for local development:

```bash
git clone https://github.com/YOUR-USERNAME/bvc-scraper.git
cd bvc-scraper
pip install -e .
```

## Quick start

```python
import bvc_scraper as bvc

# All stocks with current quotes (single request, ~1 second)
stocks = bvc.get_all_stocks()
print(f"{len(stocks)} stocks listed")
print(stocks[0])

# One stock by ticker
atw = bvc.get_stock("ATW")
print(atw["name"], atw["price"], "MAD")

# Market-wide summary
print(bvc.get_market_summary())
```

A runnable version is in [`examples/quickstart.py`](examples/quickstart.py).

## API reference

### `get_all_stocks() -> list[dict]`

Fetches every equity listed on the BVC with its current quote. One HTTP request, ~1 second. Each dict has these keys:

| Key | Type | Description |
|---|---|---|
| `ticker` | `str` | Trading symbol, e.g. `"ATW"` |
| `name` | `str` | Company name, e.g. `"ATTIJARIWAFA BANK"` |
| `sector` | `str` | Sub-sector, e.g. `"Banques"` |
| `status` | `str` | Trading status |
| `price` | `float` | Current/last traded price (MAD) |
| `open` | `float` | Day open |
| `high` | `float` | Day high |
| `low` | `float` | Day low |
| `previous_close` | `float` | Reference price (previous close) |
| `change_percent` | `float` | Daily change in percent |
| `volume` | `float` | Total MAD value traded today |
| `shares_traded` | `int` | Number of shares traded today |
| `trades_count` | `int` | Number of trades today |
| `market_cap` | `float` | Total market capitalization (MAD) |
| `best_bid` | `float` | Top bid price |
| `best_bid_size` | `int` | Top bid size |
| `best_ask` | `float` | Top ask price |
| `best_ask_size` | `int` | Top ask size |
| `fetched_at` | `str` | UTC ISO timestamp |

### `get_stock(ticker: str) -> dict | None`

Convenience wrapper that returns one stock. Re-fetches the entire market — for production use, query a cached copy from your own database instead.

### `get_market_summary() -> dict`

Aggregate market stats: gainer/loser counts, average change, total volume, total market capitalization.

### `get_historical_data(symbol_id: int, from_date: str, to_date: str) -> list[dict]`

Historical OHLCV for one instrument. Note that `symbol_id` is the BVC internal numeric ID — **not** the ticker. Use `resolve_symbol_id()` once to map a ticker to its ID, then cache the mapping in your database. Dates use `YYYY-MM-DD` format.

Returns a list of daily records sorted oldest to newest, each with: `date`, `open`, `close`, `last`, `high`, `low`, `volume`, `shares_traded`, `trades_count`.

### `resolve_symbol_id(ticker: str) -> int | None`

Maps a ticker to its internal numeric symbol ID. **Slow** (~30 seconds — makes one HTTP call per instrument). Call once per ticker on first use, then store the result.

### `get_build_id() -> str | None`

Scrapes the Next.js `buildId` from the BVC homepage. Used internally by `resolve_symbol_id`. Cached for one hour.

## Known limitations

1. **`resolve_symbol_id` only resolves the first ~50 tickers** alphabetically (A through M-ish). The underlying listing endpoint is paginated and the package does not yet handle pagination. This affects historical-data lookups for later-alphabet tickers like SGTM, TAQA, WAA. Pull requests welcome.
2. **The BVC API is not officially documented or supported.** Endpoints may change without warning. If something breaks, please open an issue.
3. **Be polite.** Cache results in your own database and refresh on a schedule (e.g. every 5 minutes during market hours) — do not call these functions on every user request.
4. **TLS verification is disabled** (`verify=False`) due to historical issues with the BVC SSL chain. If your environment requires it, edit `bvc_scraper/scraper.py`.

## Market hours

The Bourse de Casablanca trades **Monday–Friday, 9:30–15:20** (Africa/Casablanca timezone). Outside these hours prices won't change, so there's no benefit to scraping more frequently.

## Acknowledgements

This library was bootstrapped by reading the source of [`casabourse`](https://github.com/Fredysessie/Casabourse) by **Koffi Frederic SESSIE**, which taught us where the BVC's internal endpoints live. If you need a more feature-rich scraper (technical indicators, indices composition, capitalization data, sector indices, etc.), use Sessie's library directly.

This library deliberately offers a much smaller surface area: just enough for an investing simulator or a simple market dashboard.

## License

MIT. See [`LICENSE`](LICENSE).
