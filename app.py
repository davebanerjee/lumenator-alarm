from flask import Flask, render_template, request, redirect, url_for, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect, CSRFError
from functools import wraps
import json
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import hashlib
import secrets

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=['20 per day', '5 per hour'],
    storage_uri='memory://',
)

CONFIG_FILE = 'alarm_config.json'
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

def check_password(password):
    correct_password_hash = hashlib.sha256(os.getenv('PASSWORD').encode()).hexdigest()
    return hashlib.sha256(password.encode()).hexdigest() == correct_password_hash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        if check_password(request.form['password']):
            session['authenticated'] = True
            return redirect(url_for('index'))
        return render_template('login.html', error='Invalid password')
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
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

# Add error handler for rate limiting
@app.errorhandler(429)  # 429 is the rate limit exceeded error code
def ratelimit_handler(e):
    return render_template('rate_limit.html', error=str(e.description)), 429

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return render_template('csrf_error.html', reason=e.description), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
