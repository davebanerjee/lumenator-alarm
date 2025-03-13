import RPi.GPIO as GPIO
import time
import threading
import signal
import sys

"""
Raspberry Pi Trailing Edge Dimmer Implementation

This script implements a trailing edge dimmer for LED lighting using a zero-crossing
detector and MOSFET control. It turns on the MOSFET at zero-crossing and turns it off
after a calculated delay for better compatibility with LED loads.
"""

# Pin Definitions
ZERO_CROSS_PIN = 17    # Input from zero-crossing detector
GATE_PIN = 18          # Output to MOSFET gate

# Constants for 60Hz AC power
AC_HALF_CYCLE_US = 8333  # Microseconds for 60Hz (1/60/2 seconds)

# Dimming parameters
MAX_DIM_LEVEL = 1000     # Maximum dimming level (allows for fine control)
dim_level = MAX_DIM_LEVEL // 4  # Start at 25% brightness

# System flags
running = True
zero_cross_detected = False

# Set up GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(ZERO_CROSS_PIN, GPIO.IN)
GPIO.setup(GATE_PIN, GPIO.OUT)
GPIO.output(GATE_PIN, GPIO.LOW)

def precise_delay(delay_us):
    """
    More precise delay function for microsecond timing
    """
    start_time = time.time()
    while (time.time() - start_time) < (delay_us / 1000000.0):
        pass

def dimmer_thread():
    """
    Main dimmer control thread that handles the trailing edge dimming
    """
    global running, zero_cross_detected, dim_level
    
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
            delay_time = int((AC_HALF_CYCLE_US * dim_level) / MAX_DIM_LEVEL)
            
            # 3. Wait for the calculated time
            precise_delay(delay_time)
            
            # 4. Turn OFF after delay (trailing edge)
            GPIO.output(GATE_PIN, GPIO.LOW)
        
        # Update last pin state
        last_pin_state = current_pin_state
        
        # Small delay to prevent CPU hogging
        time.sleep(0.00005)  # 50 microseconds

def signal_handler(sig, frame):
    """
    Handle Ctrl+C gracefully
    """
    global running
    print("\nStopping dimmer...")
    running = False
    time.sleep(0.2)
    GPIO.output(GATE_PIN, GPIO.LOW)
    GPIO.cleanup()
    sys.exit(0)

def print_status():
    """
    Print the current dimming level
    """
    brightness_percent = (dim_level / MAX_DIM_LEVEL) * 100
    print(f"Brightness: {brightness_percent:.1f}% (level {dim_level}/{MAX_DIM_LEVEL})")

def main():
    global dim_level
    
    print("Raspberry Pi Trailing Edge Dimmer for LEDs")
    print("------------------------------------------")
    print("Commands:")
    print("  'u': Increase brightness")
    print("  'd': Decrease brightness")
    print("  'max': Set to maximum brightness")
    print("  'min': Set to minimum brightness")
    print("  'q': Quit")
    print("Press Ctrl+C to exit")
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start dimmer thread
    dimmer = threading.Thread(target=dimmer_thread)
    dimmer.daemon = True
    dimmer.start()
    
    # Print initial status
    print_status()
    
    # Main input loop
    try:
        while running:
            command = input().strip().lower()
            
            if command == 'u':
                # Increase brightness by 5%
                dim_level = min(MAX_DIM_LEVEL, dim_level + (MAX_DIM_LEVEL // 20))
                print_status()
            elif command == 'd':
                # Decrease brightness by 5%
                dim_level = max(0, dim_level - (MAX_DIM_LEVEL // 20))
                print_status()
            elif command == 'max':
                dim_level = MAX_DIM_LEVEL
                print_status()
            elif command == 'min':
                dim_level = 0
                print_status()
            elif command == 'q':
                signal_handler(None, None)
            
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    try:
        main()
    finally:
        GPIO.cleanup()