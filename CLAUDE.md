# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Candidly is a peer feedback collection tool with conversational follow-ups. The system uses an AI chatbot to conduct dynamic interviews for open-ended feedback questions, then organizes and preserves responses for review before final submission. The system includes advanced features like regeneratable summaries with prompt editing, comprehensive markdown rendering, user authentication, and coaching guides.

## Key Components

- **User Authentication**: Flask-Login with role-based permissions
- **Template System**: Create reusable feedback templates with rating, agreement, and discussion questions
- **Survey Builder**: Create feedback requests with mixed question types and user assignment
- **AI Chatbot Interface**: GPT-4o powered conversational follow-ups for discussion questions
- **Response Organization**: AI organizes chat conversations while preserving ALL user content
- **Regenerate Feature**: Users can edit AI prompts directly to customize feedback organization
- **Review Interface**: Comprehensive review with markdown rendering and inline editing
- **Coaching Guides**: AI-generated personalized coaching for delivering feedback
- **Dashboard**: User-specific view of created and assigned feedback requests

## Tech Stack

- **Backend**: Flask with SQLAlchemy ORM, Flask-Login authentication
- **Database**: SQLite (development) with comprehensive migration system
- **Frontend**: Bootstrap 5, vanilla JavaScript, Marked.js for markdown
- **AI**: OpenAI GPT-4o with Vision API for screenshots
- **Testing**: Comprehensive pytest suite

## Commands

### Setup and Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables (create .env file)
echo "OPENAI_API_KEY=your-openai-api-key-here" > .env
echo "OPENAI_MODEL=gpt-4o" >> .env

# Initialize database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### Development
```bash
# Quick start with automatic database setup (recommended)
python dev.py

# Or run development server manually
python app.py

# The app will be available at http://localhost:5001
```

**Important for Claude Code**: Use `python dev.py` for reliable startup with automatic database setup.

The `dev.py` script automatically handles database migrations, table verification, and environment configuration.

### Testing
```bash
# Install test dependencies (if not already installed)
pip install -r requirements.txt

# Run all tests
pytest

# Run tests with coverage report
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_models.py

# Run specific test
pytest tests/test_routes.py::TestCreateRequest::test_create_request_post

# Run tests in verbose mode
pytest -v
```

### Database Management
```bash
# Create new migration after model changes
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade
```

## Project Structure

```
candidly/
├── app.py              # Main Flask application with all routes and AI integration
├── models.py           # Database models (User, FeedbackTemplate, Question, Response, etc.)
├── auth.py             # Authentication system and permissions
├── config.py           # Configuration settings
├── dev.py              # Development setup script
├── requirements.txt    # Python dependencies
├── templates/          # Jinja2 HTML templates
│   ├── base.html       # Base template with Bootstrap and marked.js
│   ├── coaching.html   # AI-generated coaching guides
│   ├── report.html     # Feedback reports with regenerate feature
│   └── survey.html     # Survey interface with AI chat
├── tests/              # Comprehensive test suite
└── migrations/         # Database migration files
```

## Key Development Notes

- **Focus on simplicity**: Minimal cognitive load with clear user flows
- **Performance optimized**: Low-latency AI responses with focused single questions
- **Full authentication**: Role-based user system with permissions
- **AI-powered organization**: Preserves ALL user content while organizing professionally
- **Transparency**: Users can view and edit AI prompts directly
- **Extensible design**: Markdown rendering, comprehensive testing, and modular architecture
- **Regenerate feature**: Allows customization of feedback organization post-submission