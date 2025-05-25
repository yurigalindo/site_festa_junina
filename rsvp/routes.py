from flask import Blueprint, render_template, request, session, redirect, url_for

rsvp_blueprint = Blueprint('rsvp', __name__, template_folder='templates')

CITIES = {
    "sjc": "São José dos Campos",
    "taubate": "Taubaté"
}

GROUPS = {
    "sjc": ["Grupo SJC 1", "Grupo SJC 2"],
    "taubate": ["Grupo Taubaté A", "Grupo Taubaté B"]
}

@rsvp_blueprint.route('/', methods=['GET', 'POST'])
def select_city():
    if request.method == 'POST':
        city = request.form.get('city')
        if city in CITIES:
            session['city'] = city
            return redirect(url_for('.select_group'))
        # Handle error: city not selected or invalid
        return render_template('select_city.html', cities=CITIES, error="Por favor, selecione uma cidade.")
    return render_template('select_city.html', cities=CITIES)

@rsvp_blueprint.route('/group', methods=['GET', 'POST'])
def select_group():
    city = session.get('city')
    if not city or city not in CITIES:
        return redirect(url_for('.select_city')) # Redirect if city not in session or invalid

    if request.method == 'POST':
        group = request.form.get('group')
        if group in GROUPS.get(city, []):
            session['group'] = group
            # Redirect to the next step (e.g., number of people)
            return redirect(url_for('.next_step_placeholder')) # Placeholder for now
        # Handle error: group not selected or invalid
        return render_template('select_group.html', city_name=CITIES[city], groups=GROUPS.get(city, []), error="Por favor, selecione um grupo.")
    
    return render_template('select_group.html', city_name=CITIES[city], groups=GROUPS.get(city, []))

# Placeholder for the next step
@rsvp_blueprint.route('/next_step')
def next_step_placeholder():
    return f"Cidade: {session.get('city')}, Grupo: {session.get('group')} - Próximo passo!" 