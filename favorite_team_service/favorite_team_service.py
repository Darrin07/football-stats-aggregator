

from flask import Blueprint, request, jsonify, Flask
import requests

app = Flask(__name__)

# Create a blueprint for the favorite team service
favorite_team_blueprint = Blueprint('favorite_team', __name__)

# URL for the game results cache microservice
GAME_RESULTS_URL = 'http://localhost:5001/recent_games'


# Route to get recent results of the favorite team
@favorite_team_blueprint.route('/favorite_team', methods=['GET'])
def get_favorite_team_results():
    team_name = request.args.get('team')
    if not team_name:
        return jsonify({"error": "Team name is required."}), 400

    try:
        # Fetching recent game results from the game results cache microservice
        response = requests.get(GAME_RESULTS_URL)
        response.raise_for_status()
        game_results_cache = response.json().get('recent_games', [])

        # Filter game results for the selected favorite team
        team_results = [game for game in game_results_cache if
                        game['team_1'] == team_name or game['team_2'] == team_name]

        if not team_results:
            return jsonify({"message": f"No recent results found for team {team_name}."}), 404

        return jsonify({"team": team_name, "recent_results": team_results})
    except requests.RequestException as e:
        return jsonify({"error": "Unable to fetch recent game results."}), 500
