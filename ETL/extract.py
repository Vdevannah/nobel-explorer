import requests


LAUREATES_URL = "https://api.nobelprize.org/2.1/laureates"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def fetch_laureates_page(limit: int = 25, offset: int = 0) -> dict:
    params = {
        "limit": limit,
        "offset": offset
    }

    response = requests.get(
        LAUREATES_URL,
        headers=HEADERS,
        params=params,
        timeout=10
    )
    response.raise_for_status()
    return response.json()


def fetch_all_laureates(page_size: int = 100) -> list[dict]:
    all_laureates = []
    offset = 0

    while True:
        data = fetch_laureates_page(limit=page_size, offset=offset)
        laureates = data.get("laureates", [])

        if not laureates:
            break

        all_laureates.extend(laureates)
        offset += len(laureates)

        total_count = data.get("meta", {}).get("count")
        if total_count is not None and len(all_laureates) >= total_count:
            break

    return all_laureates


if __name__ == "__main__":
    laureates = fetch_all_laureates(page_size=100)
    print("Total laureates extracted:", len(laureates))
