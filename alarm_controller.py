import time
from datetime import datetime, timedelta
import json
import RPi.GPIO as GPIO

class AlarmController:
    def __init__(self, config_file='alarm_config.json', pin=18):
        self.config_file = config_file
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.pin, 100)  # 100 Hz frequency
        self.pwm.start(0)

    def load_config(self):
        with open(self.config_file, 'r') as f:
            return json.load(f)

    def calculate_brightness(self, start_time, current_time, fade_duration):
        elapsed = (current_time - start_time).total_seconds()
        total_fade_seconds = fade_duration * 60
        return min(100, (elapsed / total_fade_seconds) * 100)

    def run(self):
        while True:
            config = self.load_config()
            current_time = datetime.now()
            alarm_time = datetime.strptime(config['alarm_time'], '%H:%M').replace(
                year=current_time.year,
                month=current_time.month,
                day=current_time.day
            )
            
            fade_start = alarm_time - timedelta(minutes=config['fade_duration'])
            
            if fade_start <= current_time <= alarm_time:
                brightness = self.calculate_brightness(
                    fade_start,
                    current_time,
                    config['fade_duration']
                )
                self.pwm.ChangeDutyCycle(brightness)
            elif current_time > alarm_time:
                self.pwm.ChangeDutyCycle(100)  # Full brightness
            else:
                self.pwm.ChangeDutyCycle(0)  # Lights off
                
            time.sleep(60)  # Check every min

    def cleanup(self):
        self.pwm.stop()
        GPIO.cleanup()

if __name__ == '__main__':
    controller = AlarmController()
    try:
        controller.run()
    except KeyboardInterrupt:
        controller.cleanup()

