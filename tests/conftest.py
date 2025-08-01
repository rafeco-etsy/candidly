import pytest
import tempfile
import os
from app import create_app
from models import db, FeedbackTemplate, FeedbackRequest, Question, Response

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Create a temporary file to isolate the database
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "WTF_CSRF_ENABLED": False
    })

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture
def sample_template(app):
    """Create a sample feedback template with questions."""
    with app.app_context():
        template = FeedbackTemplate(name="Test Template", description="A test template")
        db.session.add(template)
        db.session.flush()
        
        # Add some questions
        questions = [
            Question(
                template_id=template.id,
                question_text="How would you rate their communication?",
                question_type="rating",
                order_index=0
            ),
            Question(
                template_id=template.id,
                question_text="What are their greatest strengths?",
                question_type="discussion",
                order_index=1
            )
        ]
        
        for question in questions:
            db.session.add(question)
        
        db.session.commit()
        
        # Refresh to ensure relationships are loaded
        db.session.refresh(template)
        yield template

@pytest.fixture
def sample_feedback_request(app, sample_template):
    """Create a sample feedback request using a template."""
    with app.app_context():
        feedback_request = FeedbackRequest(target_name="John Doe", template_id=sample_template.id)
        db.session.add(feedback_request)
        db.session.commit()
        
        # Refresh to ensure relationships are loaded
        db.session.refresh(feedback_request)
        yield feedback_request