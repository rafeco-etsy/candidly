from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_migrate import Migrate
from flask_login import login_required, current_user, login_user, logout_user
from config import Config
from models import db, FeedbackTemplate, FeedbackRequest, Question, Response, User
from auth import init_auth, auto_login_dev_user, require_permission, ensure_authenticated, can_access_request, can_complete_request, get_users_for_assignment, get_or_create_dev_user
from datetime import datetime
import json
import openai
import os
import base64

def generate_personalized_coaching(feedback_request, responses, safety_analysis):
    """Generate personalized coaching content based on actual feedback and relationship dynamics."""
    try:
        from config import Config
        client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        
        # Collect feedback content with context
        feedback_items = []
        for response in responses:
            question = Question.query.get(response.question_id)
            if response.discussion_summary:
                feedback_items.append(f"Question: {question.question_text}\nYour feedback: {response.discussion_summary}")
            elif response.rating_value:
                feedback_items.append(f"Question: {question.question_text}\nYour rating: {response.rating_value}/5")
            elif response.agreement_value:
                agreement_labels = {
                    'strongly_agree': 'Strongly Agree',
                    'agree': 'Agree', 
                    'disagree': 'Disagree',
                    'strongly_disagree': 'Strongly Disagree',
                    'na': 'N/A'
                }
                feedback_items.append(f"Question: {question.question_text}\nYour response: {agreement_labels.get(response.agreement_value, response.agreement_value)}")
        
        feedback_content = "\n\n".join(feedback_items)
        relationship_type = "supervisor" if feedback_request.template.is_supervisor_feedback else "peer/colleague"
        target_name = feedback_request.target_name
        safety_level = safety_analysis['safety_level']
        context = feedback_request.context if feedback_request.context and feedback_request.context.strip() else ""
        
        # Build comprehensive coaching prompt
        response = client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": f"""You are an expert executive coach specializing in difficult conversations and workplace feedback delivery. Generate a personalized coaching guide for someone who needs to deliver feedback they wrote to their {relationship_type}.

The coaching should be:
- Specific to the actual feedback content provided
- Mindful of the relationship dynamics and power structure
- Practical and actionable
- Psychologically safe given the assessed risk level: {safety_level}

Structure your response with these sections:
1. **Personalized Assessment** - Brief analysis of their specific situation
2. **Preparation Strategy** - Tailored preparation advice
3. **Opening Approach** - Specific opening script suggestions 
4. **Delivery Guidance** - How to share each piece of feedback
5. **Handling Reactions** - Anticipated responses and how to navigate them
6. **Closing & Next Steps** - How to end constructively

Write in second person ("you should...") as direct coaching advice. Be specific to their actual feedback content, not generic."""
                },
                {
                    "role": "user",
                    "content": f"""I need coaching on delivering feedback to {target_name}, who is my {relationship_type}. 

{f"Additional context about our relationship: {context}" if context else ""}

Here's the feedback I wrote:

{feedback_content}

Safety assessment: {safety_level} risk level
{"Specific concerns: " + ", ".join(safety_analysis.get('concerns', [])) if safety_analysis.get('concerns') else ""}

Please provide personalized coaching for delivering this specific feedback in this relationship context."""
                }
            ],
            max_tokens=1200,
            temperature=0.4
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error generating personalized coaching: {e}")
        # Fallback to basic guidance
        relationship_type = "supervisor" if feedback_request.template.is_supervisor_feedback else "colleague"
        return f"""# Personalized Coaching Guide

## Your Situation
You have feedback to deliver to {feedback_request.target_name}, your {relationship_type}. Based on your feedback content, approach this conversation thoughtfully.

## Preparation
- Choose a private, comfortable setting
- Plan for 20-30 minutes of conversation
- Review your specific feedback points beforehand
- Prepare to listen to their perspective

## Opening the Conversation
"Hi {feedback_request.target_name}, I'd like to share some observations about our working relationship. My goal is to improve how we collaborate together. Would you be open to hearing my perspective?"

## Delivery Approach
- Share your specific observations using "I" statements
- Focus on behaviors and impacts, not personality
- Ask for their perspective after each point
- Be prepared to listen and understand their viewpoint

## Next Steps
- Summarize any agreements or insights
- Identify specific actions you can both take
- Schedule follow-up if needed
- Thank them for their openness"""

def analyze_feedback_safety(responses, is_supervisor_feedback=False):
    """Analyze feedback content to assess psychological safety and relationship dynamics."""
    try:
        from config import Config
        client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        
        # Collect all feedback content
        feedback_content = []
        for response in responses:
            if response.discussion_summary:
                feedback_content.append(response.discussion_summary)
            elif response.rating_value and response.rating_value <= 2:
                feedback_content.append(f"Low rating ({response.rating_value}/5) given")
            elif response.agreement_value in ['disagree', 'strongly_disagree']:
                feedback_content.append(f"Disagreement expressed ({response.agreement_value})")
        
        if not feedback_content:
            return {
                'safety_level': 'high',
                'concerns': [],
                'suggestions': ['This appears to be positive feedback that should be comfortable to deliver directly.']
            }
        
        feedback_text = "\n".join(feedback_content)
        relationship_context = "supervisor/manager" if is_supervisor_feedback else "peer or colleague"
        
        response = client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": f"""You are an expert in workplace psychology and feedback delivery. Analyze this feedback content to assess how comfortable and safe it would be for the feedback giver to deliver this directly to their {relationship_context}.

Consider:
- Power dynamics and hierarchy
- Constructive vs critical tone
- Specific vs vague feedback
- Emotional safety concerns
- Potential for defensiveness

Respond with a JSON object containing:
- safety_level: "high" (comfortable to deliver), "medium" (some concerns), or "low" (significant concerns)
- concerns: array of specific concerns about direct delivery
- suggestions: array of specific recommendations for safe delivery"""
                },
                {
                    "role": "user",
                    "content": f"Analyze this feedback content for delivery to a {relationship_context}:\n\n{feedback_text}"
                }
            ],
            max_tokens=300,
            temperature=0.3
        )
        
        import json
        return json.loads(response.choices[0].message.content.strip())
        
    except Exception as e:
        print(f"Error analyzing feedback safety: {e}")
        # Conservative fallback
        return {
            'safety_level': 'medium',
            'concerns': ['Unable to assess feedback content automatically'],
            'suggestions': ['Consider having this conversation in a private, comfortable setting']
        }

def generate_feedback_summary(question_text, chat_history, is_supervisor_feedback=False):
    """Generate a professional, organized feedback summary from chat conversation using LLM."""
    return generate_feedback_summary_with_custom_prompt(question_text, chat_history, is_supervisor_feedback, "")

def generate_feedback_summary_with_edited_prompt(question_text, chat_history, edited_prompt):
    """Generate a professional, organized feedback summary using a user-edited prompt."""
    try:
        from config import Config
        client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        
        # Build the conversation context - focus on user responses
        user_responses = []
        full_conversation = []
        
        for msg in chat_history:
            role = "Assistant" if msg['role'] == 'assistant' else "User"
            full_conversation.append(f"{role}: {msg['content']}")
            
            # Collect user responses separately
            if msg['role'] == 'user':
                user_responses.append(msg['content'])
        
        # Use user responses as primary content, full conversation as context
        user_content = "\n".join(user_responses)
        conversation_text = "\n".join(full_conversation)
        
        # Use the edited prompt directly
        response = client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": edited_prompt
                },
                {
                    "role": "user", 
                    "content": f"""Please organize and clean up the feedback given about: "{question_text}"

The feedback giver's responses:
{user_content}

Full conversation context (for understanding):
{conversation_text}

Provide a well-organized, comprehensive feedback summary that preserves ALL the details and examples the user provided:"""
                }
            ],
            max_tokens=400,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error generating feedback summary with edited prompt: {e}")
        # Fallback to simple concatenation
        user_messages = [msg['content'] for msg in chat_history if msg['role'] == 'user']
        return ' '.join(user_messages) if user_messages else 'No response provided'

def generate_feedback_summary_with_custom_prompt(question_text, chat_history, is_supervisor_feedback=False, custom_prompt=""):
    """Generate a professional, organized feedback summary with optional custom instructions."""
    try:
        from config import Config
        client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        
        # Build the conversation context - focus on user responses
        user_responses = []
        full_conversation = []
        
        for msg in chat_history:
            role = "Assistant" if msg['role'] == 'assistant' else "User"
            full_conversation.append(f"{role}: {msg['content']}")
            
            # Collect user responses separately
            if msg['role'] == 'user':
                user_responses.append(msg['content'])
        
        # Use user responses as primary content, full conversation as context
        user_content = "\n".join(user_responses)
        conversation_text = "\n".join(full_conversation)
        
        # Build supervisor-specific guidance for organization
        supervisor_guidance = ""
        if is_supervisor_feedback:
            supervisor_guidance = """

IMPORTANT: This feedback is about a supervisor/manager. When organizing:
- Focus on leadership and management behaviors
- Emphasize examples of team support, communication, and decision-making
- Balance constructive feedback with positive observations
- Highlight specific impacts on team dynamics or professional development
- Use professional language appropriate for management feedback"""
        
        # Add custom prompt instructions if provided
        custom_instructions = ""
        if custom_prompt:
            custom_instructions = f"""

CUSTOM INSTRUCTIONS: {custom_prompt}

Follow these specific instructions in addition to the general guidelines above."""
        
        # Create organization prompt
        response = client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": f"""You are an expert at organizing and cleaning up feedback into professional, comprehensive statements. 

Your task is to organize and clean up what the feedback giver said while preserving ALL their content and meaning.

Guidelines:
- Focus ONLY on the user's actual responses and preserve ALL their examples and details
- Do NOT include or reference the interviewer's questions or prompts
- Clean up grammar, flow, and organization but preserve ALL substantive content
- Include ALL specific details, examples, and stories the user mentioned
- Organize the content logically but keep it comprehensive and detailed
- Write in third person as feedback about the person being reviewed
- This should be MORE verbose than the original, not less - organize and expand rather than summarize
- Aim for 3-6 sentences or more to capture all nuance and detail
- Base the organized feedback strictly on what the user said, including all their examples{supervisor_guidance}{custom_instructions}"""
                },
                {
                    "role": "user", 
                    "content": f"""Please organize and clean up the feedback given about: "{question_text}"

The feedback giver's responses:
{user_content}

Full conversation context (for understanding):
{conversation_text}

Provide a well-organized, comprehensive feedback summary that preserves ALL the details and examples the user provided:"""
                }
            ],
            max_tokens=400,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error generating feedback summary: {e}")
        # Fallback to simple concatenation
        user_messages = [msg['content'] for msg in chat_history if msg['role'] == 'user']
        return ' '.join(user_messages) if user_messages else 'No response provided'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    migrate = Migrate(app, db)
    init_auth(app)
    
    # Add custom template filters
    @app.template_filter('from_json')
    def from_json_filter(value):
        """Parse JSON string to Python object."""
        if not value:
            return []
        try:
            return json.loads(value)
        except:
            return []
    
    # Auto-login dev user on every request in dev mode
    @app.before_request
    def before_request():
        if app.config['LOCAL_DEV_MODE']:
            auto_login_dev_user()
    
    # Register routes
    register_routes(app)
    
    return app

def register_routes(app):
    """Register all routes with the Flask app."""
    
    @app.route('/')
    def index():
        user = auto_login_dev_user()
        return render_template('index.html', user=user)
    
    @app.route('/login')
    def auth_login():
        if app.config['LOCAL_DEV_MODE']:
            user = get_or_create_dev_user()
            if user:
                login_user(user)
                user.last_login = datetime.utcnow()
                db.session.commit()
                flash(f'Logged in as {user.name} (dev mode)', 'success')
                return redirect(url_for('dashboard'))
        
        # In production, this would handle Google OAuth
        flash('Authentication not configured for production mode.', 'error')
        return render_template('login.html')
    
    @app.route('/logout')
    @login_required
    def auth_logout():
        logout_user()
        flash('You have been logged out.', 'success')
        return redirect(url_for('index'))

    @app.route('/templates')
    @login_required
    def list_templates():
        """List all feedback templates."""
        user = ensure_authenticated()
        if not user:
            return redirect(url_for('auth_login'))
        
        templates = FeedbackTemplate.query.order_by(FeedbackTemplate.created_at.desc()).all()
        return render_template('templates/list.html', templates=templates, user=user)

    @app.route('/templates/create', methods=['GET', 'POST'])
    @require_permission('create_templates')
    def create_template():
        """Create a new feedback template."""
        if request.method == 'POST':
            name = request.form['name']
            description = request.form.get('description', '')
            intro_text = request.form.get('intro_text', '')
            is_supervisor_feedback = 'is_supervisor_feedback' in request.form
            
            # Create template
            template = FeedbackTemplate(
                name=name, 
                description=description,
                intro_text=intro_text,
                is_supervisor_feedback=is_supervisor_feedback,
                created_by_id=current_user.id
            )
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
    @login_required
    def create_request():
        user = ensure_authenticated()
        if not user:
            return redirect(url_for('auth_login'))
            
        if request.method == 'POST':
            target_name = request.form['target_name']
            target_email = request.form['target_email']
            assigned_to_email = request.form['assigned_to_email']
            context = request.form.get('context', '')
            template_id = request.form['template_id']
            reviewer_id = request.form.get('reviewer_id') or None
            
            # Check permissions for creating requests
            # Users can always create requests for themselves as the assignee
            # Only users with permission can create requests for others
            if assigned_to_email != user.email and not user.can_create_requests_for_others and not user.is_admin:
                flash('You do not have permission to create feedback requests for others.', 'error')
                return redirect(url_for('create_request'))
            
            # Find existing users by email to link accounts if they exist
            target_user = User.query.filter_by(email=target_email).first()
            assigned_user = User.query.filter_by(email=assigned_to_email).first()
            
            # Create feedback request with email-first approach
            feedback_request = FeedbackRequest(
                target_email=target_email,
                target_name=target_name,
                target_user_id=target_user.id if target_user else None,
                assigned_to_email=assigned_to_email,
                assigned_to_user_id=assigned_user.id if assigned_user else None,
                context=context,
                template_id=template_id,
                created_by_id=user.id,
                reviewer_id=reviewer_id,
                # Legacy compatibility
                assigned_to_id=assigned_user.id if assigned_user else None
            )
            db.session.add(feedback_request)
            db.session.commit()
            
            flash('Feedback request created successfully!')
            return redirect(url_for('share_link', request_id=feedback_request.id))
        
        # Get available templates and users
        templates = FeedbackTemplate.query.order_by(FeedbackTemplate.name).all()
        users = get_users_for_assignment() if user.can_create_requests_for_others or user.is_admin else [user]
        return render_template('create.html', templates=templates, users=users, current_user=user)

    @app.route('/share/<request_id>')
    def share_link(request_id):
        feedback_request = FeedbackRequest.query.get_or_404(request_id)
        return render_template('share.html', feedback_request=feedback_request)

    @app.route('/survey/<request_id>')
    @login_required
    def survey(request_id):
        user = ensure_authenticated()
        if not user:
            return redirect(url_for('auth_login'))
            
        feedback_request = FeedbackRequest.query.get_or_404(request_id)
        
        # Check if user can complete this request
        if not can_complete_request(feedback_request, user):
            flash('You are not assigned to complete this feedback request.', 'error')
            return redirect(url_for('dashboard'))
        
        questions = Question.query.filter_by(template_id=feedback_request.template_id).order_by(Question.order_index).all()
        return render_template('survey.html', feedback_request=feedback_request, questions=questions, user=user)

    @app.route('/api/chat/<question_id>', methods=['POST'])
    def chat_response(question_id):
        data = request.get_json()
        user_message = data.get('message', '').strip()
        chat_history = data.get('chat_history', [])
        feedback_request_id = data.get('feedback_request_id')
        
        # Get the original question and template to provide context
        question = Question.query.get_or_404(question_id)
        template = FeedbackTemplate.query.get_or_404(question.template_id)
        
        # Get feedback request for context
        feedback_request = FeedbackRequest.query.get_or_404(feedback_request_id) if feedback_request_id else None
        
        try:
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=app.config['OPENAI_API_KEY'])
            
            # Build context from all previous questions and responses
            context_info = ""
            if feedback_request_id:
                # Get all questions for this feedback request in order
                all_questions = Question.query.filter_by(template_id=question.template_id).order_by(Question.order_index).all()
                
                prior_context = []
                current_question_reached = False
                
                for q in all_questions:
                    if q.id == question_id:
                        current_question_reached = True
                        break
                    
                    # Look for existing responses to this question
                    existing_response = Response.query.filter_by(
                        feedback_request_id=feedback_request_id,
                        question_id=q.id,
                        is_draft=True
                    ).first()
                    
                    if existing_response:
                        if q.question_type == 'rating' and existing_response.rating_value is not None:
                            prior_context.append(f"Q: {q.question_text}\nA: {existing_response.rating_value}/5")
                        elif q.question_type == 'discussion' and existing_response.discussion_summary:
                            prior_context.append(f"Q: {q.question_text}\nA: {existing_response.discussion_summary}")
                
                if prior_context:
                    context_info = f"\n\nPrevious questions and responses in this feedback session:\n" + "\n\n".join(prior_context) + "\n\nUse this context to ask more relevant and connected follow-up questions."
            
            # Build supervisor-specific guidance
            supervisor_guidance = ""
            if template.is_supervisor_feedback:
                supervisor_guidance = """

IMPORTANT: This feedback is about someone's supervisor. Keep in mind:
- Focus on management and leadership behaviors
- Ask about communication style, decision-making, team support
- Encourage specific examples of how they handle challenges or conflicts
- Be particularly thoughtful about constructive criticism (balance with positive aspects)
- Consider questions about professional development support, delegation, and team dynamics"""

            # Build relationship context guidance
            relationship_context = ""
            if feedback_request and feedback_request.context and feedback_request.context.strip():
                relationship_context = f"""

RELATIONSHIP CONTEXT: {feedback_request.context.strip()}

This describes the relationship between the feedback giver and {feedback_request.target_name}. Use this context to ask more relevant and specific follow-up questions. Tailor your questions based on this relationship dynamic and situation."""

            # Build conversation history for the LLM
            messages = [
                {
                    "role": "system",
                    "content": f"""You are a skilled feedback interviewer helping someone provide detailed, constructive feedback. Your goal is to help them give comprehensive and thoughtful responses about: "{question.question_text}"

Guidelines:
- Ask ONE focused follow-up question at a time to encourage depth and specificity
- Help them provide concrete examples and details
- Guide them toward constructive, actionable feedback
- Keep your responses brief, conversational and supportive
- When they've provided sufficient detail (usually after 2-3 exchanges), acknowledge their response and ask if there's anything else they'd like to add
- If they indicate they're done (saying things like "done", "nothing else", "that's all"), respond with "Thank you for that detailed feedback!" to signal completion
- Reference previous answers when relevant to create a cohesive feedback experience

IMPORTANT: Always respond with just ONE question or acknowledgment. Keep responses concise and focused.{supervisor_guidance}{relationship_context}{context_info}"""
                }
            ]
            
            # Add chat history
            for msg in chat_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Add current user message
            messages.append({
                "role": "user", 
                "content": user_message
            })
            
            # Call OpenAI API
            response = client.chat.completions.create(
                model=app.config['OPENAI_MODEL'],
                messages=messages,
                max_tokens=100,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Check if this should be the final message
            is_final = (
                "thank you for that detailed feedback" in ai_response.lower() or
                "done" in user_message.lower() or 
                "nothing else" in user_message.lower() or
                "that's all" in user_message.lower()
            )
            
            return jsonify({
                'response': ai_response,
                'is_final': is_final
            })
            
        except Exception as e:
            # Fallback to simple responses if OpenAI fails
            print(f"OpenAI API error: {e}")
            
            follow_up_questions = [
                "Can you share a specific example?",
                "How has this impacted the team or project?", 
                "What made this particularly effective or challenging?",
                "Is there anything else you'd like to add?"
            ]
            
            # Simple fallback logic
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
                elif response_data['type'] == 'agreement':
                    response.agreement_value = None if response_data['value'] == '' else (
                        None if response_data['value'] == 'na' else response_data['value']
                    )
                else:  # discussion
                    response.chat_history = json.dumps(response_data.get('chat_history', []))
                    # Generate AI-powered summary from full conversation
                    chat_history = response_data.get('chat_history', [])
                    if chat_history:
                        # Get the question text and template for context
                        question_obj = Question.query.get(question_id)
                        template_obj = FeedbackTemplate.query.get(question_obj.template_id)
                        response.discussion_summary = generate_feedback_summary(
                            question_obj.question_text, 
                            chat_history,
                            template_obj.is_supervisor_feedback
                        )
                    else:
                        response.discussion_summary = 'No response provided'
                
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
                'agreement_value': r.agreement_value,
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
    @login_required
    def dashboard():
        """Dashboard to view feedback requests relevant to the current user."""
        user = ensure_authenticated()
        if not user:
            return redirect(url_for('auth_login'))
        
        # Organize requests by user role (email-first approach)
        if user.is_admin:
            # Admins see all requests
            all_requests = FeedbackRequest.query.order_by(FeedbackRequest.created_at.desc()).all()
            requests_by_role = {
                'created_by_me': all_requests,
                'assigned_to_me': [],
                'about_me': []
            }
        else:
            # Separate requests by the user's role
            # 1. Requests I created (as manager/HR)
            created_by_me = FeedbackRequest.query.filter(
                FeedbackRequest.created_by_id == user.id
            ).order_by(FeedbackRequest.created_at.desc()).all()
            
            # 2. Requests assigned to me (feedback I need to give)
            assigned_to_me = FeedbackRequest.query.filter(
                (FeedbackRequest.assigned_to_email == user.email) |
                # Legacy fallback
                (FeedbackRequest.assigned_to_id == user.id)
            ).filter(
                FeedbackRequest.created_by_id != user.id  # Exclude my own requests
            ).order_by(FeedbackRequest.created_at.desc()).all()
            
            # 3. Feedback about me (I'm the target)
            about_me = FeedbackRequest.query.filter(
                FeedbackRequest.target_email == user.email
            ).filter(
                FeedbackRequest.created_by_id != user.id  # Exclude my own requests
            ).order_by(FeedbackRequest.created_at.desc()).all()
            
            requests_by_role = {
                'created_by_me': created_by_me,
                'assigned_to_me': assigned_to_me,
                'about_me': about_me
            }
        
        # Add submission counts for each role
        role_data = {}
        for role, requests in requests_by_role.items():
            requests_with_counts = []
            for request in requests:
                submitted_count = Response.query.filter_by(
                    feedback_request_id=request.id, 
                    is_draft=False
                ).count()
                requests_with_counts.append({
                    'request': request,
                    'submitted_count': submitted_count
                })
            role_data[role] = requests_with_counts
        
        return render_template('dashboard.html', role_data=role_data, user=user)

    @app.route('/single-player', methods=['GET', 'POST'])
    @login_required
    def single_player_mode():
        """Single-player mode for completing external feedback forms with AI assistance."""
        user = ensure_authenticated()
        if not user:
            return redirect(url_for('auth_login'))
        
        if request.method == 'POST':
            # Handle form submission to start AI-assisted session
            form_text = request.form.get('form_text', '').strip()
            relationship_context = request.form.get('relationship_context', '').strip()
            uploaded_file = request.files.get('form_screenshot')
            
            # Store uploaded screenshot for later analysis
            screenshot_data = None
            screenshot_filename = None
            if uploaded_file and uploaded_file.filename:
                try:
                    # Store the image data temporarily (not in session due to size limits)
                    screenshot_data = uploaded_file.read()
                    screenshot_filename = uploaded_file.filename
                    print(f"Screenshot uploaded: {screenshot_filename}, size: {len(screenshot_data)} bytes")
                except Exception as e:
                    print(f"Error reading screenshot: {e}")
                    screenshot_data = None
            
            if not form_text and not uploaded_file:
                flash('Please provide either the feedback form text or upload a screenshot.', 'error')
                return redirect(url_for('single_player_mode'))
            
            if not relationship_context:
                flash('Please describe your working relationship with the person.', 'error')
                return redirect(url_for('single_player_mode'))
            
            # Process the form data immediately and redirect to chat with initial guidance
            try:
                client = openai.OpenAI(api_key=app.config['OPENAI_API_KEY'])
                
                # Generate initial guidance immediately
                initial_guidance = generate_initial_feedback_guidance(
                    client, relationship_context, form_text, screenshot_data
                )
                
                # Store minimal context in session (just for this chat session)
                session['chat_context'] = {
                    'relationship_context': relationship_context,
                    'form_text': form_text,
                    'has_screenshot': bool(screenshot_data),
                    'initial_guidance': initial_guidance
                }
                
                return redirect(url_for('single_player_chat'))
                
            except Exception as e:
                print(f"Error generating feedback guidance: {e}")
                flash('Error processing your feedback form. Please try again.', 'error')
                return redirect(url_for('single_player_mode'))
        
        # Clear any existing chat context for fresh start
        session.pop('chat_context', None)
        
        return render_template('single_player.html', user=user)




    def analyze_screenshot_with_vision(image_data, filename):
        """Analyze screenshot using OpenAI Vision API to extract feedback form text."""
        try:
            # Encode image to base64
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Initialize OpenAI client
            client = openai.OpenAI(api_key=app.config['OPENAI_API_KEY'])
            
            response = client.chat.completions.create(
                model="gpt-4o",  # Use GPT-4o which has vision capabilities
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Please extract all the text from this feedback form image. Focus on:
1. Feedback questions (usually numbered or bulleted)
2. Form labels and instructions
3. Any other relevant text

Please provide the extracted text in a clear, structured format that preserves the questions and their numbering/organization. If there are feedback questions, list them clearly."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            extracted_text = response.choices[0].message.content.strip()
            return extracted_text
            
        except Exception as e:
            print(f"Error analyzing screenshot with vision: {e}")
            return f"[Screenshot uploaded: {filename} - Could not extract text from image]"

    def analyze_screenshot_immediately(client, image_data, relationship_context, form_text):
        """Immediately analyze screenshot and extract comprehensive form information."""
        try:
            # Encode image to base64
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            analysis_prompt = f"""Analyze this feedback form image comprehensively.

CONTEXT:
- Working relationship: {relationship_context}
- Additional form text: {form_text if form_text else 'None provided'}

YOUR TASK:
1. Extract ALL text visible in the image
2. Identify specific feedback questions
3. Note any form structure, labels, or instructions
4. Provide a clear summary of what feedback is being requested

Please provide a comprehensive analysis that includes:
- The exact questions visible
- Any form instructions or context
- Overall structure and purpose of the form

Be thorough and specific about what you can see in the image."""

            response = client.chat.completions.create(
                model="gpt-4o",  # Use GPT-4o which has vision capabilities
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": analysis_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            analysis_result = response.choices[0].message.content.strip()
            print(f"Screenshot analysis successful: {len(analysis_result)} chars")
            return analysis_result
            
        except Exception as e:
            print(f"Error in immediate screenshot analysis: {e}")
            return f"[Screenshot analysis failed: {str(e)}]"

    @app.route('/single-player/chat')
    @login_required
    def single_player_chat():
        """Chat interface for single-player feedback assistance."""
        user = ensure_authenticated()
        if not user:
            return redirect(url_for('auth_login'))
        
        # Check if we have chat context from form submission
        chat_context = session.get('chat_context')
        if not chat_context:
            flash('Please start a new single-player session.', 'info')
            return redirect(url_for('single_player_mode'))
        
        return render_template('single_player_chat.html', 
                             relationship_context=chat_context['relationship_context'],
                             form_text=chat_context.get('form_text'),
                             has_screenshot=chat_context.get('has_screenshot', False),
                             initial_guidance=chat_context['initial_guidance'],
                             user=user)

    def parse_feedback_questions(client, form_content):
        """Parse feedback form content to extract individual questions."""
        # Check if content is insufficient
        if not form_content or len(form_content.strip()) < 20:
            return []  # Return empty list to indicate no questions could be parsed
        
        # Check if this is a failed screenshot processing message
        if form_content.startswith('[Screenshot uploaded:') and 'Could not' in form_content:
            return []  # Return empty list to indicate no questions could be parsed
        
        try:
            response = client.chat.completions.create(
                model=app.config['OPENAI_MODEL'],
                messages=[{
                    "role": "system",
                    "content": """You are analyzing a feedback form to extract individual questions. 
                    
                    Parse the form content and return a JSON array of the individual feedback questions.
                    Each question should be clean, complete, and specific.
                    
                    Example:
                    Input: "1. How does this person communicate? 2. What are their strengths? 3. Areas for improvement?"
                    Output: ["How does this person communicate?", "What are their strengths?", "What areas would you recommend for improvement?"]
                    
                    If the content doesn't contain clear feedback questions, return an empty array: []
                    
                    Return ONLY the JSON array, no other text."""
                }, {
                    "role": "user", 
                    "content": f"Extract the feedback questions from this form:\n\n{form_content}"
                }],
                max_tokens=500,
                temperature=0.3
            )
            
            result = response.choices[0].message.content.strip()
            # Try to parse as JSON, fallback to simple splitting if it fails
            try:
                import json
                questions = json.loads(result)
                if isinstance(questions, list) and len(questions) > 0:
                    return questions
                else:
                    return []  # Empty list if no valid questions found
            except:
                # Fallback: simple parsing
                lines = form_content.split('\n')
                questions = []
                for line in lines:
                    line = line.strip()
                    if line and ('?' in line or any(line.startswith(str(i)) for i in range(1, 20))):
                        # Clean up numbering and formatting
                        cleaned = line
                        # Remove leading numbers and dots
                        import re
                        cleaned = re.sub(r'^\d+[\.\)]\s*', '', cleaned)
                        if cleaned and len(cleaned) > 10:  # Ensure it's a substantial question
                            questions.append(cleaned)
                return questions
                
        except Exception as e:
            print(f"Error parsing questions: {e}")
            return []

    def parse_feedback_questions_comprehensive(client, form_text, screenshot_data, relationship_context):
        """Parse feedback form content including images to extract individual questions."""
        try:
            # Build message content for comprehensive analysis
            message_content = []
            
            analysis_prompt = f"""Analyze this feedback form setup and extract the individual questions.

CONTEXT:
- Working relationship: {relationship_context}
- Form text provided: {form_text if form_text else 'None'}

YOUR TASK:
1. Look at all available information (text and image if provided)
2. Extract the individual feedback questions
3. Return a clean JSON array of the questions
4. Each question should be complete and specific

REQUIREMENTS:
- Return ONLY a valid JSON array like: ["Question 1", "Question 2", "Question 3"]
- If no clear questions are found, return an empty array: []
- Clean up any numbering or formatting from the questions
- Make sure each question is complete and understandable

Example output: ["How effectively does this person communicate?", "What are their key strengths?", "What areas would you recommend for development?"]"""
            
            message_content.append({
                "type": "text",
                "text": analysis_prompt
            })
            
            # Add screenshot if available
            if screenshot_data:
                message_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{screenshot_data}",
                        "detail": "high"
                    }
                })
            
            response = client.chat.completions.create(
                model="gpt-4o",  # Use vision model
                messages=[{
                    "role": "user",
                    "content": message_content
                }],
                max_tokens=500,
                temperature=0.3
            )
            
            result = response.choices[0].message.content.strip()
            
            # Try to parse as JSON
            try:
                import json
                questions = json.loads(result)
                return questions if isinstance(questions, list) else []
            except:
                # Fallback to empty array if parsing fails
                print(f"Could not parse questions JSON: {result}")
                return []
                
        except Exception as e:
            print(f"Error in comprehensive question parsing: {e}")
            return []

    def handle_initial_summary(client, sp_session):
        """Generate initial summary message explaining what we're working on."""
        try:
            relationship_context = sp_session['relationship_context']
            form_text = sp_session.get('form_text', '')
            screenshot_analysis = sp_session.get('screenshot_analysis', '')
            screenshot_filename = sp_session.get('screenshot_filename')
            
            # Combine all available form content
            all_form_content = []
            if form_text:
                all_form_content.append(f"Form text: {form_text}")
            if screenshot_analysis:
                all_form_content.append(f"Screenshot analysis: {screenshot_analysis}")
            
            form_content_summary = "\n".join(all_form_content) if all_form_content else "No form content available"
            
            summary_prompt = f"""Create a welcoming summary message for a feedback assistance session.

WORKING RELATIONSHIP: {relationship_context}
FORM CONTENT: {form_content_summary}

YOUR TASK:
1. Identify who is giving feedback and who it's about (parse the relationship carefully)
2. Understand what collaboration areas are relevant
3. Analyze the form content to understand what questions need to be answered
4. Create a friendly, clear opening message that:
   - Acknowledges what we're doing (feedback assistance)
   - Names who the feedback is about
   - References their working relationship/collaboration areas
   - Acknowledges the specific form questions you can identify
   - Explains you'll help them think through examples and craft responses
   - Does NOT suggest what to write, just sets up the process

Keep it conversational and helpful. Focus on understanding and setup, not prescribing content."""

            response = client.chat.completions.create(
                model=app.config['OPENAI_MODEL'],
                messages=[{
                    "role": "user",
                    "content": summary_prompt
                }],
                max_tokens=400,
                temperature=0.7
            )
            
            summary_response = response.choices[0].message.content.strip()
            
            return jsonify({
                'response': summary_response,
                'initial_summary': True
            })
            
        except Exception as e:
            print(f"Error generating initial summary: {e}")
            return jsonify({
                'response': "Hi! I'm here to help you craft thoughtful feedback for your external form. Let me know what feedback questions you need help with, and I'll guide you through creating specific, actionable responses.",
                'error': True
            })

    def handle_generate_final_output(client, sp_session):
        """Generate final polished responses for all questions."""
        try:
            parsed_questions = sp_session.get('parsed_questions', [])
            completed_responses = sp_session.get('completed_responses', {})
            chat_history = sp_session.get('chat_history', [])
            relationship_context = sp_session['relationship_context']
            
            # Build conversation summary
            conversation_summary = "\n".join([
                f"{msg['role'].upper()}: {msg['content']}" 
                for msg in chat_history[-20:]  # Last 20 messages
            ])
            
            system_prompt = f"""Based on our conversation, generate polished, professional feedback responses for each question.

CONTEXT:
- Working relationship: {relationship_context}
- Questions to answer: {parsed_questions}
- Our conversation: {conversation_summary}

Generate a clean, professional response for each question. Each response should be:
- Specific and actionable
- Professional in tone
- Based on the examples and insights from our conversation
- 2-4 sentences per response
- Balanced between strengths and areas for improvement

Format as markdown with each question as a heading and the response below it."""

            response = client.chat.completions.create(
                model=app.config['OPENAI_MODEL'],
                messages=[{
                    "role": "system",
                    "content": system_prompt
                }, {
                    "role": "user",
                    "content": "Please generate the final feedback responses based on our conversation."
                }],
                max_tokens=800,
                temperature=0.7
            )
            
            final_output = response.choices[0].message.content.strip()
            
            return jsonify({
                'response': final_output,
                'final_output': True
            })
            
        except Exception as e:
            print(f"Error generating final output: {e}")
            return jsonify({
                'response': "I'm having trouble generating the final output. Could you try again?",
                'error': True
            })

    @app.route('/api/single-player-chat', methods=['POST'])
    @login_required
    def single_player_chat_api():
        """API endpoint for single-player chat interactions."""
        user = ensure_authenticated()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json()
        user_message = data.get('message', '').strip()
        action = data.get('action')  # 'start' for initial message, 'chat' for follow-up
        chat_history = data.get('chat_history', [])  # Chat history from frontend
        
        # Get minimal context from session
        chat_context = session.get('chat_context')
        if not chat_context:
            return jsonify({'error': 'No active session'}), 400
        
        if action != 'start' and not user_message:
            return jsonify({'error': 'Message required'}), 400
        
        try:
            client = openai.OpenAI(api_key=app.config['OPENAI_API_KEY'])
            
            if action == 'start':
                # Return the pre-generated initial guidance
                response_text = chat_context['initial_guidance']
            else:
                # Handle follow-up questions with context
                response_text = handle_feedback_followup(
                    client, 
                    chat_context['relationship_context'], 
                    chat_context.get('form_text'), 
                    user_message, 
                    chat_history
                )
            
            return jsonify({
                'response': response_text
            })
            
        except Exception as e:
            print(f"Single-player chat error: {e}")
            return jsonify({
                'response': "I'm having trouble connecting to the AI service. Could you try rephrasing your message?",
                'error': True
            })
    
    def generate_initial_feedback_guidance(client, relationship_context, form_text, screenshot_data):
        """Generate initial focused guidance for the feedback form."""
        
        # Analyze form content (screenshot or text)
        if screenshot_data:
            # Use Vision API to read screenshot
            try:
                import base64
                base64_image = base64.b64encode(screenshot_data).decode('utf-8')
                
                vision_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract the text content from this feedback form screenshot. Focus on identifying the specific questions that need to be answered."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }],
                    max_tokens=500
                )
                
                form_content = vision_response.choices[0].message.content
            except Exception as e:
                print(f"Vision API error: {e}")
                form_content = form_text or "Unable to read screenshot"
        else:
            form_content = form_text or "No form content provided"
        
        # Generate focused guidance prompt
        guidance_prompt = f"""You are a feedback expert helping someone complete an external feedback form. Your role is to probe deeply into their working relationship to gather specific, actionable feedback.

CONTEXT:
- Working relationship: {relationship_context}
- Form content: {form_content}

YOUR INITIAL MESSAGE should:
1. Briefly acknowledge their working relationship
2. Identify and recap the key questions/areas from their feedback form (if visible)
3. Ask them to start with a broad overview - what's their general impression?
4. Mention that you'll ask follow-up questions to help them think through specific examples

EXAMPLE STRUCTURE:
"I can see you're providing feedback about [person] who [relationship]. Looking at your form, it seems like they're asking about [key areas like communication, leadership, collaboration, etc.].

To get started, can you give me a broad overview? What's your general impression of working with [person] - what stands out to you as their main strengths and any areas where they could improve?

I'll ask follow-up questions to help you think through specific examples and situations that support your observations."

TONE: Curious interviewer who only asks questions. Never write feedback content for them."""

        response = client.chat.completions.create(
            model=app.config['OPENAI_MODEL'],
            messages=[{"role": "user", "content": guidance_prompt}],
            max_tokens=300,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    def handle_feedback_followup(client, relationship_context, form_text, user_message, chat_history):
        """Handle follow-up questions in the feedback chat."""
        
        system_prompt = f"""You are a skilled interviewer helping someone think through their feedback for an external form. You ONLY ask questions - you never write feedback content for them.

CONTEXT:
- Working relationship: {relationship_context}  
- Form content: {form_text or 'See previous messages for form details'}

YOUR ROLE - QUESTION-ASKING INTERVIEWER ONLY:

IF they're giving broad/general feedback:
- Acknowledge what they shared
- Pick one area and ask for a specific example
- "Can you give me a specific example of when they did that?"

IF they're giving specific examples:
- Ask follow-up questions to get more details
- "What exactly did they say/do in that moment?" 
- "How did that impact you/the project/the team?"
- "What would have been more helpful in that situation?"

PROBING QUESTIONS TO USE:
- "Tell me about a specific time when..."
- "What exactly happened in that situation?"
- "How did that make you feel/impact the work?"
- "What would you have wanted them to do differently?"
- "Can you think of another example of that behavior?"
- "Walk me through exactly what happened..."

CRITICAL: You are ONLY an interviewer. Never write feedback content, suggestions, or responses for them. Only ask questions to help them think deeper.

Keep responses very short (1-2 sentences max) with a focused follow-up question."""

        # Check if user is indicating they're done and want final feedback
        done_indicators = ['done', 'finished', 'complete', 'ready', 'organize', 'clean up', 'final', 'submit']
        if any(indicator in user_message.lower() for indicator in done_indicators):
            return generate_final_organized_feedback(client, relationship_context, form_text, chat_history)
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add recent chat history (last 6 messages to keep context manageable)
        for msg in chat_history[-6:]:
            messages.append(msg)
        
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        response = client.chat.completions.create(
            model=app.config['OPENAI_MODEL'],
            messages=messages,
            max_tokens=200,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    def generate_final_organized_feedback(client, relationship_context, form_text, chat_history):
        """Generate final organized feedback based on the conversation."""
        
        # Extract all the specific examples and feedback from the conversation
        conversation_content = "\n".join([
            f"{msg['role']}: {msg['content']}" for msg in chat_history
        ])
        
        organization_prompt = f"""Based on this conversation, organize the feedback they provided into a clean format for their external feedback form. Use ONLY their words and examples - don't add anything new.

CONTEXT:
- Working relationship: {relationship_context}
- Form content: {form_text or 'General feedback form'}
- Conversation: {conversation_content}

YOUR TASK:
1. Extract all the specific examples, behaviors, and feedback THEY mentioned
2. Organize them by theme/question area based on the form
3. Present their content in a clean format using:
   - Only their actual words and examples
   - Their original phrasing and tone
   - The specific situations they described
   - NO additions or embellishments from you

FORMAT your response as:
## Your Feedback (Organized)

**[Question/Area 1 from their form]:**
[Their exact feedback and examples for this area, organized cleanly]

**[Question/Area 2 from their form]:**
[Their exact feedback and examples for this area, organized cleanly]

[Continue for each area they covered]

---
*This is your feedback organized by question area. Copy and paste into your external form as needed.*

CRITICAL: Use only what they said. Don't write new content, don't improve their language, don't add suggestions. Just organize their actual words."""

        response = client.chat.completions.create(
            model=app.config['OPENAI_MODEL'],
            messages=[{"role": "user", "content": organization_prompt}],
            max_tokens=800,
            temperature=0.1
        )
        
        return response.choices[0].message.content.strip()


    @app.route('/api/email-suggestions')
    @login_required
    def email_suggestions():
        """Provide email suggestions for autocomplete."""
        query = request.args.get('q', '').lower()
        
        if not query or len(query) < 2:
            return jsonify([])
        
        # Get emails from users
        user_emails = []
        users = User.query.filter(User.email.ilike(f'%{query}%')).limit(10).all()
        for user in users:
            user_emails.append({
                'email': user.email,
                'name': user.name,
                'type': 'user'
            })
        
        # Get emails from feedback requests (targets and assignees)
        target_emails = db.session.query(FeedbackRequest.target_email, FeedbackRequest.target_name)\
            .filter(FeedbackRequest.target_email.ilike(f'%{query}%'))\
            .distinct().limit(5).all()
        
        assigned_emails = db.session.query(FeedbackRequest.assigned_to_email)\
            .filter(FeedbackRequest.assigned_to_email.ilike(f'%{query}%'))\
            .distinct().limit(5).all()
        
        # Add target emails
        for target_email, target_name in target_emails:
            if not any(item['email'] == target_email for item in user_emails):
                user_emails.append({
                    'email': target_email,
                    'name': target_name,
                    'type': 'target'
                })
        
        # Add assigned emails
        for (assigned_email,) in assigned_emails:
            if not any(item['email'] == assigned_email for item in user_emails):
                user_emails.append({
                    'email': assigned_email,
                    'name': assigned_email,
                    'type': 'assignee'
                })
        
        # Sort by relevance (exact match first, then starts with, then contains)
        def sort_key(item):
            email = item['email'].lower()
            if email == query:
                return (0, email)
            elif email.startswith(query):
                return (1, email)
            else:
                return (2, email)
        
        user_emails.sort(key=sort_key)
        return jsonify(user_emails[:10])

    @app.route('/aggregate-report')
    @login_required
    def aggregate_report():
        """View aggregate feedback reports for a person across multiple requests."""
        user = ensure_authenticated()
        if not user:
            return redirect(url_for('auth_login'))
        
        target_email = request.args.get('target_email', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        # Get available target people (those who have received feedback)
        if user.is_admin:
            # Admins can see aggregates for anyone
            available_targets = db.session.query(FeedbackRequest.target_email, FeedbackRequest.target_name)\
                .distinct().order_by(FeedbackRequest.target_name).all()
        else:
            # Regular users can see:
            # 1. People they created requests for (as manager)
            # 2. Themselves (as target)
            available_targets = db.session.query(FeedbackRequest.target_email, FeedbackRequest.target_name)\
                .filter(
                    (FeedbackRequest.created_by_id == user.id) |
                    (FeedbackRequest.target_email == user.email)
                ).distinct().order_by(FeedbackRequest.target_name).all()
        
        feedback_data = []
        if target_email:
            # Build date filter
            date_filter = []
            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    date_filter.append(FeedbackRequest.created_at >= start_dt)
                except ValueError:
                    pass
            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                    date_filter.append(FeedbackRequest.created_at <= end_dt)
                except ValueError:
                    pass
            
            # Get all feedback requests for this target email
            query = FeedbackRequest.query.filter(FeedbackRequest.target_email == target_email)
            if date_filter:
                query = query.filter(*date_filter)
            
            feedback_requests = query.order_by(FeedbackRequest.created_at.desc()).all()
            
            # Get responses for each request
            for req in feedback_requests:
                responses = Response.query.filter_by(
                    feedback_request_id=req.id, 
                    is_draft=False
                ).all()
                
                if responses:  # Only include requests with actual responses
                    feedback_data.append({
                        'request': req,
                        'responses': responses,
                        'response_count': len(responses)
                    })
        
        return render_template('aggregate_report.html', 
                             target_email=target_email,
                             start_date=start_date,
                             end_date=end_date,
                             available_targets=available_targets,
                             feedback_data=feedback_data,
                             user=user)

    @app.route('/report/<request_id>')
    @login_required
    def view_report(request_id):
        user = ensure_authenticated()
        if not user:
            return redirect(url_for('auth_login'))
            
        feedback_request = FeedbackRequest.query.get_or_404(request_id)
        
        # Check if user can access this request
        if not can_access_request(feedback_request, user):
            flash('You do not have permission to view this report.', 'error')
            return redirect(url_for('dashboard'))
        
        responses = Response.query.filter_by(feedback_request_id=request_id, is_draft=False).all()
        return render_template('report.html', feedback_request=feedback_request, responses=responses, user=user)

    @app.route('/coaching/<request_id>')
    @login_required
    def coaching_guide(request_id):
        user = ensure_authenticated()
        if not user:
            return redirect(url_for('auth_login'))
            
        feedback_request = FeedbackRequest.query.get_or_404(request_id)
        
        # Check if user can access this request
        if not can_access_request(feedback_request, user):
            flash('You do not have permission to view this coaching guide.', 'error')
            return redirect(url_for('dashboard'))
        
        responses = Response.query.filter_by(feedback_request_id=request_id, is_draft=False).all()
        questions = Question.query.filter_by(template_id=feedback_request.template_id).order_by(Question.order_index).all()
        
        # Analyze feedback safety and relationship dynamics
        safety_analysis = analyze_feedback_safety(responses, feedback_request.template.is_supervisor_feedback)
        
        # Generate personalized coaching content
        coaching_content = generate_personalized_coaching(feedback_request, responses, safety_analysis)
        
        return render_template('coaching.html', 
                             feedback_request=feedback_request, 
                             responses=responses, 
                             questions=questions,
                             safety_analysis=safety_analysis,
                             coaching_content=coaching_content,
                             user=user)

    @app.route('/api/regenerate-summary/<response_id>', methods=['POST'])
    @login_required
    def regenerate_summary(response_id):
        user = ensure_authenticated()
        if not user:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
        response = Response.query.get_or_404(response_id)
        feedback_request = FeedbackRequest.query.get_or_404(response.feedback_request_id)
        
        # Check if user can access this request
        if not can_access_request(feedback_request, user):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403
        
        data = request.get_json()
        custom_prompt = data.get('custom_prompt', '').strip()
        edited_prompt = data.get('edited_prompt', '').strip()
        
        try:
            # Get the question and chat history
            question = Question.query.get_or_404(response.question_id)
            template = FeedbackTemplate.query.get_or_404(question.template_id)
            
            if not response.chat_history:
                return jsonify({'success': False, 'error': 'No chat history available'}), 400
            
            chat_history = json.loads(response.chat_history)
            
            # Use edited prompt if provided, otherwise use custom prompt
            if edited_prompt:
                new_summary = generate_feedback_summary_with_edited_prompt(
                    question.question_text, 
                    chat_history,
                    edited_prompt
                )
            else:
                # Fallback to custom prompt approach
                new_summary = generate_feedback_summary_with_custom_prompt(
                    question.question_text, 
                    chat_history,
                    template.is_supervisor_feedback,
                    custom_prompt
                )
            
            # Update the response
            response.discussion_summary = new_summary
            db.session.commit()
            
            return jsonify({
                'success': True,
                'new_summary': new_summary
            })
            
        except Exception as e:
            print(f"Error regenerating summary: {e}")
            return jsonify({'success': False, 'error': 'Failed to regenerate summary'}), 500

    @app.route('/api/get-prompt/<response_id>', methods=['GET'])
    @login_required
    def get_current_prompt(response_id):
        user = ensure_authenticated()
        if not user:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
        response = Response.query.get_or_404(response_id)
        feedback_request = FeedbackRequest.query.get_or_404(response.feedback_request_id)
        
        # Check if user can access this request
        if not can_access_request(feedback_request, user):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403
        
        try:
            # Get the question and template for context
            question = Question.query.get_or_404(response.question_id)
            template = FeedbackTemplate.query.get_or_404(question.template_id)
            
            # Build supervisor-specific guidance for organization
            supervisor_guidance = ""
            if template.is_supervisor_feedback:
                supervisor_guidance = """

IMPORTANT: This feedback is about a supervisor/manager. When organizing:
- Focus on leadership and management behaviors
- Emphasize examples of team support, communication, and decision-making
- Balance constructive feedback with positive observations
- Highlight specific impacts on team dynamics or professional development
- Use professional language appropriate for management feedback"""
            
            # Reconstruct the prompt that was used
            current_prompt = f"""You are an expert at organizing and cleaning up feedback into professional, comprehensive statements. 

Your task is to organize and clean up what the feedback giver said while preserving ALL their content and meaning.

Guidelines:
- Focus ONLY on the user's actual responses and preserve ALL their examples and details
- Do NOT include or reference the interviewer's questions or prompts
- Clean up grammar, flow, and organization but preserve ALL substantive content
- Include ALL specific details, examples, and stories the user mentioned
- Organize the content logically but keep it comprehensive and detailed
- Write in third person as feedback about the person being reviewed
- This should be MORE verbose than the original, not less - organize and expand rather than summarize
- Aim for 3-6 sentences or more to capture all nuance and detail
- Base the organized feedback strictly on what the user said, including all their examples{supervisor_guidance}"""
            
            return jsonify({
                'success': True,
                'prompt': current_prompt
            })
            
        except Exception as e:
            print(f"Error getting current prompt: {e}")
            return jsonify({'success': False, 'error': 'Failed to load current prompt'}), 500

# Create the app instance
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='127.0.0.1', port=5001)