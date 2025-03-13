import RPi.GPIO as GPIO
import time
import threading
import signal
import sys
import json
import os
from datetime import datetime, timedelta
import argparse

"""
Raspberry Pi Sunrise Alarm Controller

This script implements a sunrise alarm using trailing edge dimming for LED lighting.
It utilizes a zero-crossing detector and MOSFET control, similar to the dimmer implementation
but adapted for gradual brightness increase.
"""

# Pin Definitions
ZERO_CROSS_PIN = 17    # Input from zero-crossing detector
GATE_PIN = 18          # Output to MOSFET gate

# Constants for 60Hz AC power
AC_HALF_CYCLE_US = 8333  # Microseconds for 60Hz (1/60/2 seconds)

# Dimming parameters
MAX_DIM_LEVEL = 1000     # Maximum dimming level (allows for fine control)
current_dim_level = 0    # Start with lights off

# Configuration
CONFIG_FILE = 'alarm_config.json'
DEFAULT_CONFIG = {
    'alarm_time': '07:00',
    'fade_duration': 30,  # Duration in minutes for light fade-in
    'enabled': True,
    'max_brightness': 100  # Maximum brightness percentage (will be converted to dim level)
}

# System flags
running = True
alarm_active = False

def precise_delay(delay_us):
    """
    More precise delay function for microsecond timing
    """
    start_time = time.time()
    while (time.time() - start_time) < (delay_us / 1000000.0):
        pass

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

def setup_gpio():
    """
    Initialize GPIO for dimmer control
    """
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(ZERO_CROSS_PIN, GPIO.IN)
    GPIO.setup(GATE_PIN, GPIO.OUT)
    GPIO.output(GATE_PIN, GPIO.LOW)  # Start with light off

def dimmer_thread():
    """
    Main dimmer control thread that handles the trailing edge dimming
    """
    global running, current_dim_level
    
    last_pin_state = GPIO.LOW
    
    while running:
        # Poll for zero crossing (rising edge)
        current_pin_state = GPIO.input(ZERO_CROSS_PIN)
        
        # Detect rising edge (transition from LOW to HIGH)
        if current_pin_state == GPIO.HIGH and last_pin_state == GPIO.LOW:
            # Zero-crossing detected
            
            # For trailing edge dimming:
            # 1. Turn ON at zero crossing
            GPIO.output(GATE_PIN, GPIO.HIGH)
            
            # 2. Calculate delay before turning OFF
            # The delay is proportional to the dim level
            # Higher dim_level = longer delay = brighter light
            delay_time = int((AC_HALF_CYCLE_US * current_dim_level) / MAX_DIM_LEVEL)
            
            # 3. Wait for the calculated time
            precise_delay(delay_time)
            
            # 4. Turn OFF after delay (trailing edge)
            GPIO.output(GATE_PIN, GPIO.LOW)
        
        # Update last pin state
        last_pin_state = current_pin_state
        
        # Small delay to prevent CPU hogging
        time.sleep(0.00005)  # 50 microseconds

def start_sunrise():
    """
    Begin the sunrise effect by gradually increasing brightness
    """
    global alarm_active, current_dim_level
    
    config = load_config()
    fade_duration = config['fade_duration']
    max_brightness_pct = config['max_brightness']
    
    # Convert max brightness percentage to dim level
    max_dim_level = int((max_brightness_pct / 100) * MAX_DIM_LEVEL)
    
    if not config.get('enabled', True):
        print("Alarm is disabled, not starting sunrise")
        return
    
    print(f"Starting sunrise at {datetime.now()}")
    alarm_active = True
    current_dim_level = 0
    
    # Calculate total steps and time between steps
    total_steps = 100  # Divide the fade into 100 steps for smooth transition
    step_time = (fade_duration * 60) / total_steps  # Time per step in seconds
    dim_increment = max_dim_level / total_steps
    
    # Start the fade thread
    fade_thread = threading.Thread(target=fade_in, args=(step_time, dim_increment, total_steps, max_dim_level))
    fade_thread.daemon = True
    fade_thread.start()

def fade_in(step_time, dim_increment, total_steps, max_dim_level):
    """
    Gradually increase brightness over time to simulate sunrise
    """
    global current_dim_level, alarm_active
    
    for step in range(total_steps):
        if not running or not alarm_active:
            break
        
        current_dim_level = min(int(step * dim_increment), max_dim_level)
        
        # Only print in interactive mode
        if not daemon_mode:
            brightness_pct = (current_dim_level / MAX_DIM_LEVEL) * 100
            print(f"Brightness: {brightness_pct:.1f}% (level {current_dim_level}/{MAX_DIM_LEVEL})")
            
        time.sleep(step_time)
    
    # Keep at full brightness for 30 minutes after fade completes
    if running and alarm_active:
        time.sleep(30 * 60)  # 30 minutes
    
    # Turn off light if still on
    if alarm_active:
        turn_off_light()

def turn_off_light():
    """
    Turn off the light and reset alarm state
    """
    global alarm_active, current_dim_level
    
    current_dim_level = 0
    alarm_active = False
    
    if not daemon_mode:
        print("Light turned off")

def manual_brightness(level_percent):
    """
    Manually set brightness level (0-100%)
    """
    global current_dim_level, alarm_active
    
    # Cancel any active alarm
    alarm_active = False
    
    # Convert percentage to dim level
    level_percent = max(0, min(100, level_percent))
    current_dim_level = int((level_percent / 100) * MAX_DIM_LEVEL)
    
    if not daemon_mode:
        print(f"Brightness manually set to {level_percent}% (level {current_dim_level}/{MAX_DIM_LEVEL})")

def check_schedule():
    """
    Periodically check if we need to schedule a new alarm
    (runs every minute)
    """
    if not running:
        return
    
    # Check if alarm should be running right now
    config = load_config()
    if not config.get('enabled', True):
        return
    
    next_alarm = get_next_alarm_time()
    now = datetime.now()
    
    # If it's within the fade duration window, start sunrise
    fade_duration = config['fade_duration']
    start_time = next_alarm - timedelta(minutes=fade_duration)
    
    if start_time <= now < next_alarm and not alarm_active:
        start_sunrise()
    
    # Schedule next check
    threading.Timer(60, check_schedule).start()

def signal_handler(sig, frame):
    """
    Handle Ctrl+C and termination signals gracefully
    """
    global running
    
    if not daemon_mode:
        print("\nStopping sunrise alarm...")
        
    running = False
    time.sleep(0.2)
    turn_off_light()
    GPIO.output(GATE_PIN, GPIO.LOW)
    GPIO.cleanup()
    sys.exit(0)

def print_status():
    """
    Print the current status of the alarm
    """
    config = load_config()
    next_alarm = get_next_alarm_time()
    brightness_percent = (current_dim_level / MAX_DIM_LEVEL) * 100
    
    print(f"Alarm time: {config['alarm_time']}")
    print(f"Fade duration: {config['fade_duration']} minutes")
    print(f"Enabled: {config.get('enabled', True)}")
    print(f"Max brightness: {config.get('max_brightness', 100)}%")
    print(f"Current brightness: {brightness_percent:.1f}%")
    print(f"Current dim level: {current_dim_level}/{MAX_DIM_LEVEL}")
    print(f"Alarm active: {alarm_active}")
    print(f"Next alarm: {next_alarm}")

def run_daemon():
    """
    Run as a daemon process
    """
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start dimmer thread
    dimmer = threading.Thread(target=dimmer_thread)
    dimmer.daemon = True
    dimmer.start()
    
    # Start schedule checker
    check_schedule()
    
    # Keep running until terminated
    while running:
        time.sleep(1)

def interactive_mode():
    """
    Run in interactive command-line mode
    """
    print("Raspberry Pi Sunrise Alarm Controller")
    print("------------------------------------")
    print("Commands:")
    print("  'on': Start sunrise effect")
    print("  'off': Turn off light")
    print("  'set [0-100]': Set brightness level")
    print("  'status': Show current status")
    print("  'schedule': Show next alarm time")
    print("  'quit': Exit")
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start dimmer thread
    dimmer = threading.Thread(target=dimmer_thread)
    dimmer.daemon = True
    dimmer.start()
    
    # Start schedule checker
    check_schedule()
    
    # Command-line interface
    try:
        while running:
            command = input("Enter command: ").strip().lower()
            
            if command == 'on':
                start_sunrise()
            elif command == 'off':
                turn_off_light()
            elif command.startswith('set '):
                try:
                    level = int(command.split()[1])
                    manual_brightness(level)
                except (IndexError, ValueError):
                    print("Invalid brightness level. Use: set [0-100]")
            elif command == 'status':
                print_status()
            elif command == 'schedule':
                next_alarm = get_next_alarm_time()
                print(f"Next alarm: {next_alarm}")
            elif command == 'quit':
                signal_handler(None, None)
    
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Raspberry Pi Sunrise Alarm Controller')
    
    # Define command line arguments
    parser.add_argument('command', nargs='?', default='interactive',
                        choices=['on', 'off', 'set', 'status', 'schedule', 'daemon', 'interactive'],
                        help='Command to execute')
    parser.add_argument('value', nargs='?', type=int, 
                        help='Value for set command (brightness 0-100)')
    
    args = parser.parse_args()
    
    # Global variable to track daemon mode
    daemon_mode = (args.command == 'daemon')
    
    try:
        # Setup GPIO
        setup_gpio()
        
        # Execute the specified command
        if args.command == 'on':
            start_sunrise()
        elif args.command == 'off':
            turn_off_light()
        elif args.command == 'set' and args.value is not None:
            manual_brightness(args.value)
        elif args.command == 'status':
            print_status()
        elif args.command == 'schedule':
            next_alarm = get_next_alarm_time()
            print(f"Next alarm: {next_alarm}")
        elif args.command == 'daemon':
            run_daemon()
        else:  # interactive is the default
            interactive_mode()
        
        # Cleanup for one-shot commands
        if args.command not in ['daemon', 'interactive']:
            GPIO.cleanup()
            
    except Exception as e:
        print(f"Error: {e}")
        GPIO.cleanup()