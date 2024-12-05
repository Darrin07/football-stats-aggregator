# team_rankings_service.py

from flask import Blueprint, jsonify, Flask
import requests

app = Flask(__name__)

# Create a blueprint for the team rankings service
team_rankings_blueprint = Blueprint('team_rankings', __name__)

# URL for the team stats cache microservice
TEAM_STATS_URL = 'http://localhost:5001/team_stats'


# Route to get team rankings
@team_rankings_blueprint.route('/team_rankings', methods=['GET'])
def get_team_rankings():
    try:
        # Fetching team stats from the team stats cache microservice
        response = requests.get(TEAM_STATS_URL)
        response.raise_for_status()
        team_stats_cache = response.json().get('team_stats', {})

        # Sorting teams by number of wins in descending order
        rankings = sorted(team_stats_cache.items(), key=lambda x: x[1]['wins'], reverse=True)
        return jsonify({"rankings": [{"team": team, "wins": stats["wins"], "losses": stats["losses"]} for team, stats in
                                     rankings]})
    except requests.RequestException as e:
        return jsonify({"error": "Unable to fetch team stats."}), 500
