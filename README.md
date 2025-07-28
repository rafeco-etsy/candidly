# Candidly

An AI-powered feedback collection tool that helps users give thoughtful, detailed feedback through intelligent conversations. Features both traditional survey collection and a single-player mode for external forms.

![Candidly Demo](https://img.shields.io/badge/Status-Active-brightgreen) ![Python](https://img.shields.io/badge/Python-3.13-blue) ![Flask](https://img.shields.io/badge/Flask-2.3.3-red) ![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-orange)

## ✨ Features

### 🎯 Single-Player Mode (NEW!)
- **External Form Support**: Upload screenshots or paste text from any HRIS/external feedback form
- **AI Interview Assistant**: Chat-based guidance to help you craft thoughtful responses
- **Context-Aware**: AI understands working relationships and adapts questioning depth accordingly
- **Systematic Coverage**: Ensures all feedback topics are explored comprehensively
- **Copy & Paste Ready**: Generate professional responses ready for external forms

### 🤖 AI-Powered Conversations
- **Intelligent Follow-ups**: GPT-4o conducts natural conversations to gather detailed feedback
- **Contextual Awareness**: AI remembers all previous questions and answers for connected conversations
- **Verbose Organization**: Preserves ALL user content while organizing it professionally
- **Regenerate Summaries**: Edit AI prompts directly to customize how feedback is organized

### 📝 Traditional Survey Building
- **Template System**: Create reusable feedback templates with rating and discussion questions
- **Mixed Question Types**: Combine quick ratings (1-5 scale) with in-depth discussion questions
- **Dashboard Management**: View all feedback requests and their status at a glance
- **User Authentication**: Role-based permissions for template creation and request management

### 🔍 Advanced Review & Edit Process
- **Smart Organization**: AI-powered feedback organization that preserves all details and examples
- **Inline Prompt Editing**: See and modify the exact AI instructions used for organizing feedback
- **Markdown Rendering**: Professional formatting with headers, bullet points, and emphasis
- **Full Chat Transcripts**: Collapsible conversation history for transparency and debugging
- **Review Before Submit**: Users can review and edit all responses before final submission

### 🎯 Enhanced User Experience
- **Expanding Text Areas**: Multi-line input with keyboard shortcuts (Enter to send, Ctrl+Enter for new line)
- **Real-time Updates**: Live feedback organization with loading states
- **Professional Reports**: Print-ready feedback reports with structured formatting
- **Coaching Guides**: AI-generated guidance for delivering feedback effectively

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- OpenAI API key (optional - falls back to simple responses without it)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/rafeco-etsy/candidly.git
   cd candidly
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables** (create `.env` file)
   ```bash
   echo "OPENAI_API_KEY=your-openai-api-key-here" > .env
   ```

4. **Start the development server**
   ```bash
   python dev.py
   ```
   
   The app will be available at http://localhost:5001

## 🎯 Single-Player Mode

Perfect for when you need to complete feedback in external systems (Workday, BambooHR, etc.):

1. **Access**: Navigate to `/single-player` or click "AI Feedback Assistant" from dashboard
2. **Upload Context**: Screenshot your feedback form or paste the questions
3. **Describe Relationship**: Tell the AI about your working relationship with the person
4. **Chat Interview**: AI guides you through systematic feedback gathering
5. **Final Organization**: Get professionally organized responses ready to copy/paste

### Example Single-Player Flow
```
AI: I can see this form asks about leadership and collaboration. 
    Let's start with leadership - can you give me a broad overview 
    of how they approach leading projects or teams?

You: They're really good at keeping projects on track and making 
     sure everyone knows what they need to do...

AI: That's great! Can you share a specific example of when they 
    kept a project on track? What did they actually do?

[Continue conversation...]

Final Output: Professional, organized feedback ready for your external form
```

## 🛠️ Development

### Manual Setup
```bash
# Initialize database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Run development server
python app.py
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test
pytest tests/test_routes.py::TestChatAPI
```

### Database Management
```bash
# Create new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade
```

## 🏗️ Architecture

### Core Components
- **Single-Player Mode**: AI interview assistant for external feedback forms
- **Survey Builder**: Create feedback requests with mixed question types
- **AI Chat Interface**: GPT-4o powered conversational follow-ups
- **Smart Organization**: Convert conversations into professional feedback while preserving all details
- **Review Interface**: Edit and approve responses before submission
- **Template System**: Reusable feedback question sets with dashboard management

### Tech Stack
- **Backend**: Flask with SQLAlchemy ORM, Flask-Login for authentication
- **Database**: SQLite (development) / PostgreSQL (production ready)
- **Frontend**: Bootstrap 5 with vanilla JavaScript, Marked.js for markdown rendering
- **AI**: OpenAI GPT-4o for conversations and feedback organization
- **Testing**: pytest with Flask-testing and comprehensive test coverage

### Data Flow

**Traditional Survey Mode:**
1. **Template Creation**: Define reusable question sets
2. **Request Setup**: Create feedback requests from templates or custom questions
3. **Response Collection**: Users answer ratings directly, chat for discussions
4. **AI Processing**: Contextual follow-ups and intelligent organization
5. **Review & Submit**: Final review and approval before submission
6. **Reporting**: Compiled feedback available to requestors

**Single-Player Mode:**
1. **Form Upload**: Screenshot or paste external feedback form questions
2. **Context Setting**: Describe working relationship with feedback recipient
3. **AI Interview**: Systematic chat-based exploration of all feedback topics
4. **Organization**: AI creates professional responses while preserving all user content
5. **Export**: Copy organized feedback for use in external systems

## 📖 Usage Examples

### Creating a Template
1. Navigate to `/templates/create`
2. Add questions like:
   - **Rating**: "How would you rate their communication skills?" (1-5 scale)
   - **Discussion**: "Can you describe their leadership style?"

### Feedback Collection Flow
1. **Start Survey**: Recipient gets link to feedback form
2. **Answer Ratings**: Quick 1-5 scale responses with N/A options
3. **Chat Discussions**: AI-guided conversations with expanding text areas
4. **Review Responses**: Edit AI-organized feedback with inline prompt editing
5. **Regenerate**: Customize AI prompts to change how feedback is organized
6. **Submit**: Final feedback delivered with full chat transcripts available

### Example AI Conversation
```
Assistant: How would you describe their collaboration style?

User: They're really good at working with others
Assistant: Can you share a specific example of when they collaborated well?

User: Yes, during the project last month they really helped coordinate between teams

Assistant: That sounds valuable! What specific actions did they take to coordinate effectively?
```

**Generated Organization**: 
> "They demonstrate strong collaboration skills, particularly excelling at cross-team coordination. During a recent project last month, they effectively facilitated communication between different teams, taking specific actions to coordinate efforts and ensure smooth project execution. Their collaborative approach helps bridge gaps between departments and contributes to successful project outcomes."

**With Regenerate Feature**: Users can edit the AI prompt to change organization style (more formal, bullet points, focus on specific aspects, etc.)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🔒 Security & Privacy

- All feedback conversations are stored locally in your database
- OpenAI API calls are made server-side for chat and summarization
- No conversation data is permanently stored by OpenAI (as per their API policy)
- Review step ensures users control what feedback is actually submitted

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/) and [OpenAI GPT-4o](https://openai.com/)
- UI powered by [Bootstrap 5](https://getbootstrap.com/)
- Icons from [Font Awesome](https://fontawesome.com/)

## 📧 Contact

**Project**: [https://github.com/rafeco-etsy/candidly](https://github.com/rafeco-etsy/candidly)
