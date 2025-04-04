# -*- coding: utf-8 -*-
from flask import Flask, request, Response, render_template, redirect, url_for, send_from_directory, jsonify, session
from flask_security import Security, SQLAlchemyUserDatastore, WebauthnUtil, auth_required
from datetime import datetime
from dotenv import load_dotenv
import os
import json
from models import db, User, Role, Credential, Entry
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    options_to_json,
    base64url_to_bytes
)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SECURITY_PASSWORD_SALT'] = os.getenv('SECURITY_PASSWORD_SALT')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECURITY_WEBAUTHN'] = True

# Initialize extensions
db.init_app(app)
user_datastore = SQLAlchemyUserDatastore(db, User, Role, Credential)
security = Security(app, user_datastore)

# Initialize database
with app.app_context():
    db.create_all()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    else:
        registration_password = request.form.get('registration_password')
        if registration_password != os.getenv('REGISTRATION_PASSWORD'):
            return jsonify({'error': 'Invalid registration password'}), 401
        email = request.form.get('email')
        if user_datastore.find_user(email=email):
            return jsonify({'error': 'User already exists'}), 400
        options = generate_registration_options(
            rp_id=request.host.split(',')[0],
            rp_name="Quem Paga a Boia Hoje?",
            user_name=email
    )
    json_options = options_to_json(options)
    session['registration_options'] = json_options
    return Response(response=json_options, content_type='application/json', status=200)

@app.route('/verify-registration', methods=['POST'])
def verify_registration():
    data = request.get_json()
    session_data_dict = json.loads(session['registration_options'])
    try:
        verification = verify_registration_response(
            credential=data,
            expected_challenge=base64url_to_bytes(session_data_dict['challenge']),
            expected_origin=f"https://{request.host.split(',')[0]}",
            expected_rp_id=request.host.split(',')[0]
        )
        user = user_datastore.create_user(
            email=session_data_dict['user']['id'],
            active=True
        )
        print("User created")
        credential = Credential(
            user=user,
            credential_id=verification.credential_id,
            public_key=verification.credential_public_key,
            sign_count=verification.sign_count
        )
        db.session.add(credential)
        db.session.commit()
        return jsonify({'status': 'success'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/favicon.png')
def favicon():
    return send_from_directory('static', 'favicon.png', mimetype='image/png')

@app.route('/', methods=['GET', 'POST'])
@auth_required('session')
def index():
    if request.method == 'POST':
        date = request.form['date']
        buyer = request.form['buyer']
        entry_type = request.form['type']
        value = request.form['value']
        
        # Ensure the date is in YYYY-MM-DD format
        date = datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
        
        # Create new entry using SQLAlchemy
        new_entry = Entry(
            date=date,
            buyer=buyer,
            type=entry_type,
            value=value
        )
        db.session.add(new_entry)
        db.session.commit()
        
        # Redirect to prevent form resubmission
        return redirect(url_for('index'))
    
    # Fetch the latest entry for each type based on date
    last_dinner = Entry.query.filter_by(type='Dinner')\
        .order_by(Entry.date.desc())\
        .first()
    
    last_lunch = Entry.query.filter_by(type='Lunch')\
        .order_by(Entry.date.desc())\
        .first()

    # Fetch the last 10 entries sorted by date
    last_10_entries = Entry.query\
        .order_by(Entry.date.desc())\
        .limit(10)\
        .all()

    # Pass current date to the template in YYYY-MM-DD format
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    return render_template('index.html', 
                         last_dinner=last_dinner, 
                         last_lunch=last_lunch, 
                         current_date=current_date, 
                         last_10_entries=last_10_entries)

if __name__ == '__main__':
    app.run(host='::', port=5000)
