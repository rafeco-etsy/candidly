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
            assert 'communicat' in discussion_response.discussion_summary.lower()

    def test_review_page_saves_agreement_responses(self, client):
        """Test that review page can save agreement responses."""
        with client.application.app_context():
            # Create template with agreement question
            template = FeedbackTemplate(name="Agreement Test Template")
            db.session.add(template)
            db.session.flush()
            
            agreement_question = Question(
                template_id=template.id,
                question_text="They communicate effectively",
                question_type="agreement",
                order_index=0
            )
            db.session.add(agreement_question)
            
            feedback_request = FeedbackRequest(
                target_name="Test User",
                template_id=template.id
            )
            db.session.add(feedback_request)
            db.session.commit()
            
            responses_data = {
                agreement_question.id: {
                    'type': 'agreement',
                    'value': 'strongly_agree'
                }
            }
            
            response = client.post(
                f'/review/{feedback_request.id}',
                json=responses_data,
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            
            # Verify agreement response was saved
            saved_response = Response.query.filter_by(
                feedback_request_id=feedback_request.id,
                question_id=agreement_question.id,
                is_draft=True
            ).first()
            
            assert saved_response is not None
            assert saved_response.agreement_value == 'strongly_agree'
            assert saved_response.rating_value is None
            assert saved_response.discussion_summary is None

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

class TestTemplateRoutes:
    def test_list_templates_empty(self, client):
        """Test template list page with no templates."""
        response = client.get('/templates')
        assert response.status_code == 200
        assert b'No templates created yet' in response.data

    def test_list_templates_with_data(self, client, sample_template):
        """Test template list page with templates."""
        response = client.get('/templates')
        assert response.status_code == 200
        assert b'Test Template' in response.data
        assert b'questions' in response.data

    def test_create_template_get(self, client):
        """Test GET request to create template page."""
        response = client.get('/templates/create')
        assert response.status_code == 200
        assert b'Create Feedback Template' in response.data
        assert b'Template Name' in response.data
        assert b'Introduction Text' in response.data
        assert b'This is supervisor feedback' in response.data

    def test_create_template_basic(self, client):
        """Test creating a basic template."""
        response = client.post('/templates/create', data={
            'name': 'Basic Template',
            'description': 'A simple template',
            'questions': ['How is their communication?'],
            'question_types': ['rating']
        })
        
        assert response.status_code == 302  # Redirect after creation
        
        with client.application.app_context():
            template = FeedbackTemplate.query.first()
            assert template is not None
            assert template.name == 'Basic Template'
            assert template.description == 'A simple template'
            assert template.intro_text == '' or template.intro_text is None
            assert template.is_supervisor_feedback is False

    def test_create_template_with_intro_text(self, client):
        """Test creating a template with introduction text."""
        intro_text = "Welcome to this survey.\n\nPlease provide honest feedback."
        response = client.post('/templates/create', data={
            'name': 'Template with Intro',
            'description': 'Has introduction text',
            'intro_text': intro_text,
            'questions': ['Rate their skills'],
            'question_types': ['rating']
        })
        
        assert response.status_code == 302
        
        with client.application.app_context():
            template = FeedbackTemplate.query.first()
            assert template.intro_text == intro_text
            assert 'Welcome' in template.intro_text
            assert 'honest feedback' in template.intro_text

    def test_create_supervisor_template(self, client):
        """Test creating a template marked as supervisor feedback."""
        response = client.post('/templates/create', data={
            'name': 'Supervisor Review',
            'description': 'For reviewing supervisors',
            'is_supervisor_feedback': '1',  # Checkbox value
            'questions': ['How is their leadership?'],
            'question_types': ['discussion']
        })
        
        assert response.status_code == 302
        
        with client.application.app_context():
            template = FeedbackTemplate.query.first()
            assert template.is_supervisor_feedback is True

    def test_create_template_with_agreement_questions(self, client):
        """Test creating a template with agreement questions."""
        response = client.post('/templates/create', data={
            'name': 'Agreement Template',
            'description': 'Template with agreement questions',
            'questions': ['They communicate clearly', 'Rate their technical skills'],
            'question_types': ['agreement', 'rating']
        })
        
        assert response.status_code == 302
        
        with client.application.app_context():
            template = FeedbackTemplate.query.first()
            assert template.name == 'Agreement Template'
            questions = template.questions
            assert len(questions) == 2
            
            agreement_q = next(q for q in questions if q.question_type == 'agreement')
            rating_q = next(q for q in questions if q.question_type == 'rating')
            
            assert agreement_q.question_text == 'They communicate clearly'
            assert rating_q.question_text == 'Rate their technical skills'

    def test_create_complete_template(self, client):
        """Test creating a template with all fields and question types."""
        intro_text = "Supervisor feedback survey.\n\nFocus on leadership behaviors."
        response = client.post('/templates/create', data={
            'name': 'Complete Supervisor Template',
            'description': 'Full-featured supervisor template',
            'intro_text': intro_text,
            'is_supervisor_feedback': '1',
            'questions': ['Rate leadership skills', 'They delegate effectively', 'Describe management style'],
            'question_types': ['rating', 'agreement', 'discussion']
        })
        
        assert response.status_code == 302
        
        with client.application.app_context():
            template = FeedbackTemplate.query.first()
            assert template.name == 'Complete Supervisor Template'
            assert template.intro_text == intro_text
            assert template.is_supervisor_feedback is True
            assert len(template.questions) == 3
            
            # Verify all question types
            question_types = [q.question_type for q in template.questions]
            assert 'rating' in question_types
            assert 'agreement' in question_types  
            assert 'discussion' in question_types

class TestSupervisorFeedbackFeatures:
    def test_survey_displays_intro_text(self, client):
        """Test that survey page displays introduction text."""
        with client.application.app_context():
            # Create template with intro text
            template = FeedbackTemplate(
                name="Template with Intro",
                intro_text="Welcome message.\n\nSecond paragraph."
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
                target_name="Test User",
                template_id=template.id
            )
            db.session.add(feedback_request)
            db.session.commit()
            
            response = client.get(f'/survey/{feedback_request.id}')
            assert response.status_code == 200
            assert b'Welcome message.' in response.data
            assert b'Second paragraph.' in response.data

    def test_supervisor_chat_context(self, client):
        """Test that supervisor templates get special AI context."""
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
                question_text="How is their leadership?",
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
            
            # Mock the OpenAI response to avoid actual API calls in tests
            import unittest.mock
            with unittest.mock.patch('openai.OpenAI') as mock_openai:
                mock_client = unittest.mock.Mock()
                mock_openai.return_value = mock_client
                
                mock_response = unittest.mock.Mock()
                mock_response.choices = [unittest.mock.Mock()]
                mock_response.choices[0].message.content = "Tell me about their team management style."
                mock_client.chat.completions.create.return_value = mock_response
                
                response = client.post(
                    f'/api/chat/{question.id}',
                    json={
                        'message': 'They are a good leader',
                        'feedback_request_id': feedback_request.id
                    }
                )
                
                assert response.status_code == 200
                
                # Verify the API was called with supervisor context
                mock_client.chat.completions.create.assert_called_once()
                call_args = mock_client.chat.completions.create.call_args
                messages = call_args[1]['messages']
                system_message = messages[0]['content']
                
                # Check that supervisor-specific guidance is included
                assert 'supervisor' in system_message.lower()
                assert 'management' in system_message.lower()
                assert 'leadership' in system_message.lower()