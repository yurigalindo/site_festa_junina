from flask import Flask, redirect, url_for, session
import os # Moved import os to the top
# Removed base64, io, qrcode, datetime, and SQLAlchemy direct imports as they are now handled in utils.py and models.py

from .routes import rsvp_bp # Changed to relative import
from .models import db, RSVP # Changed to relative import
# Pix utilities are no longer directly used in app.py, they are used in the blueprint

# Adjusted Flask app initialization for templates at root and instance folder
app = Flask(__name__, template_folder='../templates', static_folder='../static', instance_relative_config=True)

# Ensure the instance folder exists before configuring the database URI
# or doing anything else that might depend on it.
try:
    os.makedirs(app.instance_path, exist_ok=True)
except OSError:
    # Handle the error appropriately if instance folder creation fails
    # For now, we'll let it raise if it's a real issue other than "already exists"
    pass 

app.config['SECRET_KEY'] = 'your_very_secret_key_here'
app.config['PIX_KEY'] = 'YOUR_ACTUAL_PIX_KEY_HERE' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rsvp.db' # This will be in instance/rsvp.db if instance_relative_config is True and path is not absolute
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure database URI to be in the instance folder
# This is a common pattern, ensures the db is not in the source tree.
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{app.instance_path}/rsvp.db"

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
    # The instance folder creation is now done earlier
    app.run(debug=True, port=5001) 