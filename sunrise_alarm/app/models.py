"""
Database models for the Sunrise Alarm application.
"""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def __repr__(self):
        return f'<User {self.username}>'

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class AlarmSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, index=True)  # 0-6 for Monday-Sunday
    enabled = db.Column(db.Boolean, default=False)
    alarm_time = db.Column(db.Time, nullable=False)
    fade_duration = db.Column(db.Integer, default=30)  # Duration in minutes
    
    def __repr__(self):
        return f'<Alarm {self.day_of_week}:{self.alarm_time}>'
        
class SystemConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True)
    value = db.Column(db.String(256))
    
    @staticmethod
    def get_value(key, default=None):
        config = SystemConfig.query.filter_by(key=key).first()
        if config:
            return config.value
        return default
        
    @staticmethod
    def set_value(key, value):
        config = SystemConfig.query.filter_by(key=key).first()
        if config:
            config.value = value
        else:
            config = SystemConfig(key=key, value=value)
            db.session.add(config)
        db.session.commit()
