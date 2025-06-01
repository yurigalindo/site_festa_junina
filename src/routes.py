from flask import Blueprint, render_template, request, redirect, url_for, session, current_app

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

    if request.method == 'POST':
        names = []
        error_message = None

        for i in range(1, num_people + 1):
            name = request.form.get(f'name_{i}')
            
            if not name:
                error_message = f"Por favor, informe o nome da pessoa {i}."
                submitted_names = [request.form.get(f'name_{k}') for k in range(1, num_people + 1)]
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
        if not phone_number:
            error = "Por favor, informe seu telefone para contato."
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
        "Estamos arrecadando 15 reais por convidados. Teremos comidas de Festa Junina, Quentão e Vinho Quente.<br>"
        f"O valor total da sua contribuição é de R$ {amount_str}.<br>"
        "Por favor, realize o pix utilizando o QR Code abaixo ou a chave Copia e Cola.<br>"
        "Após o pagamento, clique em 'Fiz o Pix!' para confirmar sua presença."
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

    names_str = ", ".join(names)

    try:
        new_rsvp = RSVP(
            city=city,
            group=group,
            num_people=num_people,
            names_str=names_str,
            phone=phone_number,
        )
        db.session.add(new_rsvp)
        db.session.commit()
        print(f"RSVP data saved to database: {names_str}")
    except Exception as e:
        db.session.rollback()
        print(f"Error saving RSVP to database: {e}")
        return render_template('error.html', error_message="Ocorreu um erro ao salvar sua confirmação. Tente novamente.")

    session.pop('city', None)
    session.pop('group', None)
    session.pop('number_of_people', None)
    session.pop('names', None)
    session.pop('phone_number', None)
    session.pop('pix_qr_code', None) 
    session.pop('amount', None)
    session.pop('pix_description', None)

    return render_template('confirmation.html', names=names_str, num_people=num_people)

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