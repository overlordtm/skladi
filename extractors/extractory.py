#!/usr/bin/env python3
"""
General fund data extractor.
Reads sources.json and dispatches to the appropriate extractor based on source.type.
- nlb_api → src.nlbapi.fetch_nav
- yahoo   → yfinance.download
Outputs clean CSV files to data/.
"""
import json
import logging
import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

from src.nlbapi import fetch_nav, fetch_nav_daily

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent


def load_items():
    with open(ROOT / "sources.json") as f:
        return json.load(f)["items"]


def extract_yahoo(item: dict) -> list[dict]:
    ticker = item["source"]["ticker"]
    log.info("[%s] Downloading %s via yfinance", item["id"], ticker)

    df = yf.download(ticker, period="max", interval="1mo", progress=False, auto_adjust=True)

    if df.empty:
        raise RuntimeError(f"No data returned for {ticker}")

    close_col = ("Close", ticker) if isinstance(df.columns, pd.MultiIndex) else "Close"

    records = []
    for ts, row in df.iterrows():
        close = float(row[close_col])
        date_str = ts.strftime("%Y-%m-%d")
        records.append({"date": date_str, "close": round(close, 4)})

    return records


def write_csv(output_path: Path, records: list[dict], columns: tuple[str, str]):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    col_date, col_val = columns
    with open(output_path, "w", newline="") as f:
        f.write(f"{col_date},{col_val}\n")
        for r in records:
            f.write(f"{r['date']},{r[col_val]:.4f}\n")


def process_item(item: dict) -> bool:
    item_id = item["id"]
    source_type = item["source"]["type"]
    output_path = ROOT / item["output"]

    try:
        if source_type == "nlb_api":
            fund_id = item["source"]["fund_id"]
            log.info("[%s] Fetching NLB API (fund_id=%s)", item_id, fund_id)
            daily_records = fetch_nav_daily(fund_id)
            if not daily_records:
                raise RuntimeError("No daily data returned")
            # Write monthly CSV
            from src.nlbapi.client import _prune_monthly
            monthly = _prune_monthly(daily_records)
            write_csv(output_path, monthly, ("date", "nav"))
            # Write daily CSV
            daily_path = output_path.parent / (output_path.stem + "_daily.csv")
            write_csv(daily_path, daily_records, ("date", "nav"))
            log.info(
                "[%s] Wrote %d rows → %s (%s → %s)",
                item_id, len(monthly), output_path,
                monthly[0]["date"], monthly[-1]["date"],
            )
            log.info(
                "[%s] Wrote %d daily rows → %s (%s → %s)",
                item_id, len(daily_records), daily_path,
                daily_records[0]["date"], daily_records[-1]["date"],
            )
        elif source_type == "yahoo":
            records = extract_yahoo(item)
            write_csv(output_path, records, ("date", "close"))
            log.info(
                "[%s] Wrote %d rows → %s (%s → %s)",
                item_id, len(records), output_path,
                records[0]["date"], records[-1]["date"],
            )
        else:
            log.error("[%s] Unknown source type: %s", item_id, source_type)
            return False
        return True
    except Exception as e:
        log.error("[%s] Failed: %s", item_id, e)
        return False


def main():
    items = load_items()
    log.info("Extracting %d items from sources.json", len(items))

    all_ok = True
    for item in items:
        try:
            ok = process_item(item)
            if not ok:
                all_ok = False
        except Exception as e:
            log.error("[%s] Unexpected: %s", item.get("id", "?"), e)
            all_ok = False

        time.sleep(1)

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
