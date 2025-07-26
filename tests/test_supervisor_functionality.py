import pytest
import unittest.mock
from models import db, FeedbackTemplate, FeedbackRequest, Question, Response
from app import generate_feedback_summary
import json

class TestSupervisorSummarization:
    def test_generate_feedback_summary_regular(self, app):
        """Test feedback summarization for regular (non-supervisor) feedback."""
        with app.app_context():
            chat_history = [
                {"role": "user", "content": "They are very collaborative"},
                {"role": "assistant", "content": "Can you give me a specific example?"},
                {"role": "user", "content": "They helped coordinate the project launch successfully"}
            ]
            
            with unittest.mock.patch('openai.OpenAI') as mock_openai:
                mock_client = unittest.mock.Mock()
                mock_openai.return_value = mock_client
                
                mock_response = unittest.mock.Mock()
                mock_response.choices = [unittest.mock.Mock()]
                mock_response.choices[0].message.content = "They demonstrate strong collaboration skills and successfully coordinated project launches."
                mock_client.chat.completions.create.return_value = mock_response
                
                summary = generate_feedback_summary(
                    "How would you describe their teamwork?",
                    chat_history,
                    is_supervisor_feedback=False
                )
                
                assert summary == "They demonstrate strong collaboration skills and successfully coordinated project launches."
                
                # Verify the system prompt did NOT include supervisor guidance
                call_args = mock_client.chat.completions.create.call_args
                system_content = call_args[1]['messages'][0]['content']
                assert 'supervisor' not in system_content.lower()
                assert 'manager' not in system_content.lower()

    def test_generate_feedback_summary_supervisor(self, app):
        """Test feedback summarization for supervisor feedback."""
        with app.app_context():
            chat_history = [
                {"role": "user", "content": "They are an excellent leader"},
                {"role": "assistant", "content": "What makes their leadership style effective?"},
                {"role": "user", "content": "They provide clear direction and support team development"}
            ]
            
            with unittest.mock.patch('openai.OpenAI') as mock_openai:
                mock_client = unittest.mock.Mock()
                mock_openai.return_value = mock_client
                
                mock_response = unittest.mock.Mock()
                mock_response.choices = [unittest.mock.Mock()]
                mock_response.choices[0].message.content = "They demonstrate excellent leadership through clear direction and active support of team development."
                mock_client.chat.completions.create.return_value = mock_response
                
                summary = generate_feedback_summary(
                    "How would you describe their leadership style?",
                    chat_history,
                    is_supervisor_feedback=True
                )
                
                assert summary == "They demonstrate excellent leadership through clear direction and active support of team development."
                
                # Verify the system prompt INCLUDED supervisor guidance
                call_args = mock_client.chat.completions.create.call_args
                system_content = call_args[1]['messages'][0]['content']
                assert 'supervisor' in system_content.lower()
                assert 'leadership' in system_content.lower()
                assert 'management' in system_content.lower()

    def test_generate_feedback_summary_fallback(self, app):
        """Test feedback summarization fallback when OpenAI fails."""
        with app.app_context():
            chat_history = [
                {"role": "user", "content": "They are very helpful"},
                {"role": "assistant", "content": "How so?"},
                {"role": "user", "content": "Always available for questions"}
            ]
            
            with unittest.mock.patch('openai.OpenAI', side_effect=Exception("API Error")):
                summary = generate_feedback_summary(
                    "How helpful are they?",
                    chat_history,
                    is_supervisor_feedback=True
                )
                
                # Should fallback to concatenating user messages
                assert "They are very helpful" in summary
                assert "Always available for questions" in summary

class TestSupervisorFeedbackIntegration:
    def test_review_responses_uses_supervisor_context(self, client):
        """Test that review/responses endpoint uses supervisor context for summarization."""
        with client.application.app_context():
            # Create supervisor template
            template = FeedbackTemplate(
                name="Supervisor Template",
                is_supervisor_feedback=True
            )
            db.session.add(template)
            db.session.flush()
            
            question = Question(
                template_id=template.id,
                question_text="How is their management style?",
                question_type="discussion",
                order_index=0
            )
            db.session.add(question)
            
            feedback_request = FeedbackRequest(
                target_name="Manager",
                template_id=template.id
            )
            db.session.add(feedback_request)
            db.session.commit()
            
            chat_history = [
                {"role": "user", "content": "Great at team management"},
                {"role": "assistant", "content": "Can you elaborate?"},
                {"role": "user", "content": "Excellent at delegation and support"}
            ]
            
            responses_data = {
                question.id: {
                    'type': 'discussion',
                    'chat_history': chat_history
                }
            }
            
            with unittest.mock.patch('app.generate_feedback_summary') as mock_summary:
                mock_summary.return_value = "They excel at team management through effective delegation and support."
                
                response = client.post(
                    f'/review/{feedback_request.id}',
                    json=responses_data,
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                
                # Verify that generate_feedback_summary was called with supervisor flag
                mock_summary.assert_called_once_with(
                    question.question_text,
                    chat_history,
                    True  # is_supervisor_feedback should be True
                )

    def test_regular_feedback_template_integration(self, client):
        """Test that regular templates don't use supervisor context."""
        with client.application.app_context():
            # Create regular template
            template = FeedbackTemplate(
                name="Regular Template",
                is_supervisor_feedback=False
            )
            db.session.add(template)
            db.session.flush()
            
            question = Question(
                template_id=template.id,
                question_text="How is their communication?",
                question_type="discussion",
                order_index=0
            )
            db.session.add(question)
            
            feedback_request = FeedbackRequest(
                target_name="Colleague",
                template_id=template.id
            )
            db.session.add(feedback_request)
            db.session.commit()
            
            chat_history = [
                {"role": "user", "content": "Good communicator"}
            ]
            
            responses_data = {
                question.id: {
                    'type': 'discussion',
                    'chat_history': chat_history
                }
            }
            
            with unittest.mock.patch('app.generate_feedback_summary') as mock_summary:
                mock_summary.return_value = "They are a good communicator."
                
                response = client.post(
                    f'/review/{feedback_request.id}',
                    json=responses_data,
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                
                # Verify that generate_feedback_summary was called with supervisor flag as False
                mock_summary.assert_called_once_with(
                    question.question_text,
                    chat_history,
                    False  # is_supervisor_feedback should be False
                )

class TestTemplateDisplayFeatures:
    def test_template_list_shows_supervisor_badges(self, client):
        """Test that template list shows supervisor and intro text badges."""
        with client.application.app_context():
            # Create different types of templates
            regular_template = FeedbackTemplate(name="Regular Template")
            supervisor_template = FeedbackTemplate(
                name="Supervisor Template", 
                is_supervisor_feedback=True
            )
            intro_template = FeedbackTemplate(
                name="Intro Template",
                intro_text="Welcome message"
            )
            complete_template = FeedbackTemplate(
                name="Complete Template",
                intro_text="Full intro text",
                is_supervisor_feedback=True
            )
            
            db.session.add_all([regular_template, supervisor_template, intro_template, complete_template])
            db.session.commit()
            
            response = client.get('/templates')
            assert response.status_code == 200
            
            # Check for supervisor badge
            assert b'Supervisor' in response.data
            assert b'user-tie' in response.data  # Font Awesome icon
            
            # Check for intro text badge
            assert b'Has Intro' in response.data
            assert b'info-circle' in response.data  # Font Awesome icon

    def test_dashboard_shows_supervisor_indicators(self, client):
        """Test that dashboard shows supervisor template indicators."""
        with client.application.app_context():
            # Create supervisor template
            template = FeedbackTemplate(
                name="Manager Review",
                is_supervisor_feedback=True
            )
            db.session.add(template)
            db.session.flush()
            
            question = Question(
                template_id=template.id,
                question_text="Test question",
                question_type="rating",
                order_index=0
            )
            db.session.add(question)
            
            feedback_request = FeedbackRequest(
                target_name="Test Manager",
                template_id=template.id
            )
            db.session.add(feedback_request)
            db.session.commit()
            
            response = client.get('/dashboard')
            assert response.status_code == 200
            
            # Should show supervisor badge in the template column
            assert b'Manager Review' in response.data
            assert b'Supervisor' in response.data
            assert b'user-tie' in response.data  # Font Awesome icon