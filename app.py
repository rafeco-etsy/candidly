from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_migrate import Migrate
from config import Config
from app.models import db, FeedbackRequest, Question, Response
import json

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    migrate = Migrate(app, db)
    
    return app

app = create_app()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create', methods=['GET', 'POST'])
def create_request():
    if request.method == 'POST':
        target_name = request.form['target_name']
        
        # Create feedback request
        feedback_request = FeedbackRequest(target_name=target_name)
        db.session.add(feedback_request)
        db.session.flush()
        
        # Create questions
        questions_data = request.form.getlist('questions')
        question_types = request.form.getlist('question_types')
        
        for i, (question_text, question_type) in enumerate(zip(questions_data, question_types)):
            if question_text.strip():
                question = Question(
                    feedback_request_id=feedback_request.id,
                    question_text=question_text.strip(),
                    question_type=question_type,
                    order_index=i
                )
                db.session.add(question)
        
        db.session.commit()
        flash('Feedback request created successfully!')
        return redirect(url_for('share_link', request_id=feedback_request.id))
    
    return render_template('create.html')

@app.route('/share/<request_id>')
def share_link(request_id):
    feedback_request = FeedbackRequest.query.get_or_404(request_id)
    return render_template('share.html', feedback_request=feedback_request)

@app.route('/survey/<request_id>')
def survey(request_id):
    feedback_request = FeedbackRequest.query.get_or_404(request_id)
    questions = Question.query.filter_by(feedback_request_id=request_id).order_by(Question.order_index).all()
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

@app.route('/review/<request_id>')
def review_responses(request_id):
    feedback_request = FeedbackRequest.query.get_or_404(request_id)
    responses = Response.query.filter_by(feedback_request_id=request_id, is_draft=True).all()
    return render_template('review.html', feedback_request=feedback_request, responses=responses)

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

@app.route('/report/<request_id>')
def view_report(request_id):
    feedback_request = FeedbackRequest.query.get_or_404(request_id)
    responses = Response.query.filter_by(feedback_request_id=request_id, is_draft=False).all()
    return render_template('report.html', feedback_request=feedback_request, responses=responses)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)