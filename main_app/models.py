from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Player(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    position = db.Column(db.String, nullable=True)
    team_id = db.Column(db.String, nullable=False)
    team_name = db.Column(db.String, nullable=False)
