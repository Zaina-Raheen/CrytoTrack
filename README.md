# Cryptocurrency Price Tracker

Real-time crypto price scraper with a live web dashboard.

## Features
- Selenium scraper targeting CoinMarketCap (JS-rendered pages)
- CoinGecko API fallback (no browser required)
- Timestamped CSV logging for historical trend analysis
- Price / 24h-change filtering
- Headless browser mode
- Interactive HTML dashboard with sparklines, live refresh, filter UI

## Setup

```bash
pip install -r requirements.txt
```

## Usage

### Run the scraper (all data, saved to CSV)
```bash
python scraper.py
```

### Use in your own scripts
```python
from scraper import run, load_csv, filter_coins

# Fetch live data (auto-saves to crypto_data.csv)
coins = run()

# Only coins with price > $1 000 and positive 24h change
coins = run(min_price=1000, min_change=0)

# Load full history
df = load_csv()
print(df.tail(20))
```

### Open the dashboard
Open `dashboard.html` in any modern browser.  
The dashboard pulls data directly from the CoinGecko public API.

## CSV output format
| rank | name | symbol | price | change_24h | market_cap | timestamp | source |
|------|------|--------|-------|------------|------------|-----------|--------|

## Scheduled scraping (Linux/Mac)
Add to crontab to log data every 5 minutes:
```
*/5 * * * * cd /path/to/crypto_tracker && python scraper.py
```
