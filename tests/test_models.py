import pytest
from datetime import datetime
from models import db, FeedbackTemplate, FeedbackRequest, Question, Response
import uuid
import json

class TestFeedbackTemplate:
    def test_create_feedback_template(self, app):
        """Test creating a feedback template."""
        with app.app_context():
            template = FeedbackTemplate(name="Manager Review", description="For reviewing managers")
            db.session.add(template)
            db.session.commit()
            
            assert template.id is not None
            assert template.name == "Manager Review"
            assert template.description == "For reviewing managers"
            assert template.created_at is not None
            assert isinstance(template.created_at, datetime)

    def test_feedback_template_id_is_uuid(self, app):
        """Test that feedback template ID is a valid UUID."""
        with app.app_context():
            template = FeedbackTemplate(name="Test Template")
            db.session.add(template)
            db.session.commit()
            
            # Should be able to parse as UUID
            uuid.UUID(template.id)

    def test_create_template_with_intro_text(self, app):
        """Test creating a template with introduction text."""
        with app.app_context():
            intro_text = "Welcome to this feedback survey.\n\nPlease provide honest and constructive feedback."
            template = FeedbackTemplate(
                name="Detailed Template",
                description="Template with intro",
                intro_text=intro_text
            )
            db.session.add(template)
            db.session.commit()
            
            assert template.intro_text == intro_text
            assert "\n\n" in template.intro_text  # Multiple paragraphs supported

    def test_create_supervisor_feedback_template(self, app):
        """Test creating a template marked as supervisor feedback."""
        with app.app_context():
            template = FeedbackTemplate(
                name="Supervisor Review",
                description="For reviewing supervisors",
                is_supervisor_feedback=True
            )
            db.session.add(template)
            db.session.commit()
            
            assert template.is_supervisor_feedback is True

    def test_template_defaults(self, app):
        """Test default values for new template fields."""
        with app.app_context():
            template = FeedbackTemplate(name="Basic Template")
            db.session.add(template)
            db.session.commit()
            
            assert template.intro_text is None
            assert template.is_supervisor_feedback is False

    def test_create_full_featured_template(self, app):
        """Test creating a template with all fields populated."""
        with app.app_context():
            template = FeedbackTemplate(
                name="Complete Template",
                description="A complete template with all features",
                intro_text="Introduction paragraph 1.\n\nIntroduction paragraph 2.",
                is_supervisor_feedback=True
            )
            db.session.add(template)
            db.session.commit()
            
            assert template.name == "Complete Template"
            assert template.description == "A complete template with all features"
            assert "paragraph 1" in template.intro_text
            assert "paragraph 2" in template.intro_text
            assert template.is_supervisor_feedback is True

class TestFeedbackRequest:
    def test_create_feedback_request(self, app, sample_template):
        """Test creating a feedback request."""
        with app.app_context():
            request = FeedbackRequest(target_name="Jane Smith", template_id=sample_template.id)
            db.session.add(request)
            db.session.commit()
            
            assert request.id is not None
            assert request.target_name == "Jane Smith"
            assert request.template_id == sample_template.id
            assert request.created_at is not None
            assert isinstance(request.created_at, datetime)

    def test_feedback_request_id_is_uuid(self, app, sample_template):
        """Test that feedback request ID is a valid UUID."""
        with app.app_context():
            request = FeedbackRequest(target_name="Test User", template_id=sample_template.id)
            db.session.add(request)
            db.session.commit()
            
            # Should be able to parse as UUID
            uuid.UUID(request.id)

class TestQuestion:
    def test_create_question(self, app, sample_template):
        """Test creating a question."""
        with app.app_context():
            question = Question(
                template_id=sample_template.id,
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

    def test_question_types(self, app, sample_template):
        """Test all question types are supported."""
        with app.app_context():
            rating_q = Question(
                template_id=sample_template.id,
                question_text="Rate communication",
                question_type="rating",
                order_index=0
            )
            agreement_q = Question(
                template_id=sample_template.id,
                question_text="They communicate effectively",
                question_type="agreement",
                order_index=1
            )
            discussion_q = Question(
                template_id=sample_template.id,
                question_text="Describe strengths",
                question_type="discussion",
                order_index=2
            )
            
            db.session.add_all([rating_q, agreement_q, discussion_q])
            db.session.commit()
            
            assert rating_q.question_type == "rating"
            assert agreement_q.question_type == "agreement"
            assert discussion_q.question_type == "discussion"

class TestResponse:
    def test_create_rating_response(self, app, sample_feedback_request):
        """Test creating a rating response."""
        with app.app_context():
            questions = Question.query.filter_by(
                template_id=sample_feedback_request.template_id,
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

    def test_create_agreement_response(self, app, sample_feedback_request):
        """Test creating an agreement response."""
        with app.app_context():
            # Create an agreement question
            agreement_question = Question(
                template_id=sample_feedback_request.template_id,
                question_text="They communicate effectively with the team",
                question_type="agreement",
                order_index=2
            )
            db.session.add(agreement_question)
            db.session.commit()
            
            response = Response(
                feedback_request_id=sample_feedback_request.id,
                question_id=agreement_question.id,
                agreement_value="strongly_agree",
                is_draft=True
            )
            db.session.add(response)
            db.session.commit()
            
            assert response.rating_value is None
            assert response.discussion_summary is None
            assert response.agreement_value == "strongly_agree"

    def test_agreement_response_values(self, app, sample_feedback_request):
        """Test all valid agreement response values."""
        with app.app_context():
            agreement_question = Question(
                template_id=sample_feedback_request.template_id,
                question_text="Test agreement question",
                question_type="agreement",
                order_index=3
            )
            db.session.add(agreement_question)
            db.session.commit()
            
            agreement_values = ["strongly_agree", "agree", "disagree", "strongly_disagree", "na"]
            
            for value in agreement_values:
                response = Response(
                    feedback_request_id=sample_feedback_request.id,
                    question_id=agreement_question.id,
                    agreement_value=value,
                    is_draft=True
                )
                db.session.add(response)
            
            db.session.commit()
            
            saved_responses = Response.query.filter_by(question_id=agreement_question.id).all()
            saved_values = [r.agreement_value for r in saved_responses]
            
            for value in agreement_values:
                assert value in saved_values

    def test_create_discussion_response(self, app, sample_feedback_request):
        """Test creating a discussion response."""
        with app.app_context():
            question = Question.query.filter_by(
                template_id=sample_feedback_request.template_id,
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
            assert response.agreement_value is None
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
                template_id=sample_feedback_request.template_id
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
    def test_template_questions_relationship(self, app, sample_template):
        """Test the relationship between templates and questions."""
        with app.app_context():
            questions = sample_template.questions
            assert len(questions) == 2
            assert all(q.template_id == sample_template.id for q in questions)

    def test_template_requests_relationship(self, app, sample_template, sample_feedback_request):
        """Test the relationship between templates and feedback requests."""
        with app.app_context():
            requests = sample_template.requests
            assert len(requests) == 1
            assert requests[0].template_id == sample_template.id

    def test_feedback_request_responses_relationship(self, app, sample_feedback_request):
        """Test the relationship between feedback requests and responses."""
        with app.app_context():
            question = Question.query.filter_by(template_id=sample_feedback_request.template_id).first()
            
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

    def test_question_responses_relationship(self, app, sample_template, sample_feedback_request):
        """Test the relationship between questions and responses."""
        with app.app_context():
            question = sample_template.questions[0]
            
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