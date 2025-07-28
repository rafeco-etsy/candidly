# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Candidly is a peer feedback collection tool with conversational follow-ups. The system uses an AI chatbot to conduct dynamic interviews for open-ended feedback questions, then organizes and preserves responses for review before final submission. The system includes advanced features like regeneratable summaries with prompt editing, comprehensive markdown rendering, user authentication, and coaching guides.

## Core Architecture

Candidly is a fully-implemented feedback collection system with the following components:

### Key Components
- **User Authentication**: Flask-Login with role-based permissions (admins, template creators, users)
- **Template System**: Create reusable feedback templates with rating, agreement, and discussion questions
- **Survey Builder**: Create feedback requests with mixed question types and user assignment
- **AI Chatbot Interface**: GPT-4o powered conversational follow-ups for discussion questions
- **Response Organization**: AI organizes chat conversations while preserving ALL user content
- **Regenerate Feature**: Users can edit AI prompts directly to customize feedback organization
- **Review Interface**: Comprehensive review with markdown rendering and inline editing
- **Coaching Guides**: AI-generated personalized coaching for delivering feedback
- **Dashboard**: User-specific view of created and assigned feedback requests

### Data Flow
1. User creates feedback template or request with mixed question types
2. Feedback giver answers rating/agreement questions directly
3. Discussion questions trigger AI conversations with expanding text areas
4. System organizes chat into comprehensive feedback while preserving all details
5. Feedback giver reviews organized responses with full chat transcript access
6. Optional: Regenerate summaries by editing AI prompts directly
7. Final responses submitted and available in structured reports with coaching guides

## Technical Implementation

The system is fully implemented with the following features:
- **Real-time chat interface**: Smooth conversational experience with expanding text areas
- **AI integration**: GPT-4o for follow-up questions and response organization
- **Session management**: Preserves progress across questions with draft responses
- **Markdown rendering**: Professional formatting using marked.js library
- **User authentication**: Role-based permissions and secure session management
- **Prompt transparency**: Users can view and edit AI instructions directly
- **Full conversation storage**: Complete chat history for debugging and transparency

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

# Or manually:
# Run development server (in background for Claude Code)
nohup python app.py > flask.log 2>&1 &
# or
flask run

# Check if server is running
lsof -ti:5001

# View server logs
tail -f flask.log

# The app will be available at http://localhost:5001
```

**Important for Claude Code**: Always start the Flask server in the background using `nohup` to prevent timeout issues. The synchronous `python app.py` command will timeout after 2 minutes and kill the server.

### Development Script Features
The `dev.py` script automatically:
- Ensures database migrations are initialized and applied
- Verifies database tables exist and recreates if corrupted
- Checks for environment configuration
- Starts the development server with proper database state

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

# Downgrade migrations (if needed)
flask db downgrade
```

## Tech Stack

- **Backend**: Flask with SQLAlchemy ORM, Flask-Login for authentication
- **Database**: SQLite (for development), with comprehensive migration system
- **Frontend**: Bootstrap 5 with vanilla JavaScript, Marked.js for markdown rendering
- **AI**: OpenAI GPT-4o for intelligent conversational follow-ups and response organization
- **Testing**: Comprehensive pytest suite with fixtures and integration tests

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
│   ├── base.html      # Base template with Bootstrap and marked.js
│   ├── coaching.html  # AI-generated coaching guides
│   ├── report.html    # Feedback reports with regenerate feature
│   └── survey.html    # Survey interface with AI chat
├── tests/             # Comprehensive test suite
└── migrations/        # Database migration files
```

## Development Notes

- **Focus on simplicity**: Minimal cognitive load with clear user flows
- **Performance optimized**: Low-latency AI responses with focused single questions
- **Full authentication**: Role-based user system with permissions
- **AI-powered organization**: Preserves ALL user content while organizing professionally
- **Transparency**: Users can view and edit AI prompts directly
- **Extensible design**: Markdown rendering, comprehensive testing, and modular architecture
- **Regenerate feature**: Allows customization of feedback organization post-submission

## Key Features for Development

### Regenerate Summary System
- **API Endpoints**: `/api/get-prompt/<response_id>` and `/api/regenerate-summary/<response_id>`
- **Inline Editing**: Users can modify AI prompts directly in the UI
- **Real-time Updates**: Immediate feedback organization with loading states
- **Markdown Support**: Professional formatting for all AI-generated content

### AI Integration Best Practices
- **Focused Questions**: AI asks ONE question at a time for better user experience
- **Content Preservation**: Organization over summarization to keep all details
- **Context Awareness**: AI references previous responses for cohesive conversations
- **Customizable Prompts**: Users can edit instructions for personalized organization

### UI/UX Guidelines
- When users click on buttons, always perform some sort of state change to indicate that something has happened.

## Development Workflow Memories
- When starting the dev server always run it in the background.