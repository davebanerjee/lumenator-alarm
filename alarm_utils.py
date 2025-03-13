import json
import os
from datetime import datetime, timedelta

"""
Shared utility functions for the sunrise alarm system.
Used by both the Flask app and the alarm controller.
"""

CONFIG_FILE = 'alarm_config.json'
DEFAULT_CONFIG = {
    'alarm_time': '07:00',
    'fade_duration': 30,  # Duration in minutes for light fade-in
    'enabled': True,
    'max_brightness': 100  # Maximum brightness percentage
}

def load_config():
    """
    Load alarm configuration from file
    """
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            # Ensure all required fields exist, add defaults if not
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """
    Save alarm configuration to file
    """
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def get_next_alarm_time():
    """
    Calculate the next alarm time based on the configuration
    """
    config = load_config()
    alarm_hour, alarm_minute = map(int, config['alarm_time'].split(':'))
    
    now = datetime.now()
    alarm_time = now.replace(hour=alarm_hour, minute=alarm_minute, second=0, microsecond=0)
    
    # If the alarm time has already passed today, schedule for tomorrow
    if alarm_time <= now:
        alarm_time += timedelta(days=1)
    
    return alarm_time