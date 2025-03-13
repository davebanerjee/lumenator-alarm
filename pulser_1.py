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
    # Define the problematic range
    problem_start = 55  # Just before the problematic range
    problem_end = 80    # Just after the problematic range
    
    # Determine if we're going up or down
    going_up = end_percent > start_percent
    
    if going_up and start_percent < problem_end and end_percent > problem_start:
        # We're going up and will cross the problematic range
        print("Using special handling for problematic brightness range...")
        
        # Phase 1: Go from start to beginning of problem range
        if start_percent < problem_start:
            steps_1 = 10
            step_time_1 = (duration_sec / 3) / steps_1
            step_size_1 = (problem_start - start_percent) / steps_1
            
            current = start_percent
            for i in range(steps_1):
                duty = set_brightness(current)
                print(f"Phase 1: {current:.1f}%, Duty: {duty:.1f}%")
                time.sleep(step_time_1)
                current += step_size_1
        else:
            current = start_percent
        
        # Phase 2: Very carefully cross the problematic range with special handling
        steps_2 = 20  # More steps in the problem zone
        step_time_2 = (duration_sec / 3) / steps_2
        step_size_2 = (problem_end - max(problem_start, start_percent)) / steps_2
        
        # For the problem zone, use a slightly different PWM frequency
        pwm.ChangeFrequency(57)  # Slightly different frequency for this range
        
        for i in range(steps_2):
            duty = set_brightness(current)
            print(f"Phase 2 (careful): {current:.1f}%, Duty: {duty:.1f}%")
            time.sleep(step_time_2 * 1.5)  # Longer stabilization time in problem zone
            current += step_size_2
        
        # Switch back to standard frequency
        pwm.ChangeFrequency(60)
        
        # Phase 3: Go from end of problem range to target
        if end_percent > problem_end:
            steps_3 = 10
            step_time_3 = (duration_sec / 3) / steps_3
            step_size_3 = (end_percent - problem_end) / steps_3
            
            current = problem_end
            for i in range(steps_3):
                duty = set_brightness(current)
                print(f"Phase 3: {current:.1f}%, Duty: {duty:.1f}%")
                time.sleep(step_time_3)
                current += step_size_3
    else:
        # Standard fade for dimming or ranges outside the problem area
        steps = 20
        step_time = duration_sec / steps
        step_size = (end_percent - start_percent) / steps
        
        current = start_percent
        for i in range(steps + 1):
            duty = set_brightness(current)
            print(f"Standard fade: {current:.1f}%, Duty: {duty:.1f}%")
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
            stable_fade(0, 100, fade_time)
            print("At full brightness")
            time.sleep(pause_time)
            
            # Fade down
            print("Fading down...")
            stable_fade(100, 0, fade_time)
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
    pulse_light(cycles=2, fade_time=40.0, pause_time=2.0)