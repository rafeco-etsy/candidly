import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///candidly.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL') or 'gpt-4o'
    
    # Authentication settings
    LOCAL_DEV_MODE = os.environ.get('LOCAL_DEV_MODE', 'true').lower() == 'true'
    LOCAL_DEV_EMAIL = os.environ.get('LOCAL_DEV_EMAIL') or 'dev@example.com'
    LOCAL_DEV_NAME = os.environ.get('LOCAL_DEV_NAME') or 'Dev User'
    
    # Google OAuth (for future use)
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')