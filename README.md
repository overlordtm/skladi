# mojiskladi

Slovenian mutual fund (NLB Skladi) vs. low-cost ETF comparator — a single-page web simulator with automated daily data refresh.

## How it works

1. **Data extraction** — `extractors/extractory.py` pulls historical NAV data for 20 NLB Skladi mutual funds via their JSON API, and monthly close prices for 5 ETFs via Yahoo Finance (`yfinance`). Results are written as clean CSV files into `data/`.

2. **Web simulator** — `index.html` loads the fund list from `sources.json`, fetches CSV data on demand, and runs a dollar-cost averaging simulation with configurable fees (entry, exit, per-trade fixed). Results are rendered as a summary table and Chart.js charts.

3. **Daily automation** — GitHub Actions update CSV data daily at 02:30 UTC and deploy the site to GitHub Pages at 03:00 UTC.

## Project structure

```
├── sources.json                  Fund/ETF definitions (IDs, fees, API references, output paths)
├── index.html                    Single-page fund comparator
├── extracts/
│   └── extractory.py            Main extractor — dispatches by source.type (nlb_api / yahoo)
├── src/
│   └── nlbapi/
│       ├── __init__.py
│       └── client.py            NLB Skladi JSON API client
├── data/                         Generated CSV files (25 funds)
├── requirements.txt
├── pyproject.toml
└── .github/workflows/
    ├── update-data.yml           Daily CSV refresh at 02:30 UTC
    └── deploy-pages.yml          Daily GitHub Pages deploy at 03:00 UTC
```

## Running locally

```bash
# Install dependencies
pip install -r requirements.txt

# Fetch all fund data (20 NLB + 5 ETFs)
PYTHONPATH=. python3 extractors/extractory.py

# Serve the frontend
python3 -m http.server 8000
# Open http://localhost:8000
```

## Configuration

Edit `sources.json` to add or remove funds. Each entry has:

| Field | Description |
|-------|-------------|
| `id` | Unique URL-friendly identifier |
| `name` | Display name |
| `currency` | ISO 4217 currency code |
| `category` | `mutual_fund` or `etf` |
| `ter` | (ETF only) Total expense ratio in % |
| `ticker` | (ETF only) Yahoo Finance ticker |
| `fees` | `entry_fee` (%), `exit_fee` (%), `fixed_monthly` (EUR) |
| `source` | `{ type: "nlb_api" | "yahoo", ... }` |
| `output` | Relative path for generated CSV |

## NLB API

The NLB Skladi website exposes a public JSON endpoint for daily NAV data:

```
/content/.../unitvaluecomparator.fundsarchive.{fund_id}.json?dateMin=1990-01-01&dateMax=2099-12-31
```

Fund IDs are discoverable in the HTML of the [VEP tool page](https://www.nlbskladi.si/uporabni-izracuni/gibanje-vrednosti-enot-premozenja) as `fund-{id}` attributes. The extraction logic lives in `src/nlbapi/client.py`.
