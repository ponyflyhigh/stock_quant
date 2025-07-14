import requests

try:
    response = requests.get('https://api.binance.com/api/v3/ping', timeout=10)
    if response.status_code == 200:
        print("Binance API reachable")
    else:
        print(f"Binance API returned status: {response.status_code}")
except Exception as e:
    print(f"Error connecting to Binance API: {e}")
