#!/usr/bin/env python3
"""scripts/pit_universe.py - Combined 60+ name universe for multi-window PIT.

Curated 20 (FY24-26 thesis names) + unbiased 20 (fresh out-of-sample) +
smallcap-cache 25 (cid-resolved, from the smallcap250 backtest cache).
Deduped by ticker. Smallcap entries carry name/sector/cid from the cache;
url_key defaults to the ticker symbol for the financials fetcher.
"""

import os
import sys
import json

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from backtest_fy24_fy26 import UNIVERSE as CURATED  # noqa: E402
from backtest_unbiased_fy24_fy26 import UNIVERSE as UNBIASED  # noqa: E402


def _smallcap_entries():
    paths = [
        os.path.join(os.path.dirname(_SCRIPT_DIR), "data", "smallcap250_backtest_cache.json"),
        "/Users/sajal.goyal@zomato.com/Documents/Finance/predict/data/smallcap250_backtest_cache.json",
        os.path.join(_SCRIPT_DIR, "..", "..", "Finance", "predict", "data",
                     "smallcap250_backtest_cache.json"),
    ]
    cache = None
    for p in paths:
        if os.path.isfile(p):
            with open(p, "r") as f:
                cache = json.load(f)
            break
    if not cache:
        return []
    out = []
    for ticker, item in cache.items():
        try:
            out.append({
                "ticker": ticker,
                "name": item.get("name", ticker),
                "cat": "Small Cap",
                "sector": item.get("sector", "Smallcap"),
                "cid": int(item.get("cid")),
                "url_key": ticker,
            })
        except (TypeError, ValueError):
            continue
    return out


def build_universe():
    seen = set()
    combined = []
    for src in (CURATED, UNBIASED, _smallcap_entries()):
        for item in src:
            t = item["ticker"]
            if t in seen:
                continue
            seen.add(t)
            combined.append({
                "ticker": t,
                "name": item.get("name", t),
                "cat": item.get("cat", "Small Cap"),
                "sector": item.get("sector", ""),
                "cid": item["cid"],
                "url_key": item.get("url_key", t),
            })
    return combined


PIT_UNIVERSE = build_universe()

if __name__ == "__main__":
    print(f"Combined PIT universe: {len(PIT_UNIVERSE)} names")
    for u in PIT_UNIVERSE:
        print(f"  {u['ticker']:12} {u['cat']:10} cid={u['cid']}")
