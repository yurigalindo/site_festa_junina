import os # Moved import os to the top
from dotenv import load_dotenv

load_dotenv() # Ensure .env is loaded

from flask import Flask, redirect, url_for, session, request, current_app, render_template # Added request, current_app, render_template

from .routes import rsvp_bp # Changed to relative import
from .models import db, RSVP # Changed to relative import
# Pix utilities are no longer directly used in app.py, they are used in the blueprint

# Adjusted Flask app initialization for templates at root and instance folder
app = Flask(__name__, template_folder='../templates', static_folder='../static', instance_relative_config=True)

# Set the instance path to be at the project root level
app.instance_path = os.path.abspath(os.path.join(app.root_path, '..', 'instance'))

# Ensure the instance folder exists before configuring the database URI
# or doing anything else that might depend on it.
try:
    os.makedirs(app.instance_path, exist_ok=True)
except OSError:
    # Handle the error appropriately if instance folder creation fails
    # For now, we'll let it raise if it's a real issue other than "already exists"
    pass 

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['PIX_KEY'] = os.getenv('PIX_KEY')
app.config['ACCESS_PIN'] = os.getenv('ACCESS_PIN') # Added for PIN protection
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

@app.before_request
def require_pin_access():
    # Allow access to the 'access_denied' route and static files without PIN
    if request.endpoint and (request.endpoint == 'access_denied' or request.endpoint.startswith('static')):
        return

    master_pin = current_app.config.get('ACCESS_PIN')

    if not master_pin:
        print("CRITICAL: ACCESS_PIN environment variable is not set. Site access is blocked.")
        if request.endpoint != 'access_denied': # Avoid redirect loop
             return redirect(url_for('access_denied', error="config_error"))
        return 

    if session.get('pin_verified'):
        return

    provided_pin = request.args.get('access_pin')

    if provided_pin and provided_pin == master_pin:
        session['pin_verified'] = True
        # Redirect to remove the access_pin from the URL query parameters
        clean_path = request.path
        return redirect(clean_path)
    else:
        error_reason = "invalid_pin" if provided_pin else "no_pin"
        if request.endpoint != 'access_denied': # Avoid redirect loop
            return redirect(url_for('access_denied', error=error_reason))

app.register_blueprint(rsvp_bp) # Register the blueprint

# Route for access denied page
@app.route('/access-denied')
def access_denied():
    error_type = request.args.get('error')
    title = "Acesso Restrito"
    message = "Você não tem permissão para acessar esta página."
    instructions = "Por favor, utilize o link de acesso com o PIN correto."

    if error_type == "config_error":
        title = "Erro de Configuração"
        message = "O sistema de acesso não está configurado corretamente."
        instructions = "Por favor, entre em contato com o administrador do site."
    elif error_type == "invalid_pin":
        title = "PIN Inválido"
        message = "O PIN fornecido no link de acesso é inválido."
        instructions = "Por favor, verifique o link e tente novamente. Certifique-se de que o PIN tem 18 dígitos."
    elif error_type == "no_pin":
        title = "PIN Necessário"
        message = "Este site requer um PIN para acesso."
        instructions = "Por favor, utilize o link de acesso que contém o PIN."
    
    return render_template('access_denied.html', title=title, message=message, instructions=instructions), 403

# Main index route, redirects to the blueprint's starting point
@app.route('/')
def index():
    return redirect(url_for('rsvp.welcome'))

# Pix Helper Functions and RSVP Model have been moved to utils.py and models.py respectively.

if __name__ == '__main__':
    # The instance folder creation is now done earlier
    app.run(debug=True, port=5001) 