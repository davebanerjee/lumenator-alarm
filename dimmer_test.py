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
pwm = GPIO.PWM(PSM_PIN, 60)  # Changed to 60 Hz to match AC frequency
pwm.start(0)

def wait_for_zero_crossing():
    while (GPIO.input(ZC_PIN)):
        time.sleep(0.01)

def pulse_light(cycles=5, speed=0.05):
    try:
        while cycles > 0:
            wait_for_zero_crossing()
            duty = 0
            pwm.ChangeDutyCycle(duty)
            time.sleep(speed)

            wait_for_zero_crossing()
            duty = 20
            pwm.ChangeDutyCycle(duty)
            time.sleep(speed)

            wait_for_zero_crossing()
            duty = 100
            pwm.ChangeDutyCycle(duty)
            time.sleep(speed)
                
            cycles -= 1
            
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        pwm.stop()
        GPIO.cleanup()
        print("GPIO cleanup completed")

if __name__ == "__main__":
    print("Starting light pulsing. Press Ctrl+C to stop.")
    pulse_light(3, 3)