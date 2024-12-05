from flask import Flask, jsonify, Blueprint
import requests
from config import Config
from flask_caching import Cache
import datetime

app = Flask(__name__)

# Create a blueprint for the team stats service
team_stats_blueprint = Blueprint('team_stats', __name__)

# Set cache for one day
cache = Cache(app, config={'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TIMEOUT': 86400})

# Register the blueprint with the main Flask app
app.register_blueprint(team_stats_blueprint, url_prefix='/team_stats')


# Helper function to get the current year
def get_current_year():
    return datetime.date.today().strftime("%Y")


# Helper function to fetch data from API
def fetch_data(url, api_key):
    try:
        response = requests.get(f"{url}?api_key={api_key}")
        response.raise_for_status()
        return response.json(), None
    except requests.exceptions.RequestException as e:
        return None, f"Error occurred fetching data: {e}"


# Helper function to safely extract values
def safe_get(data, key, default='N/A'):
    return data.get(key, default) if data else default


# Helper function to extract stats for different categories
def extract_stats(data, category, subcategory=None):
    stats = safe_get(data, category, {})
    if subcategory:
        return safe_get(stats, subcategory, 'N/A')
    return stats or 'N/A'


# Route to get team stats and set cache
@team_stats_blueprint.route('/<team_id>', methods=['GET'])
@cache.cached(timeout=86400, query_string=True)  # Cache stats for one day
def get_team_stats(team_id):
    api_key = Config.SPORTRADAR_API_KEY
    year = get_current_year()
    current_season = 'REG'

    # Set SportRadar API URLs
    statistics_url = f"https://api.sportradar.com/nfl/official/trial/v7/en/seasons/{year}/{current_season}/teams/{team_id}/statistics.json"
    standings_url = f"https://api.sportradar.com/nfl/official/trial/v7/en/seasons/{year}/{current_season}/standings/season.json"

    try:
        # Fetch data from SportRadar API (with error handling)
        statistics_data, statistics_error = fetch_data(statistics_url, api_key)
        standings_data, standings_error = fetch_data(standings_url, api_key)

        if statistics_error or standings_error:
            return jsonify({'error': statistics_error or standings_error}), 500

        # Get basic team info (set initial default value for wins/losses/ties)
        team_info = {
            'name': safe_get(statistics_data, 'name'),
            'alias': safe_get(statistics_data, 'alias'),
            'market': safe_get(statistics_data, 'market'),
            'wins': 'N/A',
            'losses': 'N/A',
            'ties': 'N/A'
        }

        # Get win/loss/tie record from standings and update values in team_info
        for conference in standings_data.get('conferences', []):
            for division in conference.get('divisions', []):
                for team in division.get('teams', []):
                    if team.get('id') == team_id:
                        team_info.update({
                            'wins': safe_get(team, 'wins'),
                            'losses': safe_get(team, 'losses'),
                            'ties': safe_get(team, 'ties')
                        })

        # Extract offensive stats
        team_info.update({
            'passing_yards': extract_stats(statistics_data.get('record', {}), 'passing', 'yards'),
            'rushing_yards': extract_stats(statistics_data.get('record', {}), 'rushing', 'yards'),
            'receiving_yards': extract_stats(statistics_data.get('record', {}), 'receiving', 'yards'),
            'total_touchdowns': extract_stats(statistics_data.get('record', {}), 'touchdowns', 'total'),
            'passing_touchdowns': extract_stats(statistics_data.get('record', {}), 'touchdowns', 'pass'),
            'rushing_touchdowns': extract_stats(statistics_data.get('record', {}), 'touchdowns', 'rush'),
            'receiving_touchdowns': extract_stats(statistics_data.get('record', {}), 'receiving', 'touchdowns')
        })

        # Extract defensive stats
        team_info.update({
            'sacks': extract_stats(statistics_data.get('record', {}), 'defense', 'sacks'),
            'interceptions': extract_stats(statistics_data.get('record', {}), 'defense', 'interceptions'),
            'forced_fumbles': extract_stats(statistics_data.get('record', {}), 'defense', 'forced_fumbles'),
            'opponents_passing_touchdowns': extract_stats(statistics_data.get('opponents', {}), 'touchdowns', 'pass'),
            'opponents_rushing_touchdowns': extract_stats(statistics_data.get('opponents', {}), 'touchdowns', 'rush'),
            'field_goals_made': extract_stats(statistics_data.get('record', {}), 'field_goals', 'made'),
            'kickoff_returns': extract_stats(statistics_data.get('record', {}), 'kickoffs', 'return_yards')
        })

        # Return stats as JSON
        return jsonify(team_info)

    # If errors encountered, return error message
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'An error occurred while fetching team data: {e}'}), 500


if __name__ == '__main__':
    app.run(debug=True)
