import pytest
from datetime import datetime
from models import db, FeedbackRequest, Question, Response
import uuid
import json

class TestFeedbackRequest:
    def test_create_feedback_request(self, app):
        """Test creating a feedback request."""
        with app.app_context():
            request = FeedbackRequest(target_name="Jane Smith")
            db.session.add(request)
            db.session.commit()
            
            assert request.id is not None
            assert request.target_name == "Jane Smith"
            assert request.created_at is not None
            assert isinstance(request.created_at, datetime)

    def test_feedback_request_id_is_uuid(self, app):
        """Test that feedback request ID is a valid UUID."""
        with app.app_context():
            request = FeedbackRequest(target_name="Test User")
            db.session.add(request)
            db.session.commit()
            
            # Should be able to parse as UUID
            uuid.UUID(request.id)

class TestQuestion:
    def test_create_question(self, app, sample_feedback_request):
        """Test creating a question."""
        with app.app_context():
            question = Question(
                feedback_request_id=sample_feedback_request.id,
                question_text="How is their leadership?",
                question_type="rating",
                order_index=2
            )
            db.session.add(question)
            db.session.commit()
            
            assert question.id is not None
            assert question.question_text == "How is their leadership?"
            assert question.question_type == "rating"
            assert question.order_index == 2

    def test_question_types(self, app, sample_feedback_request):
        """Test both question types are supported."""
        with app.app_context():
            rating_q = Question(
                feedback_request_id=sample_feedback_request.id,
                question_text="Rate communication",
                question_type="rating",
                order_index=0
            )
            discussion_q = Question(
                feedback_request_id=sample_feedback_request.id,
                question_text="Describe strengths",
                question_type="discussion",
                order_index=1
            )
            
            db.session.add_all([rating_q, discussion_q])
            db.session.commit()
            
            assert rating_q.question_type == "rating"
            assert discussion_q.question_type == "discussion"

class TestResponse:
    def test_create_rating_response(self, app, sample_feedback_request):
        """Test creating a rating response."""
        with app.app_context():
            questions = Question.query.filter_by(
                feedback_request_id=sample_feedback_request.id,
                question_type="rating"
            ).first()
            
            response = Response(
                feedback_request_id=sample_feedback_request.id,
                question_id=questions.id,
                rating_value=4,
                is_draft=True
            )
            db.session.add(response)
            db.session.commit()
            
            assert response.rating_value == 4
            assert response.discussion_summary is None
            assert response.is_draft is True

    def test_create_discussion_response(self, app, sample_feedback_request):
        """Test creating a discussion response."""
        with app.app_context():
            question = Question.query.filter_by(
                feedback_request_id=sample_feedback_request.id,
                question_type="discussion"
            ).first()
            
            chat_data = [
                {"role": "user", "content": "They are great at communication"},
                {"role": "assistant", "content": "Can you provide an example?"},
                {"role": "user", "content": "They handled the client meeting very well"}
            ]
            
            response = Response(
                feedback_request_id=sample_feedback_request.id,
                question_id=question.id,
                discussion_summary="They are great at communication and handled client meetings well",
                chat_history=json.dumps(chat_data),
                is_draft=True
            )
            db.session.add(response)
            db.session.commit()
            
            assert response.rating_value is None
            assert "communication" in response.discussion_summary
            assert response.chat_history is not None
            
            # Verify chat history can be parsed back
            parsed_chat = json.loads(response.chat_history)
            assert len(parsed_chat) == 3
            assert parsed_chat[0]["role"] == "user"

    def test_response_draft_to_submitted(self, app, sample_feedback_request):
        """Test changing response from draft to submitted."""
        with app.app_context():
            question = Question.query.filter_by(
                feedback_request_id=sample_feedback_request.id
            ).first()
            
            response = Response(
                feedback_request_id=sample_feedback_request.id,
                question_id=question.id,
                rating_value=5,
                is_draft=True
            )
            db.session.add(response)
            db.session.commit()
            
            assert response.is_draft is True
            assert response.submitted_at is None
            
            # Mark as submitted
            response.is_draft = False
            response.submitted_at = datetime.utcnow()
            db.session.commit()
            
            assert response.is_draft is False
            assert response.submitted_at is not None

class TestRelationships:
    def test_feedback_request_questions_relationship(self, app, sample_feedback_request):
        """Test the relationship between feedback requests and questions."""
        with app.app_context():
            questions = sample_feedback_request.questions
            assert len(questions) == 2
            assert all(q.feedback_request_id == sample_feedback_request.id for q in questions)

    def test_feedback_request_responses_relationship(self, app, sample_feedback_request):
        """Test the relationship between feedback requests and responses."""
        with app.app_context():
            question = sample_feedback_request.questions[0]
            
            response = Response(
                feedback_request_id=sample_feedback_request.id,
                question_id=question.id,
                rating_value=3
            )
            db.session.add(response)
            db.session.commit()
            
            responses = sample_feedback_request.responses
            assert len(responses) == 1
            assert responses[0].rating_value == 3

    def test_question_responses_relationship(self, app, sample_feedback_request):
        """Test the relationship between questions and responses."""
        with app.app_context():
            question = sample_feedback_request.questions[0]
            
            # Create multiple responses for the same question
            responses = [
                Response(
                    feedback_request_id=sample_feedback_request.id,
                    question_id=question.id,
                    rating_value=i
                ) for i in range(1, 4)
            ]
            
            db.session.add_all(responses)
            db.session.commit()
            
            question_responses = question.responses
            assert len(question_responses) == 3
            assert all(r.question_id == question.id for r in question_responses)