from flask import Flask, redirect, url_for, session
# Removed base64, io, qrcode, datetime, and SQLAlchemy direct imports as they are now handled in utils.py and models.py

from rsvp_flow.routes import rsvp_bp # Import the blueprint
from models import db, RSVP # Import db instance and RSVP model
# Pix utilities are no longer directly used in app.py, they are used in the blueprint

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_very_secret_key_here'
app.config['PIX_KEY'] = 'YOUR_ACTUAL_PIX_KEY_HERE' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rsvp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app) # Initialize SQLAlchemy with the app

# Create database tables if they don't exist
# This requires the RSVP model to be imported before create_all is called.
with app.app_context():
    # RSVP model is imported from models.py
    db.create_all()

app.register_blueprint(rsvp_bp) # Register the blueprint

# Main index route, redirects to the blueprint's starting point
@app.route('/')
def index():
    return redirect(url_for('rsvp.select_city'))

# Pix Helper Functions and RSVP Model have been moved to utils.py and models.py respectively.

if __name__ == '__main__':
    app.run(debug=True, port=5001)