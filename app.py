from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect, CSRFError
from functools import wraps
import hashlib
import os
from dotenv import load_dotenv
import subprocess
import signal

# Import shared utilities
from alarm_utils import load_config, save_config, get_next_alarm_time

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

csrf = CSRFProtect(app)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=['20 per day', '5 per hour'],
    storage_uri='memory://',
)

# Path to the alarm controller script
CONTROLLER_SCRIPT = 'alarm_controller.py'
controller_process = None

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
        # Update configuration
        config['alarm_time'] = request.form['alarm_time']
        config['fade_duration'] = int(request.form['fade_duration'])
        config['enabled'] = 'enabled' in request.form
        if 'max_brightness' in request.form:
            config['max_brightness'] = int(request.form['max_brightness'])
        
        save_config(config)
        
        # Restart alarm controller to apply changes
        restart_controller()
        
        return redirect(url_for('index'))
    
    return render_template('index.html', config=config)

@app.route('/api/control', methods=['POST'])
@login_required
@csrf.exempt  # For API use, but implement API token instead in production
def control_alarm():
    action = request.json.get('action')
    
    if action == 'on':
        # Start sunrise immediately
        subprocess.run(['python', CONTROLLER_SCRIPT, 'on'], check=True)
        return jsonify({'status': 'success', 'message': 'Alarm started'})
    
    elif action == 'off':
        # Turn off the light
        subprocess.run(['python', CONTROLLER_SCRIPT, 'off'], check=True)
        return jsonify({'status': 'success', 'message': 'Alarm stopped'})
    
    elif action == 'set_brightness':
        # Set manual brightness
        level = request.json.get('level', 0)
        subprocess.run(['python', CONTROLLER_SCRIPT, 'set', str(level)], check=True)
        return jsonify({'status': 'success', 'message': f'Brightness set to {level}%'})
    
    return jsonify({'status': 'error', 'message': 'Unknown action'})

@app.route('/api/status', methods=['GET'])
@login_required
def get_status():
    # Run the controller with status command to get current state
    result = subprocess.run(['python', CONTROLLER_SCRIPT, 'status'], 
                           capture_output=True, text=True, check=True)
    
    # Parse the output
    lines = result.stdout.strip().split('\n')
    status = {}
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            status[key.strip()] = value.strip()
    
    return jsonify(status)

def start_controller():
    """Start the alarm controller as a background process"""
    global controller_process
    
    # Check if already running
    if controller_process and controller_process.poll() is None:
        return
    
    # Start as a background process
    controller_process = subprocess.Popen(['python', CONTROLLER_SCRIPT, 'daemon'])

def stop_controller():
    """Stop the alarm controller process"""
    global controller_process
    
    if controller_process:
        try:
            controller_process.terminate()
            controller_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            controller_process.kill()
        controller_process = None

def restart_controller():
    """Restart the alarm controller to apply config changes"""
    stop_controller()
    start_controller()

@app.errorhandler(429)
def ratelimit_handler(e):
    return render_template('rate_limit.html', error=str(e.description)), 429

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return render_template('csrf_error.html', reason=e.description), 400

# We'll initialize the controller when the app starts
# For newer Flask versions, we'll use a different approach

# Stop the controller when the app stops
@app.teardown_appcontext
def shutdown(exception=None):
    stop_controller()

# Create a function to initialize resources
def initialize_app():
    start_controller()

if __name__ == '__main__':
    try:
        # Initialize the controller before running the app
        initialize_app()
        app.run(host='0.0.0.0', port=5000, debug=False)
    finally:
        stop_controller()