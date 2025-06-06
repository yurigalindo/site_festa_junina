from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
import re # Add re for regex validation

from .models import db, RSVP
from .utils import generate_pix_payload


rsvp_bp = Blueprint('rsvp', __name__, template_folder='../templates')

# Hardcoded city and group data
CITY_GROUP_OPTIONS = {
    "São José dos Campos": ["Família do Yuri", "Cia. do Trailer", "Teatro da Cidade", "Família Froes", "Chicos e Chicas", "Javanês"],
    "Taubaté": ["Família da Laura", "Café 🏳️‍🌈", "Impostoras","Primos e Agregados","Dança Comigo","Mariposa Brasileiro","Med Lucinda"]
}

@rsvp_bp.route('/', methods=['GET', 'POST'])
@rsvp_bp.route('/welcome')
def welcome():
    # Clear any existing session data when the user lands on the welcome page
    session.pop('city', None)
    session.pop('group', None)
    session.pop('number_of_people', None)
    session.pop('names', None)
    session.pop('phone_number', None)
    session.pop('pix_qr_code', None) 
    session.pop('amount', None)
    return render_template('welcome.html')


@rsvp_bp.route('/city', methods=['GET', 'POST'])
def select_city():
    if request.method == 'POST':
        city = request.form.get('city')
        if city and city in CITY_GROUP_OPTIONS:
            session['city'] = city
            return redirect(url_for('rsvp.select_group'))
        else:
            error = "Por favor, selecione uma cidade válida."
            return render_template('city_selection.html', cities=CITY_GROUP_OPTIONS.keys(), error=error)
    
    # Session clearing moved to the welcome route
    # session.pop('city', None)
    # session.pop('group', None)
    # session.pop('number_of_people', None)
    # session.pop('names', None)
    # session.pop('phone_number', None)

    return render_template('city_selection.html', cities=CITY_GROUP_OPTIONS.keys())

@rsvp_bp.route('/group', methods=['GET', 'POST'])
def select_group():
    if 'city' not in session:
        return redirect(url_for('rsvp.select_city'))

    city = session['city']
    groups = CITY_GROUP_OPTIONS.get(city, [])

    if request.method == 'POST':
        group = request.form.get('group')
        if group and group in groups:
            session['group'] = group
            return redirect(url_for('rsvp.number_of_people'))
        else:
            error = "Por favor, selecione um grupo válido."
            return render_template('group_selection.html', city=city, groups=groups, error=error)

    session.pop('group', None)
    session.pop('number_of_people', None)
    session.pop('names', None)
    session.pop('phone_number', None)
    return render_template('group_selection.html', city=city, groups=groups)

@rsvp_bp.route('/names', methods=['GET', 'POST'])
def names_form():
    if 'number_of_people' not in session:
        return redirect(url_for('rsvp.number_of_people')) 
    if 'city' not in session or 'group' not in session:
        return redirect(url_for('rsvp.select_city'))

    num_people = session['number_of_people']
    # Regex to allow letters (including accented) and spaces. Allows empty strings initially, 
    # but the 'not name' check below handles empty required fields.
    name_pattern = re.compile(r"^[a-zA-Z ]+$")

    if request.method == 'POST':
        names = []
        error_message = None
        submitted_names = [request.form.get(f'name_{k}') or "" for k in range(1, num_people + 1)]

        for i in range(1, num_people + 1):
            name = request.form.get(f'name_{i}')
            
            if not name:
                error_message = f"Por favor, informe o nome da pessoa {i}."
                return render_template('names_form.html',
                                       num_people=num_people,
                                       error=error_message,
                                       names=submitted_names)
            
            # Validate name format
            if not name_pattern.match(name):
                error_message = f"O nome da pessoa {i} ('{name}') deve conter apenas letras (sem acentos) e espaços."
                return render_template('names_form.html',
                                       num_people=num_people,
                                       error=error_message,
                                       names=submitted_names)

            names.append(name)
        
        session['names'] = names
        return redirect(url_for('rsvp.contact_form'))

    retrieved_names = session.get('names', [])

    expected_names = [None] * num_people

    for i in range(min(len(retrieved_names), num_people)):
        expected_names[i] = retrieved_names[i]
    
    return render_template(
        'names_form.html',
        num_people=num_people,
        names=expected_names
    )

@rsvp_bp.route('/contact', methods=['GET', 'POST'])
def contact_form():
    if 'names' not in session:
        return redirect(url_for('rsvp.names_form'))
    if 'city' not in session or 'group' not in session:
        return redirect(url_for('rsvp.select_city'))
    if 'number_of_people' not in session:
        return redirect(url_for('rsvp.number_of_people'))

    if request.method == 'POST':
        phone_number = request.form.get('phone_number')
        error = None
        if not phone_number:
            error = "Por favor, informe seu telefone para contato."
        elif not phone_number.isdigit():
            error = "O telefone deve conter apenas números."
        elif len(phone_number) > 20:
            error = "O telefone deve ter no máximo 20 dígitos."
        
        if error:
            return render_template('contact_phone_form.html', error=error, phone_number=phone_number)
        
        session['phone_number'] = phone_number
        return redirect(url_for('rsvp.pix_payment_form'))

    phone_number = session.get('phone_number', '')
    return render_template('contact_phone_form.html', phone_number=phone_number)

@rsvp_bp.route('/pix-payment', methods=['GET'])
def pix_payment_form():
    if 'number_of_people' not in session or 'names' not in session or 'phone_number' not in session:
        if 'city' not in session or 'group' not in session:
            return redirect(url_for('rsvp.select_city'))
        if 'number_of_people' not in session: 
            return redirect(url_for('rsvp.number_of_people'))
        if 'names' not in session:
            return redirect(url_for('rsvp.names_form'))
        if 'phone_number' not in session:
            return redirect(url_for('rsvp.contact_form'))
        return redirect(url_for('rsvp.select_city')) 

    num_people = session['number_of_people']
    names = session['names']
    
    amount = 15 * num_people
    amount_str = f"{amount:.2f}"
    
    pix_description = ", ".join(names)
    if len(pix_description) > 70:
        pix_description = pix_description[:67] + "..."

    pix_payload, pix_image_b64 = generate_pix_payload(
        amount=num_people,
        names=pix_description
    )
    
    
    session['amount'] = amount
    session['pix_payload'] = pix_payload
    session['pix_description'] = pix_description

    payment_instructions = (
        "Estamos arrecadando 15 reais por convidados. Teremos comidas de Festa Junina, Quentão e Vinho Quente.<br><br>"
        "Por favor, realize o pix utilizando o QR Code abaixo ou a chave Copia e Cola.<br>"
        "A conta é do Yuri, marido da Laura.<br><br>"
        '<strong style="font-size: 1.2em; color: red;">Após o pagamento, clique em "Fiz o Pix!" para confirmar sua presença.</strong>'
    )

    return render_template(
        'pix_payment.html',
        qr_image=pix_image_b64,
        pix_payload=pix_payload,
        amount_str=amount_str,
        instructions=payment_instructions
    )

@rsvp_bp.route('/confirmation')
def confirmation():
    required_session_keys = ['city', 'group', 'number_of_people', 'names', 'phone_number', 'pix_description', 'amount']
    for key in required_session_keys:
        if key not in session:
            print(f"Missing session key: {key} during confirmation step.")
            return redirect(url_for('rsvp.select_city')) 

    city = session.get('city')
    group = session.get('group')
    num_people = session.get('number_of_people')
    names = session.get('names')
    phone_number = session.get('phone_number')

    # For database storage
    names_str_db = ", ".join(names)

    # For display on the confirmation page
    if not names: # Should not happen if validation is correct
        display_names = ""
    elif len(names) == 1:
        display_names = names[0]
    elif len(names) == 2:
        display_names = " e ".join(names)
    else:
        display_names = ", ".join(names[:-1]) + " e " + names[-1]

    try:
        new_rsvp = RSVP(
            city=city,
            group=group,
            num_people=num_people,
            names_str=names_str_db, # Use the original comma-separated string for DB
            phone=phone_number,
        )
        db.session.add(new_rsvp)
        db.session.commit()
        print(f"RSVP data saved to database: {names_str_db}")
    except Exception as e:
        db.session.rollback()
        print(f"Error saving RSVP to database: {e}")
        return render_template('error.html', error_message="Ocorreu um erro ao salvar sua confirmação. Por favor, tente novamente. Se já fez o Pix, não precisa fazer novamente, apenas clique em Fiz o Pix!")

    session.pop('city', None)
    session.pop('group', None)
    session.pop('number_of_people', None)
    session.pop('names', None)
    session.pop('phone_number', None)
    session.pop('pix_qr_code', None) 
    session.pop('amount', None)
    session.pop('pix_description', None)

    event_address = current_app.config.get('EVENT_ADDRESS', 'LOCAL A SER DEFINIDO') # Get address from config

    return render_template('confirmation.html', names=display_names, num_people=num_people, event_address=event_address)

@rsvp_bp.route('/number-of-people', methods=['GET', 'POST'])
def number_of_people():
    if 'city' not in session or 'group' not in session:
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
                    if session.get('number_of_people') != num_people:
                        session.pop('names', None)
                    session['number_of_people'] = num_people
                    return redirect(url_for('rsvp.names_form'))
            except ValueError:
                error = "Por favor, insira um número válido."

        if error:
            return render_template('number_of_people.html', error=error, num_people=num_people_str)

    num_people_value = session.get('number_of_people', '') 
    return render_template('number_of_people.html', num_people=num_people_value)

@rsvp_bp.route('/confirmed-guests')
def confirmed_guests():
    # Get all RSVPs ordered by city and group
    rsvps = RSVP.query.order_by(RSVP.city, RSVP.group, RSVP.timestamp).all()
    
    # Calculate total number of people
    total_people = sum(rsvp.num_people for rsvp in rsvps)
    
    # Group RSVPs by city and group for better display
    grouped_rsvps = {}
    for rsvp in rsvps:
        city = rsvp.city
        group = rsvp.group
        
        if city not in grouped_rsvps:
            grouped_rsvps[city] = {}
        if group not in grouped_rsvps[city]:
            grouped_rsvps[city][group] = []
            
        grouped_rsvps[city][group].append(rsvp)
    
    return render_template('confirmed_guests.html', 
                         total_people=total_people, 
                         grouped_rsvps=grouped_rsvps,
                         total_rsvps=len(rsvps)) 