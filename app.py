from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_migrate import Migrate
from config import Config
from models import db, FeedbackTemplate, FeedbackRequest, Question, Response
from datetime import datetime
import json

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Register routes
    register_routes(app)
    
    return app

def register_routes(app):
    """Register all routes with the Flask app."""
    
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/templates')
    def list_templates():
        """List all feedback templates."""
        templates = FeedbackTemplate.query.order_by(FeedbackTemplate.created_at.desc()).all()
        return render_template('templates/list.html', templates=templates)

    @app.route('/templates/create', methods=['GET', 'POST'])
    def create_template():
        """Create a new feedback template."""
        if request.method == 'POST':
            name = request.form['name']
            description = request.form.get('description', '')
            
            # Create template
            template = FeedbackTemplate(name=name, description=description)
            db.session.add(template)
            db.session.flush()
            
            # Create questions
            questions_data = request.form.getlist('questions')
            question_types = request.form.getlist('question_types')
            
            for i, (question_text, question_type) in enumerate(zip(questions_data, question_types)):
                if question_text.strip():
                    question = Question(
                        template_id=template.id,
                        question_text=question_text.strip(),
                        question_type=question_type,
                        order_index=i
                    )
                    db.session.add(question)
            
            db.session.commit()
            flash('Feedback template created successfully!')
            return redirect(url_for('list_templates'))
        
        return render_template('templates/create.html')

    @app.route('/create', methods=['GET', 'POST'])
    def create_request():
        if request.method == 'POST':
            target_name = request.form['target_name']
            template_id = request.form['template_id']
            
            # Create feedback request
            feedback_request = FeedbackRequest(target_name=target_name, template_id=template_id)
            db.session.add(feedback_request)
            db.session.commit()
            
            flash('Feedback request created successfully!')
            return redirect(url_for('share_link', request_id=feedback_request.id))
        
        # Get available templates
        templates = FeedbackTemplate.query.order_by(FeedbackTemplate.name).all()
        return render_template('create.html', templates=templates)

    @app.route('/share/<request_id>')
    def share_link(request_id):
        feedback_request = FeedbackRequest.query.get_or_404(request_id)
        return render_template('share.html', feedback_request=feedback_request)

    @app.route('/survey/<request_id>')
    def survey(request_id):
        feedback_request = FeedbackRequest.query.get_or_404(request_id)
        questions = Question.query.filter_by(template_id=feedback_request.template_id).order_by(Question.order_index).all()
        return render_template('survey.html', feedback_request=feedback_request, questions=questions)

    @app.route('/api/chat/<question_id>', methods=['POST'])
    def chat_response(question_id):
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        # Simple chatbot logic for MVP
        # In production, integrate with OpenAI or similar AI service
        follow_up_questions = [
            "Can you share a specific example?",
            "How has this impacted the team or project?",
            "What made this particularly effective or challenging?",
            "Is there anything else you'd like to add?"
        ]
        
        # Simple response logic - in real implementation, use AI
        if len(user_message) < 20:
            response = follow_up_questions[0]
        elif "example" not in user_message.lower():
            response = follow_up_questions[0]
        elif len(user_message) < 50:
            response = follow_up_questions[1]
        else:
            response = follow_up_questions[3]
        
        return jsonify({
            'response': response,
            'is_final': 'done' in user_message.lower() or 'nothing' in user_message.lower()
        })

    @app.route('/review/<request_id>', methods=['GET', 'POST'])
    def review_responses(request_id):
        feedback_request = FeedbackRequest.query.get_or_404(request_id)
        questions = Question.query.filter_by(template_id=feedback_request.template_id).order_by(Question.order_index).all()
        
        if request.method == 'POST':
            # Save responses from the survey
            responses_data = request.get_json()
            
            # Clear existing draft responses
            Response.query.filter_by(feedback_request_id=request_id, is_draft=True).delete()
            
            # Save new responses
            for question_id, response_data in responses_data.items():
                response = Response(
                    feedback_request_id=request_id,
                    question_id=question_id,
                    is_draft=True
                )
                
                if response_data['type'] == 'rating':
                    response.rating_value = None if response_data['value'] == '' else (
                        None if response_data['value'] == 'na' else int(response_data['value'])
                    )
                else:  # discussion
                    response.chat_history = json.dumps(response_data.get('chat_history', []))
                    # Generate summary from chat history
                    user_messages = [msg['content'] for msg in response_data.get('chat_history', []) if msg['role'] == 'user']
                    response.discussion_summary = ' '.join(user_messages) if user_messages else 'No response provided'
                
                db.session.add(response)
            
            db.session.commit()
            return jsonify({'success': True})
        
        responses = Response.query.filter_by(feedback_request_id=request_id, is_draft=True).all()
        
        # Convert SQLAlchemy objects to dictionaries for JSON serialization
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
        
        return render_template('review.html', 
                             feedback_request=feedback_request, 
                             questions=questions_dict, 
                             responses=responses_dict)

    @app.route('/submit/<request_id>', methods=['POST'])
    def submit_feedback(request_id):
        # Update all draft responses to submitted
        responses = Response.query.filter_by(feedback_request_id=request_id, is_draft=True).all()
        for response in responses:
            response.is_draft = False
            response.submitted_at = datetime.utcnow()
        
        db.session.commit()
        flash('Feedback submitted successfully!')
        return redirect(url_for('thank_you'))

    @app.route('/thank-you')
    def thank_you():
        return render_template('thank_you.html')

    @app.route('/dashboard')
    def dashboard():
        """Dashboard to view all feedback requests and their status."""
        feedback_requests = FeedbackRequest.query.order_by(FeedbackRequest.created_at.desc()).all()
        
        # Add submission count for each request
        requests_with_counts = []
        for request in feedback_requests:
            submitted_count = Response.query.filter_by(
                feedback_request_id=request.id, 
                is_draft=False
            ).count()
            requests_with_counts.append({
                'request': request,
                'submitted_count': submitted_count
            })
        
        return render_template('dashboard.html', requests_with_counts=requests_with_counts)

    @app.route('/report/<request_id>')
    def view_report(request_id):
        feedback_request = FeedbackRequest.query.get_or_404(request_id)
        responses = Response.query.filter_by(feedback_request_id=request_id, is_draft=False).all()
        return render_template('report.html', feedback_request=feedback_request, responses=responses)

# Create the app instance
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='127.0.0.1', port=5001)