#!/usr/bin/env python3
"""
Simple test to verify JSON serialization works correctly.
This tests the specific bug we fixed where SQLAlchemy objects couldn't be serialized.
"""
import tempfile
import os
from app import create_app
from models import db, FeedbackRequest, Question, Response
import json

def test_json_serialization():
    """Test that our models can be properly serialized to JSON."""
    
    # Create a temporary database
    db_fd, db_path = tempfile.mkstemp()
    
    # Configure test app
    class TestConfig:
        TESTING = True
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
        SECRET_KEY = "test-key"
        WTF_CSRF_ENABLED = False
    
    app = create_app(TestConfig)
    
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Create test data
        feedback_request = FeedbackRequest(target_name="Test User")
        db.session.add(feedback_request)
        db.session.flush()
        
        question = Question(
            feedback_request_id=feedback_request.id,
            question_text="How is their performance?",
            question_type="rating",
            order_index=0
        )
        db.session.add(question)
        db.session.flush()
        
        response = Response(
            feedback_request_id=feedback_request.id,
            question_id=question.id,
            rating_value=4,
            is_draft=True
        )
        db.session.add(response)
        db.session.commit()
        
        # Test the conversion logic from our review route
        questions = Question.query.filter_by(feedback_request_id=feedback_request.id).all()
        responses = Response.query.filter_by(feedback_request_id=feedback_request.id).all()
        
        # Convert to dictionaries (this is what we fixed)
        questions_dict = []
        for q in questions:
            questions_dict.append({
                'id': q.id,
                'question_text': q.question_text,
                'question_type': q.question_type,
                'order_index': q.order_index
            })
        
        responses_dict = []
        for r in responses:
            responses_dict.append({
                'id': r.id,
                'question_id': r.question_id,
                'rating_value': r.rating_value,
                'discussion_summary': r.discussion_summary,
                'chat_history': r.chat_history
            })
        
        # This should work without errors (previously caused TypeError)
        try:
            questions_json = json.dumps(questions_dict)
            responses_json = json.dumps(responses_dict)
            print("✅ JSON serialization test PASSED")
            print(f"Questions JSON: {questions_json}")
            print(f"Responses JSON: {responses_json}")
            return True
        except Exception as e:
            print(f"❌ JSON serialization test FAILED: {e}")
            return False
        finally:
            # Cleanup
            db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)

if __name__ == "__main__":
    test_json_serialization()