# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Candidly is a peer feedback collection tool with conversational follow-ups. The system uses a chatbot to conduct dynamic interviews for open-ended feedback questions, then compiles and summarizes responses for review before final submission.

## Core Architecture

This is an early-stage project currently containing only product requirements. The system will need to implement:

### Key Components
- **Survey Builder**: Create feedback requests with rating and discussion questions
- **Chatbot Interface**: AI-powered conversational follow-ups for discussion questions  
- **Response Summarization**: Convert chat conversations into concise feedback summaries
- **Review Interface**: Allow feedback givers to edit responses before submission
- **Feedback Compilation**: Generate structured reports for feedback requestors

### Data Flow
1. Feedback requestor creates survey with mixed question types
2. Feedback giver answers rating questions directly
3. Discussion questions trigger chatbot conversations with dynamic follow-ups
4. System summarizes chat into professional feedback statements
5. Feedback giver reviews/edits compiled draft before submission
6. Final responses stored and made available to requestor

## Technical Considerations

Since no code exists yet, future development should consider:
- Real-time chat interface for smooth conversational experience
- AI integration for follow-up question generation and response summarization
- Session management to preserve progress across questions
- Privacy controls for anonymous feedback when configured

## Commands

### Setup and Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### Development
```bash
# Run development server
python app.py
# or
flask run

# The app will be available at http://localhost:5001
```

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

- **Backend**: Flask with SQLAlchemy ORM
- **Database**: SQLite (for development)
- **Frontend**: Bootstrap 5 with vanilla JavaScript
- **Chatbot**: Simple rule-based responses (MVP - integrate AI service later)

## Project Structure

```
candidly/
├── app.py              # Main Flask application
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── app/
│   └── models.py      # Database models
├── templates/         # Jinja2 HTML templates
├── static/           # CSS, JS, images
└── migrations/       # Database migration files
```

## Development Notes

- PRD emphasizes simplicity and minimal cognitive load
- Performance requirement for low-latency chatbot responses
- MVP excludes authentication, notifications, and complex analytics
- Focus on single-page survey flow with clear review/confirmation step
- Chatbot uses simple rule-based responses for MVP (replace with AI integration later)