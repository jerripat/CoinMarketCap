import requests

# --- Ask user for a symbol ---
symbol = input("Enter the cryptocurrency symbol (e.g., BTC, ETH, DOGE): ").upper()

# --- CoinMarketCap Pro API endpoint ---
url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

# --- Headers with your API key ---
headers = {
    "Accepts": "application/json",
    "X-CMC_PRO_API_KEY": "cb88e221-51ee-4694-9f62-c12319dfefea"
}

# --- Parameters: specify the symbol you entered ---
params = {"symbol": symbol, "convert": "USD"}

# --- Make the request ---
response = requests.get(url, headers=headers, params=params)

# --- Handle the response ---
if response.status_code == 200:
    data = response.json()
    if symbol in data["data"]:
        coin = data["data"][symbol]
        name = coin["name"]
        price = coin["quote"]["USD"]["price"]
        change = coin["quote"]["USD"]["percent_change_24h"]
        market_cap = coin["quote"]["USD"]["market_cap"]

        print(f"\n{name} ({symbol})")
        print(f"Price: ${price:,.2f}")
        print(f"24h Change: {change:.2f}%")
        print(f"Market Cap: ${market_cap:,.0f}")
    else:
        print("Symbol not found in API response.")
else:
    print("Error:", response.status_code, response.text)
