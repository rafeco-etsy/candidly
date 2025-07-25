from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class FeedbackRequest(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    target_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    questions = db.relationship('Question', backref='feedback_request', lazy=True)
    responses = db.relationship('Response', backref='feedback_request', lazy=True)

class Question(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    feedback_request_id = db.Column(db.String(36), db.ForeignKey('feedback_request.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # 'rating' or 'discussion'
    order_index = db.Column(db.Integer, nullable=False)

class Response(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    feedback_request_id = db.Column(db.String(36), db.ForeignKey('feedback_request.id'), nullable=False)
    question_id = db.Column(db.String(36), db.ForeignKey('question.id'), nullable=False)
    rating_value = db.Column(db.Integer, nullable=True)  # For rating questions
    discussion_summary = db.Column(db.Text, nullable=True)  # For discussion questions
    chat_history = db.Column(db.Text, nullable=True)  # JSON string of chat messages
    is_draft = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    submitted_at = db.Column(db.DateTime, nullable=True)
    
    question = db.relationship('Question', backref='responses', lazy=True)