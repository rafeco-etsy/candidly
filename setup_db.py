#!/usr/bin/env python
"""Setup script to initialize database with user authentication system."""

from app import create_app
from models import db, User, FeedbackTemplate, FeedbackRequest, Question, Response
from config import Config

def setup_database():
    """Initialize database and create default admin user."""
    app = create_app()
    
    with app.app_context():
        # Drop all tables and recreate
        print("Dropping existing tables...")
        db.drop_all()
        
        print("Creating tables...")
        db.create_all()
        
        # Create default admin user for development
        if app.config['LOCAL_DEV_MODE']:
            admin_user = User(
                email=app.config['LOCAL_DEV_EMAIL'],
                name=app.config['LOCAL_DEV_NAME'],
                can_create_templates=True,
                can_create_requests_for_others=True,
                is_admin=True
            )
            db.session.add(admin_user)
            
            # Create a few additional test users
            test_users = [
                User(
                    email='user1@example.com',
                    name='Test User 1',
                    can_create_templates=False,
                    can_create_requests_for_others=False,
                    is_admin=False
                ),
                User(
                    email='user2@example.com', 
                    name='Test User 2',
                    can_create_templates=True,
                    can_create_requests_for_others=True,
                    is_admin=False
                )
            ]
            
            for user in test_users:
                db.session.add(user)
            
            db.session.commit()
            print(f"Created admin user: {admin_user.email}")
            print(f"Created {len(test_users)} test users")
        
        print("Database setup complete!")

if __name__ == '__main__':
    setup_database()