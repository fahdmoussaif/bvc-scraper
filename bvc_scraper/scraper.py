import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

log = logging.getLogger(__name__)



BASE = "https://www.casablanca-bourse.com"
DASHBOARD_URL = f"{BASE}/api/proxy/fr/api/bourse/dashboard/ticker"
HISTORY_URL = f"{BASE}/api/proxy/fr/api/bourse_data/instrument_history"
HOMEPAGE_URL = f"{BASE}/fr"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

TIMEOUT = 30




def _to_float(value: Any) -> Optional[float]:
    if value is None or value == "" or value == "-":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _to_int(value: Any) -> Optional[int]:
    f = _to_float(value)
    return int(f) if f is not None else None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")




_build_id_cache: Dict[str, Any] = {"value": None, "fetched_at": 0.0}
_BUILD_ID_TTL_SECONDS = 3600  # cache for 1 hour


def get_build_id() -> Optional[str]:

    now = time.time()
    if _build_id_cache["value"] and now - _build_id_cache["fetched_at"] < _BUILD_ID_TTL_SECONDS:
        return _build_id_cache["value"]

    try:
        r = requests.get(HOMEPAGE_URL, headers=HEADERS, timeout=TIMEOUT, verify=False)
        r.raise_for_status()
        match = re.search(r'"buildId":"([^"]+)"', r.text)
        if match:
            _build_id_cache["value"] = match.group(1)
            _build_id_cache["fetched_at"] = now
            log.info("Refreshed buildId: %s", match.group(1))
            return match.group(1)
        log.error("buildId not found on homepage")
    except Exception as e:
        log.error("Failed to fetch buildId: %s", e)
    return None




def get_all_stocks() -> List[Dict[str, Any]]:

    params = {"marche": 59, "class[]": [50]}
    try:
        r = requests.get(
            DASHBOARD_URL,
            params=params,
            headers=HEADERS,
            timeout=TIMEOUT,
            verify=False,
        )
        r.raise_for_status()
        payload = r.json()
    except Exception as e:
        log.error("Failed to fetch market data: %s", e)
        return []

    rows = payload.get("data", {}).get("values", [])
    timestamp = _now_iso()

    stocks = []
    for raw in rows:
        stocks.append({
            "ticker":          raw.get("ticker"),
            "name":            raw.get("label"),
            "sector":          raw.get("sous_secteur"),
            "status":          raw.get("field_etat_cot_val"),
            "price":           _to_float(raw.get("field_cours_courant")),
            "open":            _to_float(raw.get("field_opening_price")),
            "high":            _to_float(raw.get("field_high_price")),
            "low":             _to_float(raw.get("field_low_price")),
            "previous_close":  _to_float(raw.get("field_static_reference_price")),
            "change_percent":  _to_float(raw.get("field_var_veille")),
            "volume":          _to_float(raw.get("field_cumul_volume_echange")),
            "shares_traded":   _to_int(raw.get("field_cumul_titres_echanges")),
            "trades_count":    _to_int(raw.get("field_total_trades")),
            "market_cap":      _to_float(raw.get("field_capitalisation")),
            "best_bid":        _to_float(raw.get("field_best_bid_price")),
            "best_bid_size":   _to_int(raw.get("field_best_bid_size")),
            "best_ask":        _to_float(raw.get("field_best_ask_price")),
            "best_ask_size":   _to_int(raw.get("field_best_ask_size")),
            "fetched_at":      timestamp,
        })

    log.info("Fetched %d stocks", len(stocks))
    return stocks


def get_stock(ticker: str) -> Optional[Dict[str, Any]]:

    ticker_u = ticker.upper()
    for s in get_all_stocks():
        if s["ticker"] and s["ticker"].upper() == ticker_u:
            return s
    return None




def get_market_summary() -> Dict[str, Any]:

    stocks = get_all_stocks()
    if not stocks:
        return {}

    changes = [s["change_percent"] for s in stocks if s["change_percent"] is not None]
    caps = [s["market_cap"] for s in stocks if s["market_cap"] is not None]
    vols = [s["volume"] for s in stocks if s["volume"] is not None]

    gainers = sum(1 for s in stocks if (s["change_percent"] or 0) > 0)
    losers = sum(1 for s in stocks if (s["change_percent"] or 0) < 0)
    unchanged = sum(1 for s in stocks if s["change_percent"] == 0)

    return {
        "total_instruments": len(stocks),
        "gainers":           gainers,
        "losers":            losers,
        "unchanged":         unchanged,
        "average_change":    (sum(changes) / len(changes)) if changes else None,
        "total_volume":      sum(vols),
        "total_market_cap":  sum(caps),
        "fetched_at":        _now_iso(),
    }




def get_historical_data(
    symbol_id: int,
    from_date: str,
    to_date: str,
) -> List[Dict[str, Any]]:

    headers = {
        **HEADERS,
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
    }

    all_rows: List[Dict[str, Any]] = []
    offset = 0
    limit = 250

    while True:
        params = [
            ("fields[instrument_history]",
             "symbol,created,openingPrice,coursCourant,highPrice,lowPrice,"
             "cumulTitresEchanges,cumulVolumeEchange,totalTrades,closingPrice"),
            ("sort[date-seance][path]", "created"),
            ("sort[date-seance][direction]", "DESC"),
            ("filter[instrument-history-class][condition][path]",
             "symbol.codeClasse.field_code"),
            ("filter[instrument-history-class][condition][value]", "1"),
            ("filter[published]", "1"),
            ("page[offset]", str(offset)),
            ("page[limit]", str(limit)),
            ("filter[filter-date-start-vh][condition][path]", "field_seance_date"),
            ("filter[filter-date-start-vh][condition][operator]", ">="),
            ("filter[filter-date-start-vh][condition][value]", from_date),
            ("filter[filter-date-end-vh][condition][path]", "field_seance_date"),
            ("filter[filter-date-end-vh][condition][operator]", "<="),
            ("filter[filter-date-end-vh][condition][value]", to_date),
            ("filter[filter-historique-instrument-emetteur][condition][path]",
             "symbol.meta.drupal_internal__target_id"),
            ("filter[filter-historique-instrument-emetteur][condition][operator]", "="),
            ("filter[filter-historique-instrument-emetteur][condition][value]",
             str(symbol_id)),
        ]
        try:
            r = requests.get(
                HISTORY_URL,
                params=params,
                headers=headers,
                timeout=TIMEOUT,
                verify=False,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            log.error("Historical fetch failed at offset %d: %s", offset, e)
            break

        page = data.get("data") or []
        if not page:
            break

        for item in page:
            attrs = item.get("attributes", {})
            all_rows.append({
                "date":          attrs.get("created"),
                "open":          _to_float(attrs.get("openingPrice")),
                "close":         _to_float(attrs.get("closingPrice")),
                "last":          _to_float(attrs.get("coursCourant")),
                "high":          _to_float(attrs.get("highPrice")),
                "low":           _to_float(attrs.get("lowPrice")),
                "volume":        _to_float(attrs.get("cumulVolumeEchange")),
                "shares_traded": _to_int(attrs.get("cumulTitresEchanges")),
                "trades_count":  _to_int(attrs.get("totalTrades")),
            })

        if len(page) < limit:
            break
        offset += limit
        time.sleep(0.4)  # be polite to the API

    all_rows.sort(key=lambda r: r["date"] or "")
    log.info("Fetched %d historical rows for symbol_id=%s", len(all_rows), symbol_id)
    return all_rows




def resolve_symbol_id(ticker: str) -> Optional[int]:

    build_id = get_build_id()
    if not build_id:
        return None

    listing_url = (
        f"{BASE}/_next/data/{build_id}/fr/live-market/marche-actions-listing.json"
    )
    try:
        r = requests.get(listing_url, headers=HEADERS, timeout=TIMEOUT, verify=False)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.error("Failed to fetch listing: %s", e)
        return None

    paragraphs = (
        data.get("pageProps", {}).get("node", {}).get("field_vactory_paragraphs", [])
    )
    ticker_u = ticker.upper()

    for block in paragraphs:
        widget = block.get("field_vactory_component", {})
        if widget.get("widget_id") != "bourse_data_listing:marches-actions":
            continue
        parsed = json.loads(widget.get("widget_data", "{}"))
        instruments = (
            parsed.get("extra_field", {})
                  .get("collection", {})
                  .get("data", {})
                  .get("data", [])
        )
        for item in instruments:
            url_inst = (
                item.get("relationships", {})
                    .get("symbol", {})
                    .get("links", {})
                    .get("related", {})
                    .get("href")
            )
            if not url_inst:
                continue
            try:
                ri = requests.get(url_inst, timeout=10, verify=False)
                if ri.status_code == 200:
                    attrs = ri.json().get("data", {}).get("attributes", {})
                    if (attrs.get("symbol") or "").upper() == ticker_u:
                        sid = attrs.get("drupal_internal__id")
                        log.info("Resolved %s -> symbol_id=%s", ticker, sid)
                        return sid
            except Exception:
                continue

    log.warning("Could not resolve ticker: %s", ticker)
    return None



