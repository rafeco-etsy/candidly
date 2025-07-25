import pytest
import json
from models import db, FeedbackTemplate, FeedbackRequest, Question, Response

class TestTemplateRoutes:
    def test_list_templates_empty(self, client):
        """Test templates list page with no templates."""
        response = client.get('/templates')
        assert response.status_code == 200
        assert b'No templates created yet' in response.data

    def test_create_template_get(self, client):
        """Test GET request to create template page."""
        response = client.get('/templates/create')
        assert response.status_code == 200
        assert b'Create Feedback Template' in response.data

    def test_create_template_post(self, client):
        """Test POST request to create template."""
        response = client.post('/templates/create', data={
            'name': 'Manager Review Template',
            'description': 'For reviewing managers',
            'questions': ['How is their leadership?', 'What are their strengths?'],
            'question_types': ['rating', 'discussion']
        })
        
        assert response.status_code == 302  # Redirect after creation
        
        # Verify template was created
        with client.application.app_context():
            template = FeedbackTemplate.query.first()
            assert template is not None
            assert template.name == 'Manager Review Template'
            assert template.description == 'For reviewing managers'
            
            questions = Question.query.filter_by(template_id=template.id).all()
            assert len(questions) == 2
            assert questions[0].question_text == 'How is their leadership?'
            assert questions[0].question_type == 'rating'
            assert questions[1].question_text == 'What are their strengths?'
            assert questions[1].question_type == 'discussion'

    def test_list_templates_with_data(self, client, sample_template):
        """Test templates list page with templates."""
        response = client.get('/templates')
        assert response.status_code == 200
        assert b'Test Template' in response.data
        assert b'2 questions' in response.data

class TestTemplateBasedWorkflow:
    def test_create_request_with_template(self, client, sample_template):
        """Test creating a feedback request using a template."""
        response = client.post('/create', data={
            'target_name': 'Alice Johnson',
            'template_id': sample_template.id
        })
        
        assert response.status_code == 302  # Redirect after creation
        
        # Verify request was created with correct template
        with client.application.app_context():
            request = FeedbackRequest.query.first()
            assert request is not None
            assert request.target_name == 'Alice Johnson'
            assert request.template_id == sample_template.id

    def test_create_request_page_shows_templates(self, client, sample_template):
        """Test that create request page shows available templates."""
        response = client.get('/create')
        assert response.status_code == 200
        assert b'Test Template' in response.data
        assert b'Choose a template' in response.data

    def test_create_request_no_templates(self, client):
        """Test create request page when no templates exist."""
        response = client.get('/create')
        assert response.status_code == 200
        assert b'No templates available' in response.data
        assert b'Create Your First Template' in response.data

    def test_survey_uses_template_questions(self, client, sample_template, sample_feedback_request):
        """Test that survey page uses questions from the template."""
        response = client.get(f'/survey/{sample_feedback_request.id}')
        assert response.status_code == 200
        assert b'How would you rate their communication?' in response.data
        assert b'What are their greatest strengths?' in response.data

class TestTemplateAndRequestIntegration:
    def test_complete_template_workflow(self, client):
        """Test the complete workflow from template creation to feedback submission."""
        
        # Step 1: Create a template
        template_response = client.post('/templates/create', data={
            'name': 'Employee Feedback',
            'description': 'Annual employee review',
            'questions': [
                'How would you rate their performance?',
                'What are their key achievements?',
                'Areas for improvement?'
            ],
            'question_types': ['rating', 'discussion', 'discussion']
        })
        
        assert template_response.status_code == 302
        
        with client.application.app_context():
            template = FeedbackTemplate.query.first()
            assert template.name == 'Employee Feedback'
            
            # Step 2: Create a feedback request using the template
            request_response = client.post('/create', data={
                'target_name': 'Bob Wilson',
                'template_id': template.id
            })
            
            assert request_response.status_code == 302
            
            feedback_request = FeedbackRequest.query.first()
            assert feedback_request.target_name == 'Bob Wilson'
            assert feedback_request.template_id == template.id
            
            # Step 3: Access the survey
            survey_response = client.get(f'/survey/{feedback_request.id}')
            assert survey_response.status_code == 200
            
            # Step 4: Submit responses
            questions = Question.query.filter_by(template_id=template.id).order_by(Question.order_index).all()
            
            responses_data = {
                questions[0].id: {
                    'type': 'rating',
                    'value': '5'
                },
                questions[1].id: {
                    'type': 'discussion',
                    'chat_history': [
                        {'role': 'user', 'content': 'Led three major projects successfully'}
                    ]
                },
                questions[2].id: {
                    'type': 'discussion', 
                    'chat_history': [
                        {'role': 'user', 'content': 'Could improve time management'}
                    ]
                }
            }
            
            save_response = client.post(
                f'/review/{feedback_request.id}',
                json=responses_data,
                content_type='application/json'
            )
            
            assert save_response.status_code == 200
            assert json.loads(save_response.data)['success'] is True
            
            # Step 5: Submit final feedback
            submit_response = client.post(f'/submit/{feedback_request.id}')
            assert submit_response.status_code == 302
            
            # Verify responses were saved
            saved_responses = Response.query.filter_by(
                feedback_request_id=feedback_request.id,
                is_draft=False
            ).all()
            
            assert len(saved_responses) == 3

    def test_template_reuse(self, client, sample_template):
        """Test that templates can be reused for multiple requests."""
        
        # Create first request
        response1 = client.post('/create', data={
            'target_name': 'Person A',
            'template_id': sample_template.id
        })
        assert response1.status_code == 302
        
        # Create second request with same template
        response2 = client.post('/create', data={
            'target_name': 'Person B', 
            'template_id': sample_template.id
        })
        assert response2.status_code == 302
        
        with client.application.app_context():
            requests = FeedbackRequest.query.filter_by(template_id=sample_template.id).all()
            assert len(requests) == 2
            assert requests[0].target_name == 'Person A'
            assert requests[1].target_name == 'Person B'

class TestTemplateDashboard:
    def test_dashboard_shows_template_info(self, client, sample_template, sample_feedback_request):
        """Test that dashboard shows template-based requests correctly."""
        response = client.get('/dashboard')
        assert response.status_code == 200
        assert b'John Doe' in response.data  # Target name from sample_feedback_request