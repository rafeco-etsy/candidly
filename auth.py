from flask import current_app, session, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps
from models import db, User
from datetime import datetime

login_manager = LoginManager()

def init_auth(app):
    """Initialize authentication system."""
    login_manager.init_app(app)
    login_manager.login_view = 'auth_login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return User.query.get(str(user_id))

def get_or_create_dev_user():
    """Get or create the default development user."""
    if not current_app.config['LOCAL_DEV_MODE']:
        return None
    
    email = current_app.config['LOCAL_DEV_EMAIL']
    user = User.query.filter_by(email=email).first()
    
    if not user:
        user = User(
            email=email,
            name=current_app.config['LOCAL_DEV_NAME'],
            can_create_templates=True,
            can_create_requests_for_others=True,
            is_admin=True
        )
        db.session.add(user)
        db.session.commit()
    
    return user

def auto_login_dev_user():
    """Automatically log in the dev user in local development mode."""
    if current_app.config['LOCAL_DEV_MODE'] and not current_user.is_authenticated:
        user = get_or_create_dev_user()
        if user:
            user.last_login = datetime.utcnow()
            db.session.commit()
            login_user(user)
            return user
    return current_user if current_user.is_authenticated else None

def require_permission(permission):
    """Decorator to require specific permissions."""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            user = auto_login_dev_user()
            if not user:
                flash('Please log in to continue.', 'warning')
                return redirect(url_for('auth_login'))
            
            # Check admin override
            if user.is_admin:
                return f(*args, **kwargs)
            
            # Check specific permission
            if permission == 'create_templates' and not user.can_create_templates:
                flash('You do not have permission to create templates.', 'error')
                return redirect(url_for('dashboard'))
            elif permission == 'create_requests_for_others' and not user.can_create_requests_for_others:
                flash('You do not have permission to create feedback requests for others.', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def ensure_authenticated():
    """Ensure user is authenticated, auto-login in dev mode if needed."""
    user = auto_login_dev_user()
    if not user:
        flash('Please log in to continue.', 'warning')
        return redirect(url_for('auth_login'))
    return user

def can_access_request(feedback_request, user=None):
    """Check if user can access a feedback request."""
    if not user:
        user = current_user
    
    if not user.is_authenticated:
        return False
    
    # Admin can access everything
    if user.is_admin:
        return True
    
    # Creator can access their own requests
    if feedback_request.created_by_id == user.id:
        return True
    
    # Target person can access feedback about them (email-first)
    if feedback_request.target_email == user.email:
        return True
    
    # Assignee can access requests assigned to them (email-first)
    if feedback_request.assigned_to_email == user.email:
        return True
    
    # Legacy fallback for existing records
    if hasattr(feedback_request, 'assigned_to_id') and feedback_request.assigned_to_id == user.id:
        return True
    
    return False

def can_complete_request(feedback_request, user=None):
    """Check if user can complete/respond to a feedback request."""
    if not user:
        user = current_user
    
    if not user.is_authenticated:
        return False
    
    # Only assignee can complete the request (email-first)
    if feedback_request.assigned_to_email == user.email:
        return True
    
    # Legacy fallback for existing records
    if hasattr(feedback_request, 'assigned_to_id') and feedback_request.assigned_to_id == user.id:
        return True
    
    return False

def get_users_for_assignment():
    """Get list of users that can be assigned feedback requests."""
    return User.query.order_by(User.name).all()