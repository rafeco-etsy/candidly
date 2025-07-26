# Candidly

An AI-powered peer feedback collection tool that uses conversational follow-ups to gather detailed, thoughtful feedback through intelligent chat conversations.

![Candidly Demo](https://img.shields.io/badge/Status-Active-brightgreen) ![Python](https://img.shields.io/badge/Python-3.13-blue) ![Flask](https://img.shields.io/badge/Flask-2.3.3-red) ![OpenAI](https://img.shields.io/badge/OpenAI-GPT--3.5--turbo-orange)

## ✨ Features

### 🤖 AI-Powered Conversations
- **Intelligent Follow-ups**: GPT-3.5-turbo conducts natural conversations to gather detailed feedback
- **Contextual Awareness**: AI remembers all previous questions and answers for connected conversations
- **Professional Summarization**: Converts chat conversations into polished feedback statements

### 📝 Flexible Survey Building
- **Template System**: Create reusable feedback templates with rating and discussion questions
- **Mixed Question Types**: Combine quick ratings (1-5 scale) with in-depth discussion questions
- **Dashboard Management**: View all feedback requests and their status at a glance

### 🔍 Review & Edit Process
- **Smart Summaries**: AI-generated professional feedback from conversational exchanges
- **Review Before Submit**: Users can review and edit all responses before final submission
- **Privacy Controls**: Built-in review step ensures feedback accuracy

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
- **Survey Builder**: Create feedback requests with mixed question types
- **AI Chat Interface**: GPT-3.5-turbo powered conversational follow-ups
- **Smart Summarization**: Convert conversations into professional feedback
- **Review Interface**: Edit and approve responses before submission
- **Template System**: Reusable feedback question sets with dashboard management

### Tech Stack
- **Backend**: Flask with SQLAlchemy ORM
- **Database**: SQLite (development) / PostgreSQL (production ready)
- **Frontend**: Bootstrap 5 with vanilla JavaScript
- **AI**: OpenAI GPT-3.5-turbo for conversations and summarization
- **Testing**: pytest with Flask-testing

### Data Flow
1. **Template Creation**: Define reusable question sets
2. **Request Setup**: Create feedback requests from templates or custom questions
3. **Response Collection**: Users answer ratings directly, chat for discussions
4. **AI Processing**: Contextual follow-ups and intelligent summarization
5. **Review & Submit**: Final review and approval before submission
6. **Reporting**: Compiled feedback available to requestors

## 📖 Usage Examples

### Creating a Template
1. Navigate to `/templates/create`
2. Add questions like:
   - **Rating**: "How would you rate their communication skills?" (1-5 scale)
   - **Discussion**: "Can you describe their leadership style?"

### Feedback Collection Flow
1. **Start Survey**: Recipient gets link to feedback form
2. **Answer Ratings**: Quick 1-5 scale responses
3. **Chat Discussions**: AI-guided conversations for detailed feedback
4. **Review Responses**: Edit AI-generated summaries if needed
5. **Submit**: Final feedback delivered to requestor

### Example AI Conversation
```
Assistant: How would you describe their collaboration style?

User: They're really good at working with others
Assistant: Can you share a specific example of when they collaborated well?

User: Yes, during the project last month they really helped coordinate between teams

Assistant: That sounds valuable! What specific actions did they take to coordinate effectively?
```

**Generated Summary**: 
> "They demonstrate strong collaboration skills, particularly excelling at cross-team coordination. During recent projects, they effectively facilitated communication between different teams, taking specific actions to ensure smooth project execution and successful outcomes."

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

- Built with [Flask](https://flask.palletsprojects.com/) and [OpenAI GPT-3.5-turbo](https://openai.com/)
- UI powered by [Bootstrap 5](https://getbootstrap.com/)
- Icons from [Font Awesome](https://fontawesome.com/)

## 📧 Contact

**Project**: [https://github.com/rafeco-etsy/candidly](https://github.com/rafeco-etsy/candidly)
