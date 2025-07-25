import pytest
import json
from models import db, FeedbackTemplate, FeedbackRequest, Question, Response

class TestIndexRoute:
    def test_index_page(self, client):
        """Test the home page loads correctly."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Candidly' in response.data
        assert b'Create Feedback Request' in response.data

class TestCreateRequest:
    def test_create_request_get_with_templates(self, client, sample_template):
        """Test GET request to create page with available templates."""
        response = client.get('/create')
        assert response.status_code == 200
        assert b'Create Feedback Request' in response.data
        assert b'Test Template' in response.data

    def test_create_request_get_no_templates(self, client):
        """Test GET request to create page with no templates."""
        response = client.get('/create')
        assert response.status_code == 200
        assert b'No templates available' in response.data

    def test_create_request_post(self, client, sample_template):
        """Test POST request to create feedback request."""
        response = client.post('/create', data={
            'target_name': 'John Doe',
            'template_id': sample_template.id
        })
        
        assert response.status_code == 302  # Redirect after creation
        
        # Verify feedback request was created
        with client.application.app_context():
            request = FeedbackRequest.query.first()
            assert request is not None
            assert request.target_name == 'John Doe'
            assert request.template_id == sample_template.id

class TestShareLink:
    def test_share_link_valid_request(self, client, sample_feedback_request):
        """Test share link page with valid request."""
        response = client.get(f'/share/{sample_feedback_request.id}')
        assert response.status_code == 200
        assert b'John Doe' in response.data
        assert b'Share this link' in response.data

    def test_share_link_invalid_request(self, client):
        """Test share link page with invalid request ID."""
        response = client.get('/share/invalid-id')
        assert response.status_code == 404

class TestSurvey:
    def test_survey_page_valid_request(self, client, sample_feedback_request, sample_template):
        """Test survey page loads with questions from template."""
        response = client.get(f'/survey/{sample_feedback_request.id}')
        assert response.status_code == 200
        assert b'John Doe' in response.data
        assert b'How would you rate their communication?' in response.data
        assert b'What are their greatest strengths?' in response.data

    def test_survey_page_invalid_request(self, client):
        """Test survey page with invalid request ID."""
        response = client.get('/survey/invalid-id')
        assert response.status_code == 404

class TestChatAPI:
    def test_chat_response_api(self, client, sample_feedback_request, sample_template):
        """Test the chat API endpoint."""
        with client.application.app_context():
            question = Question.query.filter_by(
                template_id=sample_template.id,
                question_type='discussion'
            ).first()
            
            response = client.post(
                f'/api/chat/{question.id}',
                json={'message': 'They are very collaborative'}
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'response' in data
            assert 'is_final' in data
            assert isinstance(data['is_final'], bool)

    def test_chat_response_completion_detection(self, client, sample_feedback_request, sample_template):
        """Test that chat detects completion properly."""
        with client.application.app_context():
            question = Question.query.filter_by(
                template_id=sample_template.id,
                question_type='discussion'    
            ).first()
            
            # Test with completion phrases that match our logic
            completion_phrases = ['done', 'nothing else', 'I have nothing more to add']
            
            for phrase in completion_phrases:
                response = client.post(
                    f'/api/chat/{question.id}',
                    json={'message': phrase}
                )
                
                data = json.loads(response.data)
                assert data['is_final'] is True

class TestReviewResponses:
    def test_review_page_empty_responses(self, client, sample_feedback_request):
        """Test review page with no responses yet."""
        response = client.get(f'/review/{sample_feedback_request.id}')
        assert response.status_code == 200
        assert b'John Doe' in response.data

    def test_review_page_saves_responses(self, client, sample_feedback_request):
        """Test that review page can save responses via POST."""
        with client.application.app_context():
            questions = Question.query.filter_by(
                template_id=sample_feedback_request.template_id
            ).all()
            
            rating_question = next(q for q in questions if q.question_type == 'rating')
            discussion_question = next(q for q in questions if q.question_type == 'discussion')
            
            responses_data = {
                rating_question.id: {
                    'type': 'rating',
                    'value': '4'
                },
                discussion_question.id: {
                    'type': 'discussion',
                    'chat_history': [
                        {'role': 'user', 'content': 'They are excellent communicators'},
                        {'role': 'assistant', 'content': 'Can you provide an example?'},
                        {'role': 'user', 'content': 'They led the team meeting very well'}
                    ]
                }
            }
            
            response = client.post(
                f'/review/{sample_feedback_request.id}',
                json=responses_data,
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            
            # Verify responses were saved
            saved_responses = Response.query.filter_by(
                feedback_request_id=sample_feedback_request.id,
                is_draft=True
            ).all()
            
            assert len(saved_responses) == 2
            
            rating_response = next(r for r in saved_responses if r.rating_value is not None)
            discussion_response = next(r for r in saved_responses if r.discussion_summary is not None)
            
            assert rating_response.rating_value == 4
            assert 'excellent communicators' in discussion_response.discussion_summary

    def test_review_page_json_serialization(self, client, sample_feedback_request):
        """Test that review page properly serializes questions and responses to JSON."""
        with client.application.app_context():
            # Create some sample responses
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
            
            # This should not raise a JSON serialization error
            response = client.get(f'/review/{sample_feedback_request.id}')
            assert response.status_code == 200
            
            # Check that the page contains JSON data
            assert b'const questions = ' in response.data
            assert b'const responses = ' in response.data

class TestSubmitFeedback:
    def test_submit_feedback(self, client, sample_feedback_request):
        """Test submitting feedback marks responses as not draft."""
        with client.application.app_context():
            question = Question.query.filter_by(
                template_id=sample_feedback_request.template_id
            ).first()
            
            # Create a draft response
            response = Response(
                feedback_request_id=sample_feedback_request.id,
                question_id=question.id,
                rating_value=3,
                is_draft=True
            )
            db.session.add(response)
            db.session.commit()
            
            # Submit the feedback
            submit_response = client.post(f'/submit/{sample_feedback_request.id}')
            assert submit_response.status_code == 302  # Redirect to thank you page
            
            # Verify response is no longer draft
            updated_response = Response.query.first()
            assert updated_response.is_draft is False
            assert updated_response.submitted_at is not None

class TestViewReport:
    def test_view_report_no_responses(self, client, sample_feedback_request):
        """Test report page with no submitted responses."""
        response = client.get(f'/report/{sample_feedback_request.id}')
        assert response.status_code == 200
        assert b'No feedback submitted yet' in response.data

    def test_view_report_with_responses(self, client, sample_feedback_request):
        """Test report page with submitted responses."""
        with client.application.app_context():
            question = Question.query.filter_by(
                template_id=sample_feedback_request.template_id
            ).first()
            
            # Create a submitted response
            response = Response(
                feedback_request_id=sample_feedback_request.id,
                question_id=question.id,
                rating_value=4,
                is_draft=False
            )
            db.session.add(response)
            db.session.commit()
            
            report_response = client.get(f'/report/{sample_feedback_request.id}')
            assert report_response.status_code == 200
            assert b'John Doe' in report_response.data
            # Should not show the "no feedback" message
            assert b'No feedback submitted yet' not in report_response.data

class TestThankYou:
    def test_thank_you_page(self, client):
        """Test thank you page loads correctly."""
        response = client.get('/thank-you')
        assert response.status_code == 200
        assert b'Thank You!' in response.data
        assert b'feedback has been submitted' in response.data