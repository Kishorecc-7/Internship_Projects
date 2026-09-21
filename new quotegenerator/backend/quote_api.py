import requests


QUOTE_API_URL = "https://zenquotes.io/api/random"


def fetch_random_quote():

    try:
        response = requests.get(
            QUOTE_API_URL,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        if not data:
            return None

        quote_data = data[0]

        quote_text = quote_data.get("q")
        author = quote_data.get("a")

        if not quote_text or not author:
            return None

        return {
            "quote": quote_text,
            "author": author
        }

    except (
        requests.RequestException,
        ValueError,
        KeyError,
        TypeError
    ):
        return None