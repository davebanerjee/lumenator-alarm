import RPi.GPIO as GPIO
import time

# Pin Definitions
PSM_PIN = 18  # Physical pin 12
ZC_PIN = 17   # Physical pin 11

# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(PSM_PIN, GPIO.OUT)
GPIO.setup(ZC_PIN, GPIO.IN)

# Create PWM object
pwm = GPIO.PWM(PSM_PIN, 1000)
pwm.start(0)  # Start at 0% duty cycle

def alternate_power():
    try:
        print("Starting alternating power. Press Ctrl+C to stop.")
        
        # Run for a total of 10 seconds (5 full cycles)
        for i in range(5):
            # Full power for 1 second
            pwm.ChangeDutyCycle(50)
            print(f"Cycle {i+1}/5: Full power")
            time.sleep(3)
            
            # Zero power for 1 second
            pwm.ChangeDutyCycle(0)
            print(f"Cycle {i+1}/5: Zero power")
            time.sleep(3)
            
        print("Completed 10 seconds (5 cycles) of alternating power")
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        # Clean up
        pwm.stop()
        GPIO.cleanup()
        print("GPIO cleanup completed")

if __name__ == "__main__":
    alternate_power()