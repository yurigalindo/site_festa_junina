from flask_sqlalchemy import SQLAlchemy
import datetime

# Initialize SQLAlchemy instance. It will be bound to the Flask app in app.py
db = SQLAlchemy()

class RSVP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    city = db.Column(db.String(100), nullable=False)
    group = db.Column(db.String(100), nullable=False)
    num_people = db.Column(db.Integer, nullable=False)
    names_str = db.Column(db.String(500), nullable=False)  # Storing names as a comma-separated string
    phone = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f'<RSVP {self.id}>' 