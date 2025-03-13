"""
Trailing edge dimmer implementation for LED lighting.
Adapted from the provided code to work as a module within the Flask application.
"""
import RPi.GPIO as GPIO
import time
import threading
import signal
import sys
from config import Config

class DimmerController:
    def __init__(self, zero_cross_pin=None, gate_pin=None):
        # Pin configuration
        self.ZERO_CROSS_PIN = zero_cross_pin or Config.ZERO_CROSS_PIN
        self.GATE_PIN = gate_pin or Config.GATE_PIN
        
        # Constants
        self.AC_HALF_CYCLE_US = Config.AC_HALF_CYCLE_US
        self.MAX_DIM_LEVEL = Config.MAX_DIM_LEVEL
        
        # State variables
        self.dim_level = 0
        self.running = False
        self.thread = None
        
        # Initialize GPIO
        GPIO.setwarnings(False)  # Disable GPIO warnings
        
        # Clean up the specific pins we'll be using to ensure clean state
        try:
            GPIO.cleanup(self.ZERO_CROSS_PIN)
            GPIO.cleanup(self.GATE_PIN)
        except:
            # In case the pins haven't been set up yet
            pass
            
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.ZERO_CROSS_PIN, GPIO.IN)
        GPIO.setup(self.GATE_PIN, GPIO.OUT)
        GPIO.output(self.GATE_PIN, GPIO.LOW)
    
    def precise_delay(self, delay_us):
        """More precise delay function for microsecond timing"""
        start_time = time.time()
        while (time.time() - start_time) < (delay_us / 1000000.0):
            pass
    
    def dimmer_thread_function(self):
        """Main dimmer control thread that handles the trailing edge dimming"""
        last_pin_state = GPIO.LOW
        
        while self.running:
            # Poll for zero crossing (rising edge)
            current_pin_state = GPIO.input(self.ZERO_CROSS_PIN)
            
            # Detect rising edge (transition from LOW to HIGH)
            if current_pin_state == GPIO.HIGH and last_pin_state == GPIO.LOW:
                # Zero-crossing detected
                
                # For trailing edge dimming:
                # 1. Turn ON at zero crossing
                GPIO.output(self.GATE_PIN, GPIO.HIGH)
                
                # 2. Calculate delay before turning OFF
                # The delay is proportional to the dim level
                # Higher dim_level = longer delay = brighter light
                delay_time = int((self.AC_HALF_CYCLE_US * self.dim_level) / self.MAX_DIM_LEVEL)
                
                # 3. Wait for the calculated time
                self.precise_delay(delay_time)
                
                # 4. Turn OFF after delay (trailing edge)
                GPIO.output(self.GATE_PIN, GPIO.LOW)
            
            # Update last pin state
            last_pin_state = current_pin_state
            
            # Small delay to prevent CPU hogging
            time.sleep(0.00005)  # 50 microseconds
    
    def start(self):
        """Start the dimmer controller"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.dimmer_thread_function)
            self.thread.daemon = True
            self.thread.start()
    
    def stop(self):
        """Stop the dimmer controller"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.5)
        GPIO.output(self.GATE_PIN, GPIO.LOW)
    
    def set_brightness(self, brightness_percent):
        """Set the brightness level as a percentage (0-100)"""
        # Convert percentage to dim level
        brightness_percent = float(brightness_percent)  # Ensure we're working with a number
        self.dim_level = int((brightness_percent / 100.0) * self.MAX_DIM_LEVEL)
        # Ensure within bounds
        self.dim_level = max(0, min(self.MAX_DIM_LEVEL, self.dim_level))
        # Return the actual brightness percentage based on the adjusted dim_level
        return self.get_brightness_percent()
    
    def get_brightness_percent(self):
        """Get the current brightness as a percentage"""
        return (self.dim_level / self.MAX_DIM_LEVEL) * 100
    
    def cleanup(self):
        """Clean up GPIO resources"""
        self.stop()
        GPIO.cleanup([self.ZERO_CROSS_PIN, self.GATE_PIN])

# Create a global instance of the dimmer controller
dimmer = DimmerController()