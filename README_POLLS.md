# ALX Project Nexus - Online Poll System

A professional Django REST API application for creating and managing online polls, built as part of the ALX Software Engineering program.

## 🚀 Features

- **User Authentication & Authorization**
  - JWT token-based authentication
  - User registration and login
  - Permission-based access control

- **Poll Management**
  - Create, read, update, delete polls
  - Set poll expiration dates
  - Multiple choice options per poll
  - Real-time voting results

- **Voting System**
  - One vote per IP address per poll
  - Secure vote validation
  - Vote counting and statistics
  - Results visualization

- **Security Features**
  - Rate limiting
  - CSRF protection
  - XSS prevention
  - SQL injection protection
  - Security headers

- **Performance & Scalability**
  - Redis caching
  - Celery background tasks
  - Database optimization
  - Asynchronous processing

## 🏗️ Architecture

```
alx-project-nexus/
├── .github/workflows/     # CI pipelines
├── backend/              # Django application
│   ├── manage.py
│   ├── polls/           # Polls app
│   ├── pollsystem/      # Main project
│   └── staticfiles/     # Static assets
├── docs/                # Documentation
├── tests/               # Test suite
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 🛠️ Technology Stack

- **Backend**: Django 4.2, Django REST Framework
- **Database**: PostgreSQL 15
- **Cache/Queue**: Redis 7
- **Task Queue**: Celery + Celery Beat
- **Authentication**: JWT tokens
- **Containerization**: Docker & Docker Compose
- **Testing**: Django TestCase, pytest
- **CI**: GitHub Actions

## 📋 Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL (for local development)
- Redis (for local development)

## 🚀 Quick Start

### Using Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/alx-project-nexus.git
   cd alx-project-nexus
   ```

2. **Start the application**
   ```bash
   docker-compose up --build
   ```

3. **Access the application**
   - API: http://localhost:8000/api/
   - Admin: http://localhost:8000/admin/

### Local Development

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run migrations**
   ```bash
   cd backend
   python manage.py migrate
   ```

5. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start development server**
   ```bash
   python manage.py runserver
   ```

## 📚 API Documentation

### Authentication Endpoints

- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout

### Poll Endpoints

- `GET /api/polls/` - List all polls
- `POST /api/polls/` - Create new poll
- `GET /api/polls/{id}/` - Get poll details
- `PUT /api/polls/{id}/` - Update poll
- `DELETE /api/polls/{id}/` - Delete poll
- `GET /api/polls/{id}/results/` - Get poll results

### Voting Endpoints

- `POST /api/votes/` - Cast a vote
- `GET /api/polls/{id}/options/` - Get poll options

### Example API Usage

```bash
# Register user
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "securepass123"}'

# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "securepass123"}'

# Create poll (with auth token)
curl -X POST http://localhost:8000/api/polls/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"title": "Favorite Color", "description": "What is your favorite color?", "expires_at": "2024-12-31T23:59:59Z"}'
```

## 🧪 Testing

### Run All Tests
```bash
cd backend
python manage.py test ../tests/
```

### Run Specific Test Categories
```bash
python manage.py test tests.test_models     # Model tests
python manage.py test tests.test_views      # View tests
python manage.py test tests.test_api        # API tests
python manage.py test tests.test_performance # Performance tests
```

### Coverage Report
```bash
pip install coverage
coverage run --source='.' manage.py test ../tests/
coverage report
coverage html  # Generate HTML report
```

## 🔄 Background Tasks

The application uses Celery for background task processing:

### Celery Workers
- **Poll cleanup**: Automatically archive expired polls
- **Email notifications**: Send poll result summaries
- **Data aggregation**: Calculate voting statistics
- **Cache warming**: Pre-populate frequently accessed data

### Celery Beat (Scheduler)
- Runs periodic tasks like poll expiry checks
- Generates daily/weekly reports
- Cleans up old data

## 🛡️ Security Features

- **Rate Limiting**: 100 requests per hour per IP
- **CSRF Protection**: Django's built-in CSRF middleware
- **SQL Injection Prevention**: Django ORM protection
- **XSS Protection**: Input sanitization and output escaping
- **Secure Headers**: Security middleware for HTTP headers

## 🚀 Deployment

### Production Deployment

1. **Environment Setup**
   ```bash
   # Production environment variables
   DEBUG=False
   SECRET_KEY=your-super-secret-key
   DATABASE_URL=postgresql://user:pass@localhost/dbname
   REDIS_URL=redis://localhost:6379/0
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   ```

2. **Database Migration**
   ```bash
   python manage.py migrate
   python manage.py collectstatic
   ```

3. **Using Docker in Production**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

### CI Pipeline

The project includes GitHub Actions workflows for:
- **Testing**: Run test suite on all PRs and commits
- **Security Scanning**: Check for vulnerabilities with CodeQL
- **Code Quality**: Linting, formatting, and security checks
- **Build Verification**: Docker image build testing

## 📊 Database Schema

### ERD (Entity Relationship Diagram)

```sql
-- Users (Django's built-in User model)
-- ├── id (PK)
-- ├── username
-- ├── email
-- └── password_hash

-- Polls
-- ├── id (PK)
-- ├── title
-- ├── description
-- ├── created_by (FK → Users.id)
-- ├── created_at
-- ├── expires_at
-- └── is_active

-- Poll Options
-- ├── id (PK)
-- ├── poll_id (FK → Polls.id)
-- ├── text
-- └── order

-- Votes
-- ├── id (PK)
-- ├── poll_id (FK → Polls.id)
-- ├── option_id (FK → PollOptions.id)
-- ├── voter_ip (UNIQUE per poll)
-- └── voted_at
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Standards
- Follow PEP 8 for Python code
- Use Black for code formatting
- Add tests for new features
- Update documentation as needed

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **Your Name** - [GitHub Profile](https://github.com/yourusername)
- **ALX Software Engineering Program** - [ALX](https://www.alxafrica.com/)

## 🙏 Acknowledgments

- ALX Software Engineering Program
- Django and DRF communities
- Contributors and reviewers

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Email: your-email@example.com
- ALX Community Forums

---

**Built with ❤️ for the ALX Software Engineering Program**
