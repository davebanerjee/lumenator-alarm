"""
Main routes for the Sunrise Alarm application.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import TimeField, IntegerField, BooleanField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from app.models import AlarmSchedule, SystemConfig, User
from app.dimmer import dimmer
from app.scheduler import schedule_next_alarm, initialize_scheduler
from app import db
import json
from datetime import datetime, time

main_bp = Blueprint('main', __name__)

# Forms
class AlarmForm(FlaskForm):
    enabled = BooleanField('Enabled')
    alarm_time = TimeField('Alarm Time', validators=[DataRequired()])
    fade_duration = IntegerField('Fade Duration (minutes)', 
                                validators=[DataRequired(), NumberRange(min=1, max=120)],
                                default=30)
    submit = SubmitField('Save')

class ManualControlForm(FlaskForm):
    brightness = IntegerField('Brightness (%)', 
                              validators=[NumberRange(min=0, max=100)],
                              default=50)
    submit_on = SubmitField('Turn On')
    submit_off = SubmitField('Turn Off')
    
    def __init__(self, *args, **kwargs):
        super(ManualControlForm, self).__init__(*args, **kwargs)
        # This ensures the brightness field is properly populated during form processing

# Routes
@main_bp.route('/')
@login_required
def index():
    next_alarm = SystemConfig.get_value('next_alarm', '')
    if next_alarm:
        next_alarm = datetime.fromisoformat(next_alarm)
    
    is_light_on = dimmer.get_brightness_percent() > 0
    current_brightness = round(dimmer.get_brightness_percent())
    
    return render_template('index.html', 
                          next_alarm=next_alarm,
                          is_light_on=is_light_on,
                          current_brightness=current_brightness)

@main_bp.route('/schedule')
@login_required
def schedule():
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    alarms = {}
    
    for day_idx, day_name in enumerate(days):
        alarm = AlarmSchedule.query.filter_by(day_of_week=day_idx).first()
        if not alarm:
            alarm = AlarmSchedule(day_of_week=day_idx, 
                                  enabled=False, 
                                  alarm_time=time(7, 0),  # Default 7:00 AM
                                  fade_duration=30)
            db.session.add(alarm)
            db.session.commit()
        
        alarms[day_name] = alarm
    
    return render_template('schedule.html', days=days, alarms=alarms)

@main_bp.route('/schedule/<int:day_id>', methods=['GET', 'POST'])
@login_required
def edit_schedule(day_id):
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    if day_id < 0 or day_id > 6:
        flash('Invalid day selected')
        return redirect(url_for('main.schedule'))
    
    alarm = AlarmSchedule.query.filter_by(day_of_week=day_id).first()
    if not alarm:
        alarm = AlarmSchedule(day_of_week=day_id, 
                             enabled=False, 
                             alarm_time=time(7, 0),
                             fade_duration=30)
        db.session.add(alarm)
        db.session.commit()
    
    form = AlarmForm(obj=alarm)
    
    if form.validate_on_submit():
        alarm.enabled = form.enabled.data
        alarm.alarm_time = form.alarm_time.data
        alarm.fade_duration = form.fade_duration.data
        db.session.commit()
        
        # Reschedule alarms
        schedule_next_alarm()
        
        flash(f'Alarm for {days[day_id]} has been updated')
        return redirect(url_for('main.schedule'))
    
    return render_template('edit_schedule.html', 
                          form=form, 
                          day=days[day_id], 
                          day_id=day_id)

@main_bp.route('/manual', methods=['GET', 'POST'])
@login_required
def manual_control():
    form = ManualControlForm()
    
    # Only set default value on GET request, not on POST
    if request.method == 'GET':
        current_brightness = round(dimmer.get_brightness_percent())
        form.brightness.data = current_brightness
    
    if form.validate_on_submit():
        # Get the brightness value from the form
        brightness = form.brightness.data
        
        if form.submit_on.data:
            # Explicitly set the brightness and start the dimmer
            dimmer.set_brightness(brightness)
            dimmer.start()
            flash(f'Light turned on at {brightness}% brightness')
        elif form.submit_off.data:
            dimmer.set_brightness(0)
            dimmer.stop()
            flash('Light turned off')
        
        # Store the last manual state with the current brightness value
        SystemConfig.set_value('last_manual_state', 
                               json.dumps({
                                   'on': form.submit_on.data,
                                   'brightness': brightness
                               }))
        
        return redirect(url_for('main.manual_control'))
    
    # For both GET and failed validation, get the current brightness
    current_brightness = round(dimmer.get_brightness_percent())
    
    return render_template('manual_control.html', form=form, current_brightness=current_brightness)

@main_bp.route('/api/brightness/<int:level>', methods=['POST'])
@login_required
def set_brightness(level):
    """API endpoint to set brightness level (0-100)"""
    if level < 0 or level > 100:
        return jsonify({'error': 'Brightness must be between 0 and 100'}), 400
    
    # First set the brightness level
    actual_level = dimmer.set_brightness(level)
    
    # Then start/stop the dimmer as needed
    if level > 0:
        if not dimmer.running:
            dimmer.start()
    else:
        dimmer.stop()
    
    # Store the last manual state
    SystemConfig.set_value('last_manual_state', 
                          json.dumps({
                              'on': level > 0,
                              'brightness': actual_level
                          }))
    
    return jsonify({'success': True, 'brightness': actual_level})

# This function is now called explicitly in create_app instead of using before_app_first_request
def initialize_app():
    """Initialize the application"""
    from app.models import User
    
    # Check if we need to create a default user
    if User.query.count() == 0:
        # Create default admin user
        admin = User(username='admin')
        admin.set_password('sunrise')
        db.session.add(admin)
        db.session.commit()
        print("Created default admin user with password 'sunrise'")
    
    # Restore the last manual state if any
    last_state = SystemConfig.get_value('last_manual_state', '')
    if last_state:
        try:
            state = json.loads(last_state)
            if state.get('on', False):
                dimmer.set_brightness(state.get('brightness', 50))
                dimmer.start()
        except Exception as e:
            print(f"Error restoring last state: {e}")
    
    # Initialize the scheduler
    initialize_scheduler()