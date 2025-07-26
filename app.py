from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_migrate import Migrate
from config import Config
from models import db, FeedbackTemplate, FeedbackRequest, Question, Response
from datetime import datetime
import json
import openai
import os

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
    """Generate a professional feedback summary from chat conversation using LLM."""
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
        
        # Build supervisor-specific guidance for summarization
        supervisor_guidance = ""
        if is_supervisor_feedback:
            supervisor_guidance = """

IMPORTANT: This feedback is about a supervisor/manager. When summarizing:
- Focus on leadership and management behaviors
- Emphasize examples of team support, communication, and decision-making
- Balance constructive feedback with positive observations
- Highlight specific impacts on team dynamics or professional development
- Use professional language appropriate for management feedback"""
        
        # Create summarization prompt
        response = client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": f"""You are an expert at summarizing feedback into professional, actionable statements. 

Your task is to create a concise, professional summary based on what the feedback giver actually said, not the interviewer's questions.

Guidelines:
- Focus ONLY on the user's actual responses and the concrete examples they provided
- Do NOT include or reference the interviewer's questions or prompts
- Maintain a professional, constructive tone
- Include specific details and examples when the user mentioned them
- Keep it concise but comprehensive (1-3 sentences typically)
- Write in third person as feedback about the person being reviewed
- Base the summary strictly on what the user said, not what was asked{supervisor_guidance}"""
                },
                {
                    "role": "user", 
                    "content": f"""Please summarize the feedback given about: "{question_text}"

The feedback giver's responses:
{user_content}

Full conversation context (for understanding):
{conversation_text}

Provide a professional feedback summary based ONLY on what the feedback giver actually said:"""
                }
            ],
            max_tokens=200,
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
            intro_text = request.form.get('intro_text', '')
            is_supervisor_feedback = 'is_supervisor_feedback' in request.form
            
            # Create template
            template = FeedbackTemplate(
                name=name, 
                description=description,
                intro_text=intro_text,
                is_supervisor_feedback=is_supervisor_feedback
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
        chat_history = data.get('chat_history', [])
        feedback_request_id = data.get('feedback_request_id')
        
        # Get the original question and template to provide context
        question = Question.query.get_or_404(question_id)
        template = FeedbackTemplate.query.get_or_404(question.template_id)
        
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

            # Build conversation history for the LLM
            messages = [
                {
                    "role": "system",
                    "content": f"""You are a skilled feedback interviewer helping someone provide detailed, constructive feedback. Your goal is to help them give comprehensive and thoughtful responses about: "{question.question_text}"

Guidelines:
- Ask thoughtful follow-up questions to encourage depth and specificity
- Help them provide concrete examples and details
- Guide them toward constructive, actionable feedback
- Keep your responses conversational and supportive
- When they've provided sufficient detail (usually after 2-3 exchanges), acknowledge their response and ask if there's anything else they'd like to add
- If they indicate they're done (saying things like "done", "nothing else", "that's all"), respond with "Thank you for that detailed feedback!" to signal completion
- Reference previous answers when relevant to create a cohesive feedback experience{supervisor_guidance}

Be warm, professional, and focused on helping them give the best possible feedback.{context_info}"""
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
                max_tokens=200,
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

    @app.route('/coaching/<request_id>')
    def coaching_guide(request_id):
        feedback_request = FeedbackRequest.query.get_or_404(request_id)
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
                             coaching_content=coaching_content)

# Create the app instance
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='127.0.0.1', port=5001)