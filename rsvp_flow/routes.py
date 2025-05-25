from flask import Blueprint, render_template, request, redirect, url_for, session

rsvp_bp = Blueprint('rsvp', __name__, url_prefix='/rsvp', template_folder='../templates')

# Hardcoded city and group data
CITY_GROUP_OPTIONS = {
    "São José dos Campos": ["Amigos do Noivo", "Amigas da Noiva", "Família do Noivo", "Família da Noiva", "Amigos dos Pais"],
    "Taubaté": ["Amigos de Taubaté", "Família de Taubaté", "Trabalho"]
}

@rsvp_bp.route('/', methods=['GET', 'POST'])
@rsvp_bp.route('/city', methods=['GET', 'POST'])
def select_city():
    if request.method == 'POST':
        city = request.form.get('city')
        if city and city in CITY_GROUP_OPTIONS:
            session['city'] = city
            return redirect(url_for('rsvp.select_group'))
        else:
            # User might have manipulated the form or selected an invalid option
            error = "Por favor, selecione uma cidade válida."
            return render_template('city_selection.html', cities=CITY_GROUP_OPTIONS.keys(), error=error)
    
    # Clear previous selections if user revisits this step
    session.pop('city', None)
    session.pop('group', None)
    session.pop('number_of_people', None)
    session.pop('names', None)
    session.pop('vegetarian_options', None)
    session.pop('phone_number', None)

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
            # Redirect to the next step in the main app, which is number_of_people
            return redirect(url_for('number_of_people')) 
        else:
            error = "Por favor, selecione um grupo válido."
            return render_template('group_selection.html', city=city, groups=groups, error=error)

    # Clear subsequent selections if user revisits this step
    session.pop('group', None)
    session.pop('number_of_people', None)
    session.pop('names', None)
    session.pop('vegetarian_options', None)
    session.pop('phone_number', None)
    return render_template('group_selection.html', city=city, groups=groups) 