from flask import Blueprint, jsonify, Flask
import requests

app = Flask(__name__)

# Create a blueprint for the recent games service
recent_games_blueprint = Blueprint('recent_games', __name__)

# URL for the game results cache microservice
GAME_RESULTS_URL = 'http://localhost:5001/recent_games'


# Route to get recent game results
@recent_games_blueprint.route('/recent_games', methods=['GET'])
def get_recent_games():
    try:
        # Fetching recent game results from the game results cache microservice
        response = requests.get(GAME_RESULTS_URL)
        response.raise_for_status()
        game_results_cache = response.json().get('recent_games', [])

        return jsonify({"recent_games": game_results_cache})
    except requests.RequestException as e:
        return jsonify({"error": "Unable to fetch recent game results."}), 500
