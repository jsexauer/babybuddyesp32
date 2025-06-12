# Example Secrets

class Secrets:
    # === Wi-Fi Credentials ===
    SSID = "xxx"
    PASSWORD = "xxx"

    # === BabyBuddy API Info ===
    BABYBUDDY_URL = "https://xxx/api"
    API_TOKEN = "xxx"
    CHILD_ID = 1

    HEADERS = {
            "Authorization": f"Token {API_TOKEN}",
            "Content-Type": "application/json"
        }

