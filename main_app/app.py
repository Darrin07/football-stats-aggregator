from flask import Flask, render_template, request, redirect, url_for
import requests
from config import Config
from flask_caching import Cache
from models import db, Player
import os
import json

from team_rankings_service.team_rankings_service import team_rankings_blueprint
from recent_games_service.recent_games_service import recent_games_blueprint
from favorite_team_service.favorite_team_service import favorite_team_blueprint
from team_stats_service.teamStats import team_stats_blueprint

app = Flask(__name__)
app.config.from_object(Config)

# Simple cache
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Initialize the database
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), '../teams.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Creating tables if they don't exist
with app.app_context():
    db.create_all()


# Home Page
@app.route('/')
def home():
    return render_template('index.html')


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

# Route to get team stats
@app.route('/team-search', methods=['GET', 'POST'])
def team_search():
    if request.method == 'POST':
        team_name = request.form.get('team_name')

        if team_name:
            teams_url = f"https://api.sportradar.com/nfl/official/trial/v7/en/teams.json?api_key={Config.SPORTRADAR_API_KEY}"
            try:
                teams_response = requests.get(teams_url)
                teams_response.raise_for_status()
                teams_data = teams_response.json()

                # Find the matching team_id
                team_id = None
                for team in teams_data.get('teams', []):
                    if team.get('name', '').lower() == team_name.lower():
                        team_id = team['id']
                        break

                if team_id:
                    # Fetch and display the stats directly
                    year = get_current_year()
                    current_season = 'REG'
                    statistics_url = f"https://api.sportradar.com/nfl/official/trial/v7/en/seasons/{year}/{current_season}/teams/{team_id}/statistics.json"
                    standings_url = f"https://api.sportradar.com/nfl/official/trial/v7/en/seasons/{year}/{current_season}/standings/season.json"

                    # Fetch data from SportRadar API (with error handling)
                    statistics_data, statistics_error = fetch_data(statistics_url, Config.SPORTRADAR_API_KEY)
                    standings_data, standings_error = fetch_data(standings_url, Config.SPORTRADAR_API_KEY)

                    if statistics_error or standings_error:
                        return render_template('team_search.html', error=statistics_error or standings_error)

                    # Create the team data object
                    team_info = {
                        'name': safe_get(statistics_data, 'name'),
                        'alias': safe_get(statistics_data, 'alias'),
                        'market': safe_get(statistics_data, 'market'),
                        'wins': 'N/A',
                        'losses': 'N/A',
                        'ties': 'N/A'
                    }

                    # Update team_info with win/loss/tie record
                    for conference in standings_data.get('conferences', []):
                        for division in conference.get('divisions', []):
                            for team in division.get('teams', []):
                                if team.get('id') == team_id:
                                    team_info.update({
                                        'wins': safe_get(team, 'wins'),
                                        'losses': safe_get(team, 'losses'),
                                        'ties': safe_get(team, 'ties')
                                    })

                    # Add offensive and defensive stats
                    team_info.update({
                        'passing_yards': extract_stats(statistics_data.get('record', {}), 'passing', 'yards'),
                        'rushing_yards': extract_stats(statistics_data.get('record', {}), 'rushing', 'yards'),
                        'receiving_yards': extract_stats(statistics_data.get('record', {}), 'receiving', 'yards'),
                        'total_touchdowns': extract_stats(statistics_data.get('record', {}), 'touchdowns', 'total'),
                        'passing_touchdowns': extract_stats(statistics_data.get('record', {}), 'touchdowns', 'pass'),
                        'rushing_touchdowns': extract_stats(statistics_data.get('record', {}), 'touchdowns', 'rush'),
                        'receiving_touchdowns': extract_stats(statistics_data.get('record', {}), 'receiving', 'touchdowns'),
                        'sacks': extract_stats(statistics_data.get('record', {}), 'defense', 'sacks'),
                        'interceptions': extract_stats(statistics_data.get('record', {}), 'defense', 'interceptions'),
                        'forced_fumbles': extract_stats(statistics_data.get('record', {}), 'defense', 'forced_fumbles'),
                        'field_goals_made': extract_stats(statistics_data.get('record', {}), 'field_goals', 'made'),
                        'kickoff_returns': extract_stats(statistics_data.get('record', {}), 'kickoffs', 'return_yards')
                    })

                    return render_template('team_details.html', team=team_info)

                # No matching team found
                return render_template('team_search.html', error="Team not found.")

            except requests.exceptions.RequestException as e:
                return render_template('team_search.html', error=f"An error occurred while fetching team data: {e}")

    return render_template('team_search.html')



# @app.route('/team-search', methods=['GET', 'POST'])
# def team_search():
#     if request.method == 'POST':
#         team_name = request.form.get('team_name')
#
#         if team_name:
#             # Instead of fetching from the microservice, we use the hardcoded team dictionary.
#             if team_name.lower() == "Chiefs":
#                 hardcoded_team_data = {
#                     "id": "6680d28d-d4d2-49f6-aace-5292d3ec02c2",
#                     "name": "Kansas City Chiefs",
#                     "wins": 8,
#                     "losses": 4,
#                     "ties": 0,
#                     "passing_yards": 3200,
#                     "rushing_yards": 1400,
#                     "receiving_yards": 3100,
#                     "total_touchdowns": 42,
#                     "passing_touchdowns": 28,
#                     "rushing_touchdowns": 10,
#                     "receiving_touchdowns": 4,
#                     "sacks": 30,
#                     "interceptions": 12,
#                     "forced_fumbles": 8,
#                     "field_goals_made": 25,
#                     "kickoff_returns": 600
#                 }
#                 # Render the team_details.html page with the hardcoded data
#                 return render_template('team_details.html', team=hardcoded_team_data)
#
#             return render_template('team_search.html', error="Team not found.")
#
#     return render_template('team_search.html')


# Player Search Page
@app.route('/player-search', methods=['GET', 'POST'])
def player_search():
    if request.method == 'POST':
        player_name = request.form.get('player_name')
        if player_name:
            # Check if player already exists in the database
            existing_player = Player.query.filter(Player.name.ilike(f"%{player_name}%")).first()
            if existing_player:
                return redirect(url_for('player_details', player_id=existing_player.id))

            # Get League Hierarchy to get all team IDs
            api_key = app.config['SPORTRADAR_API_KEY']
            league_url = f"https://api.sportradar.com/nfl/official/trial/v7/en/league/hierarchy.json?api_key={api_key}"

            try:
                league_response = requests.get(league_url)
                league_response.raise_for_status()
                league_data = league_response.json()

                # Loop through teams to get their rosters and search for the player
                for conference in league_data['conferences']:
                    for division in conference['divisions']:
                        for team in division['teams']:
                            team_id = team['id']
                            team_name = f"{team['market']} {team['name']}"
                            roster_url = f"https://api.sportradar.com/nfl/official/trial/v7/en/teams/{team_id}/full_roster.json?api_key={api_key}"

                            # Cache roster API call to reduce API usage
                            cache_key = f"roster_{team_id}"
                            team_response = cache.get(cache_key)
                            if not team_response:
                                team_response = requests.get(roster_url)
                                if team_response.status_code == 200:
                                    team_response = team_response.json()
                                    cache.set(cache_key, team_response, timeout=86400)
                                else:
                                    continue

                            team_roster = team_response
                            for player in team_roster.get('players', []):
                                if player_name.lower() in player['name'].lower():
                                    player_id = player['id']

                                    # Save player to the database
                                    new_player = Player(
                                        id=player_id,
                                        name=player['name'],
                                        position=player.get('position'),
                                        team_id=team_id,
                                        team_name=team_name
                                    )
                                    db.session.add(new_player)
                                    db.session.commit()

                                    # Redirect to player details
                                    return redirect(url_for('player_details', player_id=player_id))

                # If player not found
                return render_template('player_search.html', error=f"No player found with the name '{player_name}'.")

            except requests.exceptions.RequestException as e:
                return render_template('player_search.html', error=f"An error occurred: {e}")

    return render_template('player_search.html')


# Player Details Page
@app.route('/players/<player_id>')
def player_details(player_id):
    api_key = Config.SPORTRADAR_API_KEY
    url = f"https://api.sportradar.com/nfl/official/trial/v7/en/players/{player_id}/profile.json?api_key={api_key}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        player_data = response.json()

        # Filter offense stats to exclude preseason and only keep regular and postseason stats
        all_offense_stats = player_data.get("seasons", [])
        season_stat_map = {}

        for season in all_offense_stats:
            year = season['year']
            # Only include regular and postseason stats
            if season['type'] in ['REG', 'POST']:
                for team in season['teams']:
                    if team.get('statistics'):
                        stats = team['statistics']

                        # Initialize or accumulate stats for each season
                        if year not in season_stat_map:
                            season_stat_map[year] = {
                                'year': year,
                                'team_name': f"{team['market']} {team['name']}",
                                'games_played': stats.get('games_played', 0),
                                'passing_yards': stats.get('passing', {}).get('yards', 0),
                                'passing_touchdowns': stats.get('passing', {}).get('touchdowns', 0),
                                'rushing_yards': stats.get('rushing', {}).get('yards', 0),
                                'rushing_touchdowns': stats.get('rushing', {}).get('touchdowns', 0),
                                'receiving_yards': stats.get('receiving', {}).get('yards', 0),
                                'receptions': stats.get('receiving', {}).get('receptions', 0),
                                'receiving_touchdowns': stats.get('receiving', {}).get('touchdowns', 0),
                                'sacks': stats.get('defense', {}).get('sacks', 0),
                                'interceptions': stats.get('defense', {}).get('interceptions', 0)
                            }
                        else:
                            # Aggregate if stats for the same season exist across different entries
                            season_stat_map[year]['games_played'] += stats.get('games_played', 0)
                            season_stat_map[year]['passing_yards'] += stats.get('passing', {}).get('yards', 0)
                            season_stat_map[year]['passing_touchdowns'] += stats.get('passing', {}).get('touchdowns', 0)
                            season_stat_map[year]['rushing_yards'] += stats.get('rushing', {}).get('yards', 0)
                            season_stat_map[year]['rushing_touchdowns'] += stats.get('rushing', {}).get('touchdowns', 0)
                            season_stat_map[year]['receiving_yards'] += stats.get('receiving', {}).get('yards', 0)
                            season_stat_map[year]['receptions'] += stats.get('receiving', {}).get('receptions', 0)
                            season_stat_map[year]['receiving_touchdowns'] += stats.get('receiving', {}).get(
                                'touchdowns', 0)
                            season_stat_map[year]['sacks'] += stats.get('defense', {}).get('sacks', 0)
                            season_stat_map[year]['interceptions'] += stats.get('defense', {}).get('interceptions', 0)

        unique_offense_stats = list(season_stat_map.values())

        return render_template('player_details.html', player=player_data, offense_stats=unique_offense_stats)

    except requests.exceptions.RequestException as e:
        return render_template('player_details.html', error=f"An error occurred: {e}")


# Add Favorite Team
@app.route('/add-favorite-team', methods=['POST'])
def add_favorite_team():
    team_name = request.form.get('team_name')

    if team_name:
        # Since we aren't using user accounts, we'll use local storage.
        # Alternatively, we can simulate saving favorites to a JSON file for demonstration purposes.

        try:
            with open('favorite_teams.json', 'r') as file:
                favorite_teams = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            favorite_teams = []

        if team_name not in favorite_teams:
            favorite_teams.append(team_name)

        with open('favorite_teams.json', 'w') as file:
            json.dump(favorite_teams, file, indent=4)

        return redirect(url_for('favorite_teams'))

    return redirect(url_for('team_search'))


@app.route('/recent-games', methods=['GET'])
def recent_games():
    api_key = Config.SPORTRADAR_API_KEY
    # Replace with the actual endpoint for recent games from Sportradar
    # For example, we assume there is a 'schedule' endpoint to get recent games
    url = f"https://api.sportradar.com/nfl/official/trial/v7/en/games/2023/REG/schedule.json?api_key={api_key}"

    try:
        # Cache the recent games data for a short period (e.g., 10 minutes)
        cache_key = "recent_games_data"
        recent_games_data = cache.get(cache_key)

        if not recent_games_data:
            # Fetch live data from Sportradar if not cached
            response = requests.get(url)
            response.raise_for_status()
            response_data = response.json()

            # Parse the response to extract recent games
            recent_games_data = []
            for week in response_data['weeks']:
                for game in week['games']:
                    if game.get('status') == 'closed':  # Only include completed games
                        recent_games_data.append({
                            "home_team": game['home']['name'],
                            "home_score": game['scoring']['home_points'],
                            "away_team": game['away']['name'],
                            "away_score": game['scoring']['away_points']
                        })

            # Cache the data to reduce API requests
            cache.set(cache_key, recent_games_data, timeout=600)  # Cache for 10 minutes

        return render_template('recent_games.html', recent_games=recent_games_data)

    except requests.exceptions.RequestException as e:
        return render_template('recent_games.html', error=f"An error occurred while fetching recent games: {e}")

# Team Rankings Page
@app.route('/team-rankings', methods=['GET'])
def team_rankings():
    api_key = app.config['SPORTRADAR_API_KEY']  # Use app config to access API key
    url = f"https://api.sportradar.com/nfl/official/trial/v7/en/seasons/2023/REG/standings.json?api_key={api_key}"

    try:
        # Check if the response is cached
        cache_key = "team_rankings_data"
        response_data = cache.get(cache_key)

        if not response_data:
            # Fetch live data from Sportradar if not in cache
            response = requests.get(url)
            response.raise_for_status()
            response_data = response.json()
            cache.set(cache_key, response_data, timeout=3600)  # Cache for 1 hour

        # Process data to extract relevant ranking information
        rankings = []
        for conference in response_data['conferences']:
            for division in conference['divisions']:
                for team in division['teams']:
                    rankings.append({
                        "name": f"{team['market']} {team['name']}",
                        "wins": team['record']['overall']['wins'],
                        "losses": team['record']['overall']['losses']
                    })

        # Sort teams by their wins (descending order)
        sorted_rankings = sorted(rankings, key=lambda x: x['wins'], reverse=True)

        return render_template('team_rankings.html', rankings=sorted_rankings)

    except requests.exceptions.RequestException as e:
        return render_template('team_rankings.html', error=f"An error occurred while fetching team rankings: {e}")


# register blueprints for each microservice
app.register_blueprint(team_rankings_blueprint)
app.register_blueprint(recent_games_blueprint)
app.register_blueprint(favorite_team_blueprint)
app.register_blueprint(team_stats_blueprint, url_prefix='/team_stats')

if __name__ == "__main__":
    app.run(debug=True)
