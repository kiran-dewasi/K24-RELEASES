import requests


API_KEY = "k24-secret-key-123"
BASE_URL = "http://localhost:8001"


def main() -> None:
    response = requests.get(
        f"{BASE_URL}/api/vouchers",
        params={
            "start_date": "20260301",
            "end_date": "20260331",
            "page": 1,
            "limit": 50,
        },
        headers={"x-api-key": API_KEY},
        timeout=30,
    )

    print("Status:", response.status_code)
    data = response.json()
    print("Total count:", data.get("total_count"))
    print("Vouchers returned:", len(data.get("vouchers", [])))
    for v in data.get("vouchers", []):
        print(
            f"  Vch#{v.get('voucher_number')} | {v.get('voucher_type')} | date={v.get('date')}"
        )


if __name__ == "__main__":
    main()

