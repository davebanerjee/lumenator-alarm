"""
Configuration settings for the Sunrise Alarm application.
"""
import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # GPIO Pin Definitions
    ZERO_CROSS_PIN = 17    # Input from zero-crossing detector
    GATE_PIN = 18          # Output to MOSFET gate
    
    # Constants for 60Hz AC power
    AC_HALF_CYCLE_US = 8333  # Microseconds for 60Hz (1/60/2 seconds)
    
    # Dimming parameters
    MAX_DIM_LEVEL = 1000     # Maximum dimming level