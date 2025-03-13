"""
Scheduler for sunrise alarm functionality.
"""
import time
from datetime import datetime, timedelta
from app import scheduler, db
from app.models import AlarmSchedule, SystemConfig
from app.dimmer import dimmer

def get_next_alarm():
    """Get the next scheduled alarm"""
    now = datetime.now()
    day_of_week = now.weekday()  # 0-6 for Monday-Sunday
    
    # Search for the next 7 days
    for i in range(7):
        check_day = (day_of_week + i) % 7
        alarms = AlarmSchedule.query.filter_by(day_of_week=check_day, enabled=True).all()
        
        for alarm in alarms:
            alarm_datetime = datetime.combine(now.date() + timedelta(days=i), alarm.alarm_time)
            
            if alarm_datetime > now:
                return alarm, alarm_datetime
    
    return None, None

def schedule_next_alarm():
    """Schedule the next alarm in the system"""
    alarm, alarm_time = get_next_alarm()
    
    if alarm:
        # Remove any existing jobs
        scheduler.remove_all_jobs()
        
        # Schedule the sunrise alarm
        scheduler.add_job(
            start_sunrise,
            'date',
            run_date=alarm_time - timedelta(minutes=alarm.fade_duration),
            args=[alarm.fade_duration]
        )
        
        # Update the next alarm time in the system config
        SystemConfig.set_value('next_alarm', alarm_time.isoformat())
        
        return True
    else:
        SystemConfig.set_value('next_alarm', '')
        return False

def start_sunrise(fade_duration):
    """Start the sunrise effect over the specified duration"""
    # Start with 0% brightness
    dimmer.set_brightness(0)
    dimmer.start()
    
    # Calculate the total number of steps for smooth fading
    total_steps = fade_duration * 60  # Convert minutes to seconds
    step_size = 100.0 / total_steps
    
    # Gradually increase brightness
    current_brightness = 0
    for _ in range(total_steps):
        current_brightness += step_size
        dimmer.set_brightness(min(100, current_brightness))
        time.sleep(1)  # Update every second
    
    # Ensure we reach 100% brightness
    dimmer.set_brightness(100)
    
    # Schedule the next alarm
    schedule_next_alarm()

def initialize_scheduler():
    """Initialize the scheduler system"""
    # Start the scheduler if not already running
    if not scheduler.running:
        scheduler.start()
    
    # Schedule the next alarm
    schedule_next_alarm()