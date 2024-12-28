from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
import json
import os
from datetime import datetime, timedelta
import hashlib
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # Generate a secure secret key

# Configuration file path
CONFIG_FILE = 'alarm_config.json'

# Default configuration
DEFAULT_CONFIG = {
    'alarm_time': '07:00',
    'fade_duration': 30  # Duration in minutes for light fade-in
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

# Password protection
def check_password(password):
    # TODO: In production, use a secure password hash stored in a separate config file
    correct_password_hash = hashlib.sha256('your_secure_password'.encode()).hexdigest()
    return hashlib.sha256(password.encode()).hexdigest() == correct_password_hash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if check_password(request.form['password']):
            session['authenticated'] = True
            return redirect(url_for('index'))
        return render_template('login.html', error='Invalid password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    config = load_config()
    if request.method == 'POST':
        config['alarm_time'] = request.form['alarm_time']
        config['fade_duration'] = int(request.form['fade_duration'])
        save_config(config)
        return redirect(url_for('index'))
    return render_template('index.html', config=config)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
