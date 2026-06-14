"""NLB Skladi JSON API client for fetching daily NAV data."""

import json
import logging
import time
import urllib.request

log = logging.getLogger(__name__)

API_TEMPLATE = (
    "https://www.nlbskladi.si/content/nlbskladi/nlbskladisi/sl/uporabni-izracuni/"
    "gibanje-vrednosti-enot-premozenja/jcr:content/root/container/container/"
    "contentcontainer/unitvaluecomparator.fundsarchive.{fund_id}.json"
    "?dateMin=1990-01-01&dateMax=2099-12-31"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Referer": "https://www.nlbskladi.si/uporabni-izracuni/gibanje-vrednosti-enot-premozenja",
}


def _prune_monthly(records: list[dict]) -> list[dict]:
    """Keep only the last record per calendar month (most recent NAV)."""
    result = []
    prev_key = None
    for r in records:
        key = r["date"][:7]  # YYYY-MM
        if key != prev_key:
            if prev_key is not None:
                result.append(last)
            prev_key = key
        last = r
    if prev_key is not None:
        result.append(last)
    return result


def fetch_nav(fund_id: str, retries: int = 3) -> list[dict]:
    """Fetch monthly NAV records for a given NLB fund ID.

    Returns a list of dicts with 'date' (str YYYY-MM-DD) and 'nav' (float).
    """
    records = _fetch_raw(fund_id, retries)
    return _prune_monthly(records)


def fetch_nav_daily(fund_id: str, retries: int = 3) -> list[dict]:
    """Fetch all daily NAV records (no pruning)."""
    return _fetch_raw(fund_id, retries)


def _fetch_raw(fund_id: str, retries: int = 3) -> list[dict]:
    url = API_TEMPLATE.format(fund_id=fund_id)

    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())

            records = []
            for entry in data:
                date = entry["date"]
                for f in entry["funds"]:
                    if f["id"] == fund_id and f["nav"]:
                        nav = float(f["nav"].replace(",", "."))
                        records.append({"date": date, "nav": nav})
                        break

            return records
        except Exception as e:
            wait = (attempt + 1) * 5
            log.warning(
                "[%s] API attempt %d/%d failed: %s — waiting %ds",
                fund_id, attempt + 1, retries, e, wait if attempt < retries - 1 else 0,
            )
            if attempt < retries - 1:
                time.sleep(wait)

    raise RuntimeError(f"Failed to fetch fund {fund_id} after {retries} attempts")
