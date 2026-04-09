"""
Quick smoke test / usage example for bvc_scraper.

Run with:
    python examples/quickstart.py
"""

import logging

import bvc_scraper as bvc


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    print("\n=== get_all_stocks() ===")
    stocks = bvc.get_all_stocks()
    print(f"Got {len(stocks)} stocks")
    for s in stocks[:3]:
        print(s)

    print("\n=== get_market_summary() ===")
    print(bvc.get_market_summary())

    print("\n=== get_stock('ATW') ===")
    atw = bvc.get_stock("ATW")
    if atw:
        print(f"{atw['name']}: {atw['price']} MAD ({atw['change_percent']:+.2f}%)")
        print(f"Sector: {atw['sector']}")
        print(f"Market cap: {atw['market_cap']:,.0f} MAD")

    # Historical data — uncomment to test (slow on first run)
    #
    # print("\n=== resolve_symbol_id('IAM') ===")
    # sid = bvc.resolve_symbol_id("IAM")
    # print("symbol_id:", sid)
    #
    # if sid:
    #     print("\n=== get_historical_data('IAM', 2024-01-01, 2024-12-31) ===")
    #     hist = bvc.get_historical_data(sid, "2024-01-01", "2024-12-31")
    #     print(f"Got {len(hist)} historical rows")
    #     if hist:
    #         print("First:", hist[0])
    #         print("Last: ", hist[-1])


if __name__ == "__main__":
    main()
