import requests
from config import Config


def fetch_player_data(access_level, language, player_id, data_format):
    """Fetch player data from Sportradar API."""
    api_key = Config.SPORTRADAR_API_KEY
    base_url = "https://api.sportradar.com/nfl/official/{access_level}/v7/{language}/players/{player_id}/profile.{" \
               "format} "
    url = base_url.format(access_level=access_level, language=language, player_id=player_id, format=data_format)

    headers = {
        "apikey": api_key
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return None
