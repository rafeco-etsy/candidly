# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Candidly is an AI-powered feedback collection tool with two main modes:
1. **Traditional Survey Mode**: Full feedback collection system with templates, AI chat, and review process
2. **Single-Player Mode**: AI interview assistant for external feedback forms (HRIS, Workday, etc.)

The system uses GPT-4o to conduct intelligent conversations that gather detailed, specific feedback, then organizes responses professionally while preserving all user content.

## Key Components

**Traditional Survey Mode:**
- User authentication with role-based permissions
- Template system for reusable feedback questions (rating, agreement, discussion)
- AI chatbot for conversational follow-ups on discussion questions
- Response organization while preserving all user content
- Regenerate feature with editable AI prompts
- Review interface with markdown rendering

**Single-Player Mode:**
- Screenshot upload and text input for external feedback forms
- OpenAI Vision API for form text extraction
- Chat-based AI interview that systematically covers all feedback topics
- Context-aware questioning that adapts to working relationship and role level
- Final organized feedback ready for copy/paste to external systems

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
├── app.py              # Main Flask application with routes and AI integration
├── models.py           # Database models 
├── config.py           # Configuration settings
├── dev.py              # Development setup script
├── requirements.txt    # Python dependencies
├── templates/          # Jinja2 HTML templates
│   ├── base.html       # Base template with Bootstrap and marked.js
│   ├── single_player.html     # Single-player mode form upload
│   ├── single_player_chat.html # Single-player AI chat interface
│   ├── survey.html     # Traditional survey interface with AI chat
│   └── report.html     # Feedback reports with regenerate feature
├── tests/              # Comprehensive test suite
└── migrations/         # Database migration files
```

## Key Development Notes

- **Single-Player Mode**: Primary focus is the AI interview assistant for external forms
- **AI Integration**: GPT-4o with Vision API for screenshot text extraction
- **Chat Interface**: Expanding textareas, character counters, systematic topic coverage
- **Context Awareness**: AI adapts questioning depth based on working relationship
- **Content Preservation**: AI organizes feedback while preserving ALL user details