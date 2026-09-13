import os
import time
import datetime
import pandas as pd

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


try:
    from pycoingecko import CoinGeckoAPI
    COINGECKO_AVAILABLE = True
except ImportError:
    COINGECKO_AVAILABLE = False

CSV_FILE = "crypto_data.csv"
TOP_N    = 10


def build_driver(headless: bool = True) -> "webdriver.Chrome":
    """Return a configured Chrome WebDriver."""
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


def scrape_coinmarketcap(headless: bool = True) -> list[dict]:
    """Scrape top-10 coins from CoinMarketCap using Selenium."""
    driver = build_driver(headless)
    coins  = []
    try:
        driver.get("https://coinmarketcap.com/")
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "table tbody tr")
        ))
        time.sleep(3)          # let JS fully hydrate

        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")[:TOP_N]
        for row in rows:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 8:
                    continue

                rank        = cells[1].text.strip()
                name_el     = cells[2]
                name        = name_el.find_element(By.CSS_SELECTOR, "p").text.strip()
                symbol      = name_el.find_elements(By.TAG_NAME, "p")[1].text.strip() if len(
                                  name_el.find_elements(By.TAG_NAME, "p")) > 1 else ""
                price       = cells[3].text.strip().replace("\n", "")
                change_24h  = cells[5].text.strip().replace("\n", "")
                market_cap  = cells[7].text.strip().replace("\n", "")

                coins.append({
                    "rank":        rank,
                    "name":        name,
                    "symbol":      symbol,
                    "price":       price,
                    "change_24h":  change_24h,
                    "market_cap":  market_cap,
                    "timestamp":   datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "source":      "CoinMarketCap",
                })
            except Exception:
                continue
    finally:
        driver.quit()
    return coins



def fetch_coingecko() -> list[dict]:
    """Fetch top-10 coins from CoinGecko public API."""
    cg   = CoinGeckoAPI()
    data = cg.get_coins_markets(
        vs_currency="usd",
        order="market_cap_desc",
        per_page=TOP_N,
        page=1,
        sparkline=False,
        price_change_percentage="24h",
    )
    coins = []
    for i, c in enumerate(data, start=1):
        change = c.get("price_change_percentage_24h") or 0.0
        coins.append({
            "rank":       str(i),
            "name":       c["name"],
            "symbol":     c["symbol"].upper(),
            "price":      f"${c['current_price']:,.2f}",
            "change_24h": f"{change:+.2f}%",
            "market_cap": f"${c['market_cap']:,.0f}",
            "timestamp":  datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source":     "CoinGecko",
        })
    return coins



def save_to_csv(coins: list[dict], filepath: str = CSV_FILE) -> None:
    """Append coin data to CSV, writing header only when file is new."""
    df = pd.DataFrame(coins)
    write_header = not os.path.exists(filepath)
    df.to_csv(filepath, mode="a", header=write_header, index=False)
    print(f"  → Saved {len(df)} rows to '{filepath}'")


def load_csv(filepath: str = CSV_FILE) -> pd.DataFrame | None:
    """Return the full historical CSV as a DataFrame, or None if absent."""
    if os.path.exists(filepath):
        return pd.read_csv(filepath)
    return None




def filter_coins(
    coins: list[dict],
    min_price: float | None = None,
    max_price: float | None = None,
    min_change: float | None = None,
) -> list[dict]:
    
    def parse_price(p: str) -> float:
        return float(p.replace("$", "").replace(",", "").strip())

    def parse_change(c: str) -> float:
        return float(c.replace("%", "").replace("+", "").strip())

    result = []
    for coin in coins:
        try:
            price  = parse_price(coin["price"])
            change = parse_change(coin["change_24h"])
            if min_price  is not None and price  < min_price:  continue
            if max_price  is not None and price  > max_price:  continue
            if min_change is not None and change < min_change: continue
            result.append(coin)
        except ValueError:
            result.append(coin)   # keep if unparseable
    return result



def run(
    use_selenium: bool = True,
    headless: bool = True,
    min_price: float | None = None,
    max_price: float | None = None,
    min_change: float | None = None,
    save: bool = True,
) -> list[dict]:
    """
    Collect top-10 cryptocurrency data, optionally filter, and save to CSV.

    Returns the list of coin dicts.
    """
    print(f"\n{'='*55}")
    print("  Cryptocurrency Price Tracker")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*55}")

    coins: list[dict] = []

    if use_selenium and SELENIUM_AVAILABLE:
        print("  Scraping CoinMarketCap via Selenium …")
        try:
            coins = scrape_coinmarketcap(headless=headless)
            if coins:
                print(f"  ✓ Scraped {len(coins)} coins from CoinMarketCap.")
        except Exception as e:
            print(f"  ✗ Selenium scraping failed: {e}")

    if not coins:
        if COINGECKO_AVAILABLE:
            print("  Falling back to CoinGecko API …")
            try:
                coins = fetch_coingecko()
                print(f"  ✓ Fetched {len(coins)} coins from CoinGecko.")
            except Exception as e:
                print(f"  ✗ CoinGecko fetch failed: {e}")
        else:
            print("  ✗ No data source available.")
            return []

    if any(v is not None for v in [min_price, max_price, min_change]):
        before = len(coins)
        coins  = filter_coins(coins, min_price, max_price, min_change)
        print(f"  Filtered: {before} → {len(coins)} coins")

    df = pd.DataFrame(coins)
    if not df.empty:
        print("\n" + df[["rank", "name", "symbol", "price", "change_24h", "market_cap"]].to_string(index=False))

    if save and coins:
        save_to_csv(coins)

    print(f"\n{'='*55}\n")
    return coins


if __name__ == "__main__":
    run(use_selenium=True, headless=True)
