from flask import Flask, render_template, redirect, url_for, flash, request
from extensions import db  # Import db from the new file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Initialize app and configurations
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Replace with a secure key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///zeno.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database and login manager
from extensions import db
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Import models and forms
from models import User, Note
from forms import LoginForm, RegistrationForm, TranscribeForm

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_request
def create_tables():
    db.create_all()

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_pw = generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    notes = Note.query.filter_by(user_id=current_user.id).order_by(Note.timestamp.desc()).all()
    return render_template('dashboard.html', notes=notes)

import requests

def transcribe_with_deepgram(audio_file):
    # Retrieve your Deepgram API key from configuration or environment variable
    DEEPGRAM_API_KEY = app.config.get('DEEPGRAM_API_KEY')
    headers = {
        'Authorization': f'Token {DEEPGRAM_API_KEY}',
        'Content-Type': 'application/octet-stream'
    }
    url = "https://api.deepgram.com/v1/listen"
    
    # Read the binary data from the audio file
    audio_data = audio_file.read()
    
    response = requests.post(url, headers=headers, data=audio_data)
    response_data = response.json()
    
    try:
        transcript = response_data['results']['channels'][0]['alternatives'][0]['transcript']
    except (KeyError, IndexError):
        transcript = "Transcription failed. Please try again."
    
    return transcript

@app.route('/transcribe', methods=['GET', 'POST'])
@login_required
def transcribe():
    form = TranscribeForm()
    if form.validate_on_submit():
        # Call the Deepgram API instead of simulating transcription
        transcript = transcribe_with_deepgram(form.audio_file.data)
        
        new_note = Note(content=transcript, user_id=current_user.id, timestamp=datetime.utcnow())
        db.session.add(new_note)
        db.session.commit()
        flash('Transcription completed and note saved!')
        return redirect(url_for('dashboard'))
    return render_template('transcribe.html', form=form)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
