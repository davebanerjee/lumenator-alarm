import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def callback(channel):
    print("Zero crossing detected!")

try:
    GPIO.add_event_detect(17, GPIO.RISING, callback=callback)
    print("Monitoring zero crossings. Press Ctrl+C to stop.")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    GPIO.cleanup()