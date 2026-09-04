import requests
import json

url = "https://api.nobelprize.org/2.1/laureates"

headers = {
    "User-Agent": "Mozilla/5.0"
}

params = {
    "nobelPrizeYear": 1954,
    "nobelPrizeCategory": "che"
}

response = requests.get(
    url,
    headers=headers,
    params=params,
    timeout=10
)

print("Status code:", response.status_code)
print("Content-Type:", response.headers.get("Content-Type"))

if response.status_code == 200:
    data = response.json()
    print(json.dumps(data, indent=2))
else:
    print("Request failed.")
    print(response.text[:1000])