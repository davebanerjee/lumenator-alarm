#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

"""
Simplified control for IoTMug MOSFET Trailing Edge Dimmer with focus on stability.
This version uses a simpler approach to eliminate flickering.
"""

# Pin definition - just the control pin
GATE_PIN = 18        # GPIO pin connected to GATE/PWM input of dimmer

# Constants
PWM_FREQ = 60        # Match PWM to AC frequency for US (60Hz)
MIN_DUTY = 10        # Minimum duty cycle that works without flickering
MAX_DUTY = 100       # Maximum duty cycle

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(GATE_PIN, GPIO.OUT)

# Initialize PWM
pwm = GPIO.PWM(GATE_PIN, PWM_FREQ)
pwm.start(0)  # Start with lights off

def set_brightness(level):
    """
    Set brightness level (0-100)
    """
    # Scale to usable range
    if level <= 0:
        duty = 0
    else:
        # Scale from 0-100 to MIN_DUTY-MAX_DUTY
        duty = MIN_DUTY + ((MAX_DUTY - MIN_DUTY) * level / 100)
    
    # Apply duty cycle
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.05)  # Short stabilization delay
    return duty

def stable_fade(start_percent, end_percent, duration_sec):
    """
    Perform a stable fade between brightness percentages
    """
    # Number of steps (smaller steps = smoother fade but more potential for flicker)
    steps = 20  # Reduced number of steps for stability
    
    step_time = duration_sec / steps
    step_size = (end_percent - start_percent) / steps
    
    current = start_percent
    
    # Perform the fade with fewer, more stable steps
    for i in range(steps + 1):
        duty = set_brightness(current)
        print(f"Brightness: {current:.1f}%, Duty: {duty:.1f}%")
        
        # Longer delay between steps for stability
        time.sleep(step_time)
        current += step_size

def pulse_light(cycles=3, fade_time=5.0, pause_time=1.0):
    """
    Create stable pulsing effect
    """
    try:
        print("Starting stable light pulse sequence")
        
        for i in range(cycles):
            print(f"Cycle {i+1}/{cycles}")
            
            # Full off
            set_brightness(0)
            time.sleep(0.5)
            
            # Fade up - using a slightly higher minimum for stability
            print("Fading up...")
            stable_fade(15, 100, fade_time)
            print("At full brightness")
            time.sleep(pause_time)
            
            # Fade down
            print("Fading down...")
            stable_fade(100, 15, fade_time)
            print("At minimum brightness")
            time.sleep(pause_time)
            
            # Full off again
            set_brightness(0)
            time.sleep(pause_time)
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        # Clean up
        set_brightness(0)
        pwm.stop()
        GPIO.cleanup()
        print("GPIO cleanup completed")

if __name__ == "__main__":
    print("Stable Dimmer Control for IoTMug Trailing Edge Dimmer")
    print("----------------------------------------------------")
    print("Press Ctrl+C to stop")
    
    # Run the pulse effect with focus on stability
    pulse_light(cycles=2, fade_time=80.0, pause_time=2.0)