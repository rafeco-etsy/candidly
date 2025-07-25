#!/usr/bin/env python3
"""
Test the actual review route that was causing the JSON serialization error.
"""
import tempfile
import os
from app import create_app
from models import db, FeedbackRequest, Question, Response

def test_review_route():
    """Test that the review route works without JSON serialization errors."""
    
    # Create a temporary database
    db_fd, db_path = tempfile.mkstemp()
    
    # Configure test app
    class TestConfig:
        TESTING = True
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
        SECRET_KEY = "test-key"
        WTF_CSRF_ENABLED = False
    
    app = create_app(TestConfig)
    client = app.test_client()
    
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Create test data
        feedback_request = FeedbackRequest(target_name="Test Person")
        db.session.add(feedback_request)
        db.session.flush()
        
        question = Question(
            feedback_request_id=feedback_request.id,
            question_text="What are their strengths?",
            question_type="discussion",
            order_index=0
        )
        db.session.add(question)
        db.session.flush()
        
        response = Response(
            feedback_request_id=feedback_request.id,
            question_id=question.id,
            discussion_summary="They are great at teamwork",
            is_draft=True
        )
        db.session.add(response)
        db.session.commit()
        
        request_id = feedback_request.id
    
    # Test the review route (this previously caused the TypeError)
    try:
        response = client.get(f'/review/{request_id}')
        if response.status_code == 200:
            print("✅ Review route test PASSED")
            print(f"Response status: {response.status_code}")
            # Check that the page contains the expected JavaScript
            if b'const questions = ' in response.data and b'const responses = ' in response.data:
                print("✅ JavaScript variables are properly embedded")
            else:
                print("⚠️  JavaScript variables might not be embedded correctly")
            return True
        else:
            print(f"❌ Review route test FAILED: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Review route test FAILED with exception: {e}")
        return False
    finally:
        # Cleanup
        os.close(db_fd)
        os.unlink(db_path)

if __name__ == "__main__":
    test_review_route()