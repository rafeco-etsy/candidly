from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import uuid

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    google_id = db.Column(db.String(255), unique=True, nullable=True)  # For Google OAuth
    
    # Permissions
    can_create_templates = db.Column(db.Boolean, default=False)
    can_create_requests_for_others = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    created_templates = db.relationship('FeedbackTemplate', foreign_keys='FeedbackTemplate.created_by_id', backref='creator', lazy=True)
    created_requests = db.relationship('FeedbackRequest', foreign_keys='FeedbackRequest.created_by_id', backref='creator', lazy=True)
    assigned_requests = db.relationship('FeedbackRequest', foreign_keys='FeedbackRequest.assigned_to_id', backref='assignee', lazy=True)
    reviewed_requests = db.relationship('FeedbackRequest', foreign_keys='FeedbackRequest.reviewer_id', backref='reviewer', lazy=True)
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def get_id(self):
        return str(self.id)

class FeedbackTemplate(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    intro_text = db.Column(db.Text, nullable=True)
    is_supervisor_feedback = db.Column(db.Boolean, default=False, nullable=False)
    created_by_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    questions = db.relationship('Question', backref='template', lazy=True)
    requests = db.relationship('FeedbackRequest', backref='template', lazy=True)

class FeedbackRequest(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    target_name = db.Column(db.String(255), nullable=False)
    target_email = db.Column(db.String(255), nullable=True)  # Optional email for the feedback target
    template_id = db.Column(db.String(36), db.ForeignKey('feedback_template.id'), nullable=False)
    created_by_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    assigned_to_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    reviewer_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=True)  # Optional reviewer before delivery
    context = db.Column(db.Text, nullable=True)  # Additional context for GPT about the relationship/situation
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    responses = db.relationship('Response', backref='feedback_request', lazy=True)

class Question(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    template_id = db.Column(db.String(36), db.ForeignKey('feedback_template.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # 'rating', 'agreement', or 'discussion'
    order_index = db.Column(db.Integer, nullable=False)

class Response(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    feedback_request_id = db.Column(db.String(36), db.ForeignKey('feedback_request.id'), nullable=False)
    question_id = db.Column(db.String(36), db.ForeignKey('question.id'), nullable=False)
    rating_value = db.Column(db.Integer, nullable=True)  # For rating questions
    agreement_value = db.Column(db.String(20), nullable=True)  # For agreement questions
    discussion_summary = db.Column(db.Text, nullable=True)  # For discussion questions
    chat_history = db.Column(db.Text, nullable=True)  # JSON string of chat messages
    is_draft = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    submitted_at = db.Column(db.DateTime, nullable=True)
    
    question = db.relationship('Question', backref='responses', lazy=True)