from flask import Flask, render_template, request, redirect, url_for, session
import base64
import io
import qrcode
import datetime # Added for timestamp
from sheets_utils import append_to_sheet # Added for Google Sheets integration
from rsvp_flow.routes import rsvp_bp # Import the new blueprint

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_very_secret_key_here'  # Replace with a real secret key
app.config['PIX_KEY'] = 'YOUR_ACTUAL_PIX_KEY_HERE' # IMPORTANT: Replace with your real Pix key
app.config['GOOGLE_SHEET_ID'] = 'YOUR_GOOGLE_SHEET_ID_FROM_CONFIG_OR_ENV' # Placeholder
# For a real application, load PIX_KEY from environment variables or a secure config file.

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
        for i in range(1, num_people + 1):
            name = request.form.get(f'name_{i}')
            vegetarian = request.form.get(f'vegetarian_{i}') == 'on' # Checkbox value is 'on' if checked
            
            if not name:
                # Basic validation: ensure all names are provided
                error = f"Por favor, informe o nome da pessoa {i}."
                return render_template('names_form.html', num_people=num_people, error=error)

            names.append(name)
            vegetarian_options.append(vegetarian)
        
        session['names'] = names
        session['vegetarian_options'] = vegetarian_options
        return redirect(url_for('contact_form'))

    return render_template('names_form.html', num_people=num_people)

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
    
    session['pix_amount'] = amount
    session['pix_payload'] = pix_payload # This is the "copia e cola"
    session['pix_description_for_sheets'] = pix_description # For Google Sheets

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
    city = session.get('city', 'N/A')
    group = session.get('group', 'N/A')
    num_people = session.get('number_of_people', 0)
    names = session.get('names', [])
    vegetarian_options = session.get('vegetarian_options', [])
    phone_number = session.get('phone_number', 'N/A')
    pix_amount = session.get('pix_amount', 0.0)
    pix_description_gs = session.get('pix_description_for_sheets', 'N/A')

    # Prepare data for Google Sheets
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    names_str = ", ".join(names)
    veg_options_str = ", ".join(["Sim" if veg else "Não" for veg in vegetarian_options])

    sheet_data = [
        timestamp, city, group, num_people, names_str, 
        veg_options_str, phone_number, pix_amount, pix_description_gs
    ]

    sheet_save_error = None
    if not append_to_sheet(sheet_data):
        sheet_save_error = "Houve um problema ao salvar sua confirmação na planilha. Não se preocupe, seus dados de sessão estão seguros. Por favor, entre em contato com o organizador."
        # In a real app, you might want to log this error more robustly
        # or offer the user a way to retry or send the data manually.

    # Clear session after processing if desired, or keep for "back" navigation review
    # For this flow, we'll assume we can clear parts or all of it after confirmation.
    # For simplicity, we won't clear it yet.

    confirmation_html_parts = [
        "<!DOCTYPE html>",
        "<html lang=\"pt-BR\">",
        "<head>",
        "    <meta charset=\"UTF-8\">",
        "    <title>Confirmação</title>",
        "    <style>",
        "        body { font-family: sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; text-align: center; }",
        "        .container { background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); display: inline-block; text-align: left; max-width: 600px; margin-top: 20px; }",
        "        h1 { color: #5cb85c; }",
        "        h3, h4 { color: #333; margin-top: 1.5em; }",
        "        ul { list-style-type: none; padding-left: 0; }",
        "        li { background-color: #eee; margin-bottom: 5px; padding: 8px; border-radius: 3px; }",
        "        p { margin: 0.5em 0; }",
        "        .error-message { color: red; font-weight: bold; margin-top: 1em; padding: 10px; border: 1px solid red; background-color: #ffebeb; border-radius: 4px; }", # Added error style
        "    </style>",
        "</head>",
        "<body>",
        "    <div class=\"container\">"
    ]

    if sheet_save_error:
        confirmation_html_parts.append(f"        <div class=\"error-message\">{sheet_save_error}</div>")

    confirmation_html_parts.extend([
        "        <h1>Obrigado!</h1>",
        "        <p>Sua presença foi registrada com sucesso!</p>",
        "        <h3>Detalhes da sua Confirmação:</h3>",
        f"        <p><strong>Cidade:</strong> {city}</p>",
        f"        <p><strong>Grupo:</strong> {group}</p>",
        f"        <p><strong>Número de Pessoas:</strong> {num_people}</p>",
        f"        <p><strong>Telefone:</strong> {phone_number}</p>",
        f"        <p><strong>Valor Pago (Pix):</strong> R$ {pix_amount:.2f}</p>",
        f"        <p><strong>Descrição Pix (para Planilha):</strong> {pix_description_gs}</p>",
        "        <h4>Participantes:</h4>",
        "        <ul>"
    ])
    if names:
        for i, name in enumerate(names):
            veg_status = "Sim" if vegetarian_options and i < len(vegetarian_options) and vegetarian_options[i] else "Não"
            confirmation_html_parts.append(f"            <li>{name} (Vegetariano: {veg_status})</li>")
    confirmation_html_parts.append("        </ul>")
    confirmation_html_parts.append("        <br><p><a href=\"/\">Iniciar Novo RSVP</a></p>")
    confirmation_html_parts.append("    </div>")
    confirmation_html_parts.append("</body>")
    confirmation_html_parts.append("</html>")
    
    return "\n".join(confirmation_html_parts)

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
                    session['number_of_people'] = num_people
                    return redirect(url_for('names_form')) # Corrected redirect
            except ValueError:
                error = "Por favor, insira um número válido."

        if error:
            return render_template('number_of_people.html', error=error, num_people=num_people_str)

    return render_template('number_of_people.html')

if __name__ == '__main__':
    app.run(debug=True, port=5001)