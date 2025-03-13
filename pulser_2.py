#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

"""
Simplified control for IoTMug MOSFET Trailing Edge Dimmer.
This version provides easy configuration of steps, brightness range, and timing.
"""

# Pin definition
GATE_PIN = 18        # GPIO pin connected to GATE/PWM input of dimmer

# Constants
PWM_FREQ = 60
MIN_DUTY = 0        # Minimum duty cycle
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
    time.sleep(0.1)  # Short stabilization delay
    return duty

def fade(start_brightness, end_brightness, total_time, steps):
    """
    Perform a fade between brightness percentages.
    
    Parameters:
    start_brightness : The starting brightness (0-100)
    end_brightness : The ending brightness (0-100)
    total_time : Total duration of the fade in seconds
    steps : Number of steps to use for the fade
    """
    # Determine if we're going up or down
    going_up = end_brightness > start_brightness
    
    # Calculate step size and time
    brightness_range = abs(end_brightness - start_brightness)
    step_size = brightness_range / steps
    step_time = total_time / steps
    
    # Start at the initial brightness
    current = start_brightness
    
    # Standard fade
    for i in range(steps):
        if going_up:
            next_level = min(current + step_size, end_brightness)
        else:
            next_level = max(current - step_size, end_brightness)
            
        set_brightness(next_level)
        print(f"Step {i+1}/{steps}: {next_level:.1f}%")
        current = next_level
        time.sleep(step_time)
    
    # Ensure we end exactly at the target brightness
    set_brightness(end_brightness)
    print(f"Final: {end_brightness:.1f}%")

def run_cycle(start_brightness=0, end_brightness=100, fade_up_time=5.0, fade_down_time=5.0, 
              pause_at_top=1.0, pause_at_bottom=1.0, steps=20, cycles=1):
    """
    Run complete dimming cycles with configurable parameters.
    
    Parameters:
    start_brightness : Starting brightness level (0-100)
    end_brightness : Maximum brightness level to reach (0-100)
    fade_up_time : Time in seconds to fade from start to end brightness
    fade_down_time : Time in seconds to fade from end to start brightness
    pause_at_top : Time in seconds to pause at maximum brightness
    pause_at_bottom : Time in seconds to pause at minimum brightness
    steps : Number of steps to use during fading
    cycles : Number of cycles to run
    """
    try:
        print(f"Starting {cycles} dimming cycle(s) with {steps} steps")
        print(f"Brightness range: {start_brightness}% to {end_brightness}%")
        print(f"Timing: {fade_up_time}s up, {pause_at_top}s hold, {fade_down_time}s down, {pause_at_bottom}s off")
        
        for i in range(cycles):
            print(f"\nCycle {i+1}/{cycles}")
            
            # Fade up
            print("Fading up...")
            fade(start_brightness, end_brightness, fade_up_time, steps)
            
            # Hold at high brightness
            print(f"Holding at {end_brightness}% for {pause_at_top}s")
            time.sleep(pause_at_top)
            
            # Fade down
            print("Fading down...")
            fade(end_brightness, start_brightness, fade_down_time, steps)
            
            # Hold at low brightness
            print(f"Holding at {start_brightness}% for {pause_at_bottom}s")
            time.sleep(pause_at_bottom)
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        # Clean up
        set_brightness(0)
        pwm.stop()
        GPIO.cleanup()
        print("GPIO cleanup completed")

if __name__ == "__main__":
    print("Configurable Dimmer Control for IoTMug Trailing Edge Dimmer")
    print("----------------------------------------------------")
    print("Press Ctrl+C to stop")
    
    # Example usage with easy configuration
    run_cycle(
        start_brightness=0,     # Start at 0% brightness
        end_brightness=100,     # Go up to 100% brightness
        fade_up_time=30.0,      # Take 30 seconds to fade up
        fade_down_time=30.0,    # Take 30 seconds to fade down
        pause_at_top=2.0,       # Hold at maximum for 2 seconds
        pause_at_bottom=1.0,    # Hold at minimum for 1 second
        steps=10,               # Use 10 steps for the fade
        cycles=1                # Run 1 complete cycle
    )