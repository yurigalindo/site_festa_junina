from flask import Flask, render_template, request, redirect, url_for, session
import base64
import io
import qrcode
import datetime # Added for timestamp
from flask_sqlalchemy import SQLAlchemy # Added for SQLAlchemy
# from sheets_utils import append_to_sheet # Removed Google Sheets integration
from rsvp_flow.routes import rsvp_bp # Import the new blueprint

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_very_secret_key_here'  # Replace with a real secret key
app.config['PIX_KEY'] = 'YOUR_ACTUAL_PIX_KEY_HERE' # IMPORTANT: Replace with your real Pix key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rsvp.db' # Added SQLite URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Optional: disable modification tracking

db = SQLAlchemy(app) # Initialize SQLAlchemy

# Define the RSVP model
class RSVP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    city = db.Column(db.String(100), nullable=False)
    group = db.Column(db.String(100), nullable=False)
    num_people = db.Column(db.Integer, nullable=False)
    names_str = db.Column(db.String(500), nullable=False) # Storing names as a comma-separated string
    veg_options_str = db.Column(db.String(100), nullable=False) # Storing veg options as comma-separated string of "True"/"False"
    phone = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f'<RSVP {self.id}>'

# Create database tables if they don't exist
with app.app_context():
    db.create_all()

app.register_blueprint(rsvp_bp) # Register the blueprint

# Dummy routes for previous and next steps for now
@app.route('/')
def index():
    # Redirect to the first step of the RSVP flow
    return redirect(url_for('rsvp.select_city'))

@app.route('/names-vegetarian')
def names_vegetarian():
    return "Next step: Enter names and vegetarian status."

@app.route('/names', methods=['GET', 'POST'])
def names_form():
    if 'number_of_people' not in session:
        return redirect(url_for('number_of_people')) # Or perhaps number_of_people
    if 'city' not in session or 'group' not in session: # Check for city and group
        return redirect(url_for('rsvp.select_city'))

    num_people = session['number_of_people']

    if request.method == 'POST':
        names = []
        vegetarian_options = []
        error_message = None # Initialize error message

        for i in range(1, num_people + 1):
            name = request.form.get(f'name_{i}')
            vegetarian = request.form.get(f'vegetarian_{i}') == 'on' # Checkbox value is 'on' if checked
            
            if not name:
                error_message = f"Por favor, informe o nome da pessoa {i}."
                # If there's an error, collect all submitted data to re-populate the form
                submitted_names = [request.form.get(f'name_{k}') for k in range(1, num_people + 1)]
                submitted_veg_options = [request.form.get(f'vegetarian_{k}') == 'on' for k in range(1, num_people + 1)]
                return render_template('names_form.html',
                                       num_people=num_people,
                                       error=error_message,
                                       names=submitted_names,
                                       vegetarian_options=submitted_veg_options)

            names.append(name)
            vegetarian_options.append(vegetarian)
        
        session['names'] = names
        session['vegetarian_options'] = vegetarian_options
        return redirect(url_for('contact_form'))

    # GET request:
    retrieved_names = session.get('names', [])
    retrieved_vegetarian_options = session.get('vegetarian_options', [])

    # Ensure lists are correctly sized for the template, padded with defaults
    expected_names = [None] * num_people
    expected_veg_options = [False] * num_people

    for i in range(min(len(retrieved_names), num_people)):
        expected_names[i] = retrieved_names[i]
    
    for i in range(min(len(retrieved_vegetarian_options), num_people)):
        expected_veg_options[i] = retrieved_vegetarian_options[i]

    return render_template(
        'names_form.html',
        num_people=num_people,
        names=expected_names,
        vegetarian_options=expected_veg_options
    )

@app.route('/contact', methods=['GET', 'POST'])
def contact_form():
    if 'names' not in session or 'vegetarian_options' not in session: # Check for names and vegetarian options
        return redirect(url_for('names_form'))
    if 'city' not in session or 'group' not in session: # Check for city and group
        return redirect(url_for('rsvp.select_city'))
    if 'number_of_people' not in session:
        return redirect(url_for('number_of_people'))

    if request.method == 'POST':
        phone_number = request.form.get('phone_number')
        if not phone_number:
            error = "Por favor, informe seu telefone para contato."
            # Pass back the attempted phone_number on error
            return render_template('contact_phone_form.html', error=error, phone_number=phone_number)
        
        # Basic validation could be expanded here (e.g., regex for phone format)
        session['phone_number'] = phone_number
        return redirect(url_for('pix_payment_form')) # Next step: Pix payment

    # For GET request, retrieve previous value if any (e.g. if user clicks back)
    phone_number = session.get('phone_number', '')
    return render_template('contact_phone_form.html', phone_number=phone_number)

# --- Pix Helper Functions ---
def generate_pix_payload(pix_key, merchant_name, merchant_city, amount_str, description, txid="***"):
    """
    Generates a static Pix BRCode payload.
    txid="***" for static QR codes that can be paid multiple times.
    For unique transactions, generate a unique txid.
    Amount is formatted as a string, e.g., "150.00"
    """
    # Payload Format Version
    payload_format_indicator = "000201"
    # Merchant Account Information (Simplified for static QR)
    # Using a fixed GUID for Pix. Recebedor Digital (PSP aagencia e conta)
    # This is a common structure, but for specific PSPs, details might vary slightly.
    # Key Type: 00 (Chave Aleatória/EVP), 01 (CPF), 02 (CNPJ), 03 (Telefone), 04 (Email)
    # Assuming pix_key is a phone number, email or EVP. For CPF/CNPJ, formatting might be needed.
    merchant_account_info = f"0014BR.GOV.BCB.PIX01{len(pix_key):02}{pix_key}"
    
    # Merchant Category Code (0000 for generic)
    merchant_category_code = "52040000" # Typically 0000 for generic or specific codes like 5311 for dept stores. Using 0000 as safe default or 5204 (generic money transfer)
    
    # Transaction Currency (986 for BRL)
    transaction_currency = "5303986"
    
    # Transaction Amount
    transaction_amount = f"54{len(amount_str):02}{amount_str}"
    
    # Country Code (BR)
    country_code = "5802BR"
    
    # Merchant Name (up to 25 chars)
    merchant_name_val = merchant_name[:25].upper() # Ensure it's uppercase and fits length
    merchant_name_field = f"59{len(merchant_name_val):02}{merchant_name_val}"
    
    # Merchant City (up to 15 chars)
    merchant_city_val = merchant_city[:15].upper()
    merchant_city_field = f"60{len(merchant_city_val):02}{merchant_city_val}"
    
    # Additional Data Field Template (for transaction ID and description)
    # ID 05 for Transaction ID (txid)
    # ID 50 for Description if needed (but specs say description is in QR code, usually through txid details with PSP)
    # For simplicity, we'll put a simple TXID. The "description" from specs is embedded in the payment by user,
    # or associated by the PSP with the TXID if it's a dynamic QR.
    # Here, the description refers to data that helps the payer, not necessarily part of this minimal BRCode structure.
    # The problem states "description: names of all confirmed people" for the QR Code.
    # This description is for the *payer's* reference, not usually part of the core BRCode unless using dynamic QR.
    # We'll make the TXID based on a simplified version of names, or keep it "***" for generic static.
    # For this use case, a static QR is fine, but the "description" field of Pix is more complex.
    # Let's use the provided description in a way that might be visible to the payer if the app supports it.
    # A common way is to make txid somewhat descriptive if it's short enough or use a specific field.
    # The BRCode standard has specific fields for this.
    # Simplified Additional Data: Using a simple TXID. The description is often shown by the banking app
    # when it resolves the Pix key and amount.
    
    additional_data_field_txid = f"05{len(txid):02}{txid}"
    additional_data_field = f"62{len(additional_data_field_txid):02}{additional_data_field_txid}"

    # CRC16 Checksum (calculated at the end)
    # Placeholder for now, will calculate later
    payload_without_crc = (
        payload_format_indicator +
        "26" + str(len(merchant_account_info)).zfill(2) + merchant_account_info + # ID 26 - Merchant Account Information
        merchant_category_code +
        transaction_currency +
        transaction_amount +
        country_code +
        merchant_name_field +
        merchant_city_field +
        additional_data_field
    )
    
    # Calculate CRC16
    crc16 = calculate_crc16(payload_without_crc)
    
    return payload_without_crc + "6304" + crc16

def calculate_crc16(payload):
    """Calculates CRC16-CCITT for Pix payload."""
    crc = 0xFFFF
    polynomial = 0x1021
    
    for byte in payload.encode('utf-8'):
        crc ^= (byte << 8)
        for _ in range(8):
            if (crc & 0x8000):
                crc = (crc << 1) ^ polynomial
            else:
                crc = crc << 1
    return format(crc & 0xFFFF, '04X')

def generate_qr_code_base64(payload):
    """Generates a QR code from the payload and returns a base64 encoded image string."""
    img = qrcode.make(payload)
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str
# --- End Pix Helper Functions ---

@app.route('/pix-payment', methods=['GET'])
def pix_payment_form():
    if 'number_of_people' not in session or 'names' not in session or 'phone_number' not in session:
        # Not enough data to proceed, redirect to an earlier step
        # Check for all necessary session variables from previous steps
        if 'city' not in session or 'group' not in session:
            return redirect(url_for('rsvp.select_city'))
        if 'number_of_people' not in session:
            return redirect(url_for('number_of_people'))
        if 'names' not in session:
            return redirect(url_for('names_form'))
        if 'phone_number' not in session:
            return redirect(url_for('contact_form'))
        # Fallback if a specific check is missed, though the above should cover it
        return redirect(url_for('rsvp.select_city')) 

    num_people = session['number_of_people']
    names = session['names']
    
    amount = 15 * num_people
    amount_str = f"{amount:.2f}" # Format as X.XX
    
    # Description for Pix: names of all confirmed people
    # Max length for description field in some Pix standards can be short.
    # Keep it concise.
    pix_description = ", ".join(names)
    if len(pix_description) > 70: # Truncate if too long, as an example limit
        pix_description = pix_description[:67] + "..."

    # For static QR, TXID is often "***"
    # For the "description" to show to the user as part of QR data, it can be part of TXID if short,
    # or some PSPs use specific fields in dynamic QRs.
    # The prompt says "description: names of all confirmed people" for the QR code itself.
    # We will use a simplified transaction ID or a generic one.
    # The BRCode structure mainly carries key, amount, merchant name, city.
    # The "description" the user sees on their bank app often comes from the PSP resolving the key/txid.
    # Let's use a generic TXID for simplicity as per common static QR practice.
    txid = "***" 
    # If you want a more dynamic TXID based on names, ensure it's short and URL-safe characters.
    # Example: txid = "".join(filter(str.isalnum, pix_description))[:25] 


    pix_payload = generate_pix_payload(
        pix_key=app.config['PIX_KEY'],
        merchant_name="Arraia da Laura", # As per project context
        merchant_city="SJC", # Or more generic if not tied to one, but spec implies event context
        amount_str=amount_str,
        description=pix_description, # This description is more for internal reference or if PSP uses it
        txid=txid # Static QR codes often use "***"
    )
    
    qr_image_base64 = generate_qr_code_base64(pix_payload)
    
    session['amount'] = amount
    session['pix_payload'] = pix_payload # This is the "copia e cola"
    session['pix_description'] = pix_description # For Google Sheets

    payment_instructions = (
        f"O valor total da sua contribuição é de R$ {amount_str}.<br>"
        "Por favor, faça o pagamento via Pix utilizando o QR Code abaixo ou a chave Copia e Cola.<br>"
        "Após o pagamento, clique em 'Fiz o Pix!' para confirmar sua presença."
    )

    return render_template(
        'pix_payment.html',
        qr_image=qr_image_base64,
        pix_payload=pix_payload,
        amount_str=amount_str,
        instructions=payment_instructions
    )

@app.route('/confirmation') # Placeholder for confirmation page
def confirmation():
    # This is where you would typically save to Google Sheets.
    # For now, just show a thank you message.
    # Retrieve data from session to display or save

    # Ensure all required data is in session before proceeding
    required_session_keys = ['city', 'group', 'number_of_people', 'names', 'vegetarian_options', 'phone_number', 'pix_description', 'amount']
    for key in required_session_keys:
        if key not in session:
            # If any key is missing, redirect to an earlier appropriate step or an error page.
            # This is a simplified redirect; a real app might have a more specific error page
            # or redirect to the last valid step.
            print(f"Missing session key: {key} during confirmation step.")
            return redirect(url_for('rsvp.select_city')) 

    city = session.get('city')
    group = session.get('group')
    num_people = session.get('number_of_people')
    names = session.get('names')
    vegetarian_options = session.get('vegetarian_options') # This is a list of booleans
    phone_number = session.get('phone_number')

    # Convert lists to strings for storage
    names_str = ", ".join(names)
    veg_options_str = ", ".join(map(str, vegetarian_options)) # Converts [True, False] to "True, False"

    # Store data in SQLite database
    try:
        new_rsvp = RSVP(
            city=city,
            group=group,
            num_people=num_people,
            names_str=names_str,
            veg_options_str=veg_options_str,
            phone=phone_number,
        )
        db.session.add(new_rsvp)
        db.session.commit()
        print(f"RSVP data saved to database: {names_str}")
    except Exception as e:
        db.session.rollback()
        print(f"Error saving RSVP to database: {e}")
        # Optionally, render an error page or flash a message to the user
        # For now, we'll just print the error and proceed to the confirmation page
        # but ideally, you'd handle this more gracefully.
        return render_template('error.html', error_message="Ocorreu um erro ao salvar sua confirmação. Tente novamente.")

    # Clear the session after successful RSVP or if there was an attempt to save
    # You might want to clear session selectively or based on success
    session.pop('city', None)
    session.pop('group', None)
    session.pop('number_of_people', None)
    session.pop('names', None)
    session.pop('vegetarian_options', None)
    session.pop('phone_number', None)
    session.pop('pix_qr_code', None) # Also clear QR code if stored
    session.pop('amount', None)
    session.pop('pix_description', None)
    # Do not clear 'confirmed_details' if you want to display it on the thank you page

    return render_template('confirmation.html', names=names_str, num_people=num_people)

@app.route('/number-of-people', methods=['GET', 'POST'])
def number_of_people():
    if 'city' not in session or 'group' not in session: # Check for city and group
        return redirect(url_for('rsvp.select_city'))

    if request.method == 'POST':
        num_people_str = request.form.get('num_people')
        error = None
        if not num_people_str:
            error = "Por favor, informe o número de pessoas."
        else:
            try:
                num_people = int(num_people_str)
                if not 1 <= num_people <= 10:
                    error = "O número de pessoas deve ser entre 1 e 10."
                else:
                    # If number_of_people changes, clear associated session data
                    if session.get('number_of_people') != num_people:
                        session.pop('names', None)
                        session.pop('vegetarian_options', None)
                    session['number_of_people'] = num_people
                    return redirect(url_for('names_form')) # Corrected redirect
            except ValueError:
                error = "Por favor, insira um número válido."

        if error:
            # Pass back the attempted value on error
            return render_template('number_of_people.html', error=error, num_people=num_people_str)

    # GET request: Retrieve from session and pass to template
    num_people_value = session.get('number_of_people', '') 
    return render_template('number_of_people.html', num_people=num_people_value)

if __name__ == '__main__':
    app.run(debug=True, port=5001)