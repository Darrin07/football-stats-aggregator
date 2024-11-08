from flask import Flask, render_template, request, redirect, url_for
import requests
from config import Config
from flask_caching import Cache
from models import db, Player
import os

app = Flask(__name__)
app.config.from_object(Config)

# simple cache
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Initialize the database
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'teams.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Creating tables if they don't exist
with app.app_context():
    db.create_all()

# Home Page
@app.route('/')
def home():
    return render_template('index.html')

# Search Page
@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        search_type = request.form.get('search_type')
        player_name = request.form.get('player_name')

        if search_type == 'player' and player_name:
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
                return render_template('search.html', error=f"No player found with the name '{player_name}'.")

            except requests.exceptions.RequestException as e:
                return render_template('search.html', error=f"An error occurred: {e}")

        # If team search is added later, handle here
        return render_template('search.html', error="Please enter a valid search term.")

    return render_template('search.html')


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
                                'receiving_yards': stats.get('receiving', {}).get('yards', 0),
                                'receptions': stats.get('receiving', {}).get('receptions', 0),
                                'receiving_touchdowns': stats.get('receiving', {}).get('touchdowns', 0),
                                # Add more stats here as required
                            }
                        else:
                            # Aggregate if stats for the same season exist across different entries
                            season_stat_map[year]['games_played'] += stats.get('games_played', 0)
                            season_stat_map[year]['receiving_yards'] += stats.get('receiving', {}).get('yards', 0)
                            season_stat_map[year]['receptions'] += stats.get('receiving', {}).get('receptions', 0)
                            season_stat_map[year]['receiving_touchdowns'] += stats.get('receiving', {}).get('touchdowns', 0)

        unique_offense_stats = list(season_stat_map.values())

        return render_template('player_details.html', player=player_data, offense_stats=unique_offense_stats)

    except requests.exceptions.RequestException as e:
        return render_template('player_details.html', error=f"An error occurred: {e}")


if __name__ == "__main__":
    app.run(debug=True)
