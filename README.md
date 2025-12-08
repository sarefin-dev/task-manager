# Task Management API
(this readme has been generated using claude and many codes as well - not all features are included, repo still in development)
A modern, high-performance async REST API built with FastAPI, SQLModel, and PostgreSQL for efficient task management with full CRUD operations.

![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688?style=flat&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat&logo=python)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791?style=flat&logo=postgresql)
![SQLModel](https://img.shields.io/badge/SQLModel-0.0.22-red?style=flat)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

- 🚀 **Fully Async** - Built with async/await patterns using asyncpg for maximum performance
- 🔄 **Complete CRUD** - Create, Read, Update, Delete operations for task management
- 🗃️ **Database Migrations** - Version-controlled schema management with Alembic
- 📊 **Advanced Filtering** - Filter tasks by completion status, priority, with pagination support
- ✅ **Data Validation** - Automatic request/response validation using Pydantic
- 📚 **Interactive API Docs** - Auto-generated Swagger UI and ReDoc documentation
- 🎯 **Type Safety** - Full type hints throughout the codebase with SQLModel
- 🔍 **Query Optimization** - Efficient async database queries with connection pooling
- ⏰ **Timezone Aware** - Proper timezone handling for all datetime fields
- 🏗️ **Clean Architecture** - Well-organized modular structure following best practices

## 🛠️ Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast web framework for building APIs
- **ORM**: [SQLModel](https://sqlmodel.tiangolo.com/) - SQL databases with Python type hints
- **Database**: [PostgreSQL](https://www.postgresql.org/) - Advanced open-source relational database
- **Async Driver**: [asyncpg](https://github.com/MagicStack/asyncpg) - Fast PostgreSQL driver for Python
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/) - Lightweight database migration tool
- **Server**: [Uvicorn](https://www.uvicorn.org/) - Lightning-fast ASGI server
- **Validation**: [Pydantic](https://docs.pydantic.dev/) - Data validation using Python type annotations

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.12+** - [Download](https://www.python.org/downloads/)
- **PostgreSQL 14+** - [Download](https://www.postgresql.org/download/)
- **Git** - [Download](https://git-scm.com/downloads/)

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/task-api.git
cd task-api
```

### 2. Create Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/taskdb
ENVIRONMENT=development
```

**Environment Variables:**
- `DATABASE_URL` - PostgreSQL async connection string
- `ENVIRONMENT` - Application environment (development/production)

### 5. Database Setup

**Create the database:**
```sql
CREATE DATABASE taskdb;
```

**Initialize Alembic (first time only):**
```bash
alembic init alembic
```

**Create initial migration:**
```bash
alembic revision --autogenerate -m "create tasks table"
```

**Apply migrations:**
```bash
alembic upgrade head
```

### 6. Run the Application

**Development Mode (with auto-reload):**
```bash
fastapi dev app/main.py
```

**Production Mode:**
```bash
fastapi run app/main.py --workers 4
```

The API will be available at:
- **Application**: http://127.0.0.1:8000
- **Interactive Docs**: http://127.0.0.1:8000/docs
- **Alternative Docs**: http://127.0.0.1:8000/redoc

> **Note**: `fastapi dev` includes auto-reload for development. Use `fastapi run` for production deployments.

## 📡 API Endpoints

### Health & Info

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Welcome message and API info |
| `GET` | `/health` | Health check endpoint |

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/tasks/` | Create a new task |
| `GET` | `/tasks/` | Get all tasks (with filters & pagination) |
| `GET` | `/tasks/{id}` | Get a specific task by ID |
| `PATCH` | `/tasks/{id}` | Update a task (partial update) |
| `DELETE` | `/tasks/{id}` | Delete a task |
| `POST` | `/tasks/{id}/complete` | Mark task as completed |

### Query Parameters

**GET /tasks/**
- `skip` (integer, default=0, min=0) - Number of records to skip for pagination
- `limit` (integer, default=100, min=1, max=100) - Maximum records to return
- `completed` (boolean, optional) - Filter by completion status
- `priority` (string, optional) - Filter by priority: `low`, `medium`, or `high`

### Request/Response Examples

#### Create Task

**Request:**
```http
POST /tasks/
Content-Type: application/json

{
  "title": "Complete project documentation",
  "description": "Write comprehensive README and API docs",
  "priority": "high"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "title": "Complete project documentation",
  "description": "Write comprehensive README and API docs",
  "priority": "high",
  "completed": false,
  "created_at": "2025-12-08T18:30:00+00:00",
  "updated_at": null
}
```

#### Get All Tasks with Filters

**Request:**
```http
GET /tasks/?completed=false&priority=high&skip=0&limit=10
```

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "title": "Complete project documentation",
    "description": "Write comprehensive README and API docs",
    "priority": "high",
    "completed": false,
    "created_at": "2025-12-08T18:30:00+00:00",
    "updated_at": null
  }
]
```

#### Update Task

**Request:**
```http
PATCH /tasks/1
Content-Type: application/json

{
  "completed": true
}
```

**Response (200 OK):**
```json
{
  "id": 1,
  "title": "Complete project documentation",
  "description": "Write comprehensive README and API docs",
  "priority": "high",
  "completed": true,
  "created_at": "2025-12-08T18:30:00+00:00",
  "updated_at": "2025-12-08T19:45:00+00:00"
}
```

#### Error Response

**Response (404 Not Found):**
```json
{
  "detail": "Task with id 999 not found"
}
```

## 📁 Project Structure

```
task-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── database.py          # Database connection and session management
│   ├── models.py            # SQLModel models and Pydantic schemas
│   └── routers/
│       ├── __init__.py
│       └── tasks.py         # Task endpoints and business logic
├── alembic/
│   ├── versions/            # Database migration files
│   │   └── xxxx_create_tasks_table.py
│   └── env.py              # Alembic configuration for async support
├── alembic.ini             # Alembic settings
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (not in git)
├── .gitignore             # Git ignore rules
├── Dockerfile             # Docker container definition
├── docker-compose.yml     # Docker Compose configuration
└── README.md              # Project documentation
```

## 🔧 Development

### FastAPI CLI Commands

**Development Mode:**
```bash
# Start dev server with auto-reload
fastapi dev app/main.py

# Custom port
fastapi dev app/main.py --port 8080

# Custom host and port
fastapi dev app/main.py --host 0.0.0.0 --port 8080
```

**Production Mode:**
```bash
# Start production server
fastapi run app/main.py

# With multiple workers
fastapi run app/main.py --workers 4

# With proxy headers (behind reverse proxy)
fastapi run app/main.py --workers 4 --proxy-headers
```

### Database Migrations

**Create a new migration:**
```bash
alembic revision --autogenerate -m "description of changes"
```

**Apply all pending migrations:**
```bash
alembic upgrade head
```

**Rollback last migration:**
```bash
alembic downgrade -1
```

**View current migration:**
```bash
alembic current
```

**View migration history:**
```bash
alembic history --verbose
```

**Rollback to specific migration:**
```bash
alembic downgrade <revision_id>
```

### Code Quality

This project follows PEP 8 style guidelines and uses type hints throughout.

**Format code (optional):**
```bash
# Install formatters
pip install black isort

# Format code
black app/
isort app/

# Check code quality
black --check app/
```

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

**1. Create `Dockerfile`:**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run migrations and start server
CMD alembic upgrade head && \
    fastapi run app/main.py --host 0.0.0.0 --port 8000 --workers 4
```

**2. Create `docker-compose.yml`:**

```yaml
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: taskdb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-network

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:${DB_PASSWORD:-changeme}@db:5432/taskdb
      ENVIRONMENT: production
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - app-network

volumes:
  postgres_data:

networks:
  app-network:
    driver: bridge
```

**3. Run with Docker:**

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## 🚀 Production Deployment

### Environment Configuration

Create separate environment files:

**.env.development**
```env
DATABASE_URL=postgresql+asyncpg://postgres:dev_password@localhost:5432/taskdb_dev
ENVIRONMENT=development
LOG_LEVEL=debug
```

**.env.production**
```env
DATABASE_URL=postgresql+asyncpg://postgres:secure_password@db-server:5432/taskdb
ENVIRONMENT=production
LOG_LEVEL=info
```

### Production Best Practices

1. **Disable Auto-Generated Docs in Production**

Update `app/main.py`:

```python
import os

ENV = os.getenv("ENVIRONMENT", "development")

app = FastAPI(
    title="Task Management API",
    description="Simple async task management API with PostgreSQL and SQLModel",
    version="1.0.0",
    docs_url="/docs" if ENV == "development" else None,
    redoc_url="/redoc" if ENV == "development" else None,
)
```

2. **Use Environment Variables for Secrets**

Never hardcode credentials. Always use environment variables.

3. **Run with Multiple Workers**

```bash
export ENVIRONMENT=production
fastapi run app/main.py --workers 4 --proxy-headers
```

4. **Set Up Database Connection Pooling**

Update `app/database.py` for production:

```python
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Disable SQL logging in production
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
)
```

5. **Enable HTTPS**

Use a reverse proxy like Nginx or Traefik in front of your FastAPI application.

### Using Gunicorn (Linux Only)

For Linux production deployments:

```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

## 🧪 Testing

```bash
# Install testing dependencies
pip install pytest pytest-asyncio httpx

# Create tests directory
mkdir tests
```

**Example test file (`tests/test_tasks.py`):**

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_task():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/tasks/",
            json={
                "title": "Test Task",
                "description": "Test Description",
                "priority": "medium"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Task"
        assert data["completed"] is False
```

**Run tests:**
```bash
pytest
```

## 🔐 Security Considerations

- ✅ Never commit `.env` file to version control
- ✅ Use strong, unique passwords for database
- ✅ Disable interactive docs in production
- ✅ Implement rate limiting for API endpoints
- ✅ Add authentication/authorization (JWT tokens)
- ✅ Use HTTPS in production
- ✅ Validate and sanitize all inputs
- ✅ Keep dependencies updated
- ✅ Use prepared statements (SQLAlchemy handles this)
- ✅ Implement proper logging and monitoring

## 📊 Monitoring & Logging

### Add Logging

Update `app/main.py`:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

### Health Check Endpoint

The `/health` endpoint can be used for:
- Kubernetes liveness/readiness probes
- Load balancer health checks
- Monitoring systems

## 📝 Development Workflow

### Quick Reference Commands

```bash
# Development
fastapi dev app/main.py                    # Start dev server
alembic revision --autogenerate -m "msg"   # Create migration
alembic upgrade head                       # Apply migrations

# Testing
pytest                                     # Run tests
pytest -v                                  # Verbose output
pytest --cov=app                          # With coverage

# Production
export ENVIRONMENT=production
fastapi run app/main.py --workers 4

# Docker
docker-compose up -d                       # Start services
docker-compose logs -f api                 # View logs
docker-compose down                        # Stop services
```

## 🎯 Future Enhancements

- [ ] **Authentication & Authorization** - JWT-based user authentication
- [ ] **User Management** - User registration, login, profile management
- [ ] **Task Assignment** - Assign tasks to specific users
- [ ] **Categories/Tags** - Organize tasks with categories and tags
- [ ] **Due Dates** - Add deadline tracking with reminders
- [ ] **File Attachments** - Upload and attach files to tasks
- [ ] **Search Functionality** - Full-text search across tasks
- [ ] **Audit Logging** - Track all changes to tasks
- [ ] **Rate Limiting** - Implement API rate limiting
- [ ] **Caching** - Add Redis for performance optimization
- [ ] **Email Notifications** - Send email reminders for due tasks
- [ ] **WebSocket Support** - Real-time updates
- [ ] **Task Comments** - Add commenting system
- [ ] **Recurring Tasks** - Support for repeating tasks
- [ ] **Export/Import** - Export tasks to CSV/JSON

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Commit with conventional commits**
   ```bash
   git commit -m 'feat: add amazing feature'
   ```
5. **Push to the branch**
   ```bash
   git push origin feature/amazing-feature
   ```
6. **Open a Pull Request**

### Commit Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, semicolons, etc.)
- `refactor:` - Code refactoring without feature changes
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks, dependency updates

### Code Review Checklist

- [ ] Code follows project structure and conventions
- [ ] All tests pass
- [ ] New features include tests
- [ ] Documentation is updated
- [ ] Commit messages follow convention
- [ ] No secrets or credentials in code

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Your Name**
- GitHub: [@yourusername](https://github.com/yourusername)
- Email: your.email@example.com
- LinkedIn: [Your LinkedIn](https://linkedin.com/in/yourprofile)

## 🙏 Acknowledgments

- [FastAPI Documentation](https://fastapi.tiangolo.com/) - Excellent framework documentation
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/) - Great ORM with type safety
- [Alembic Documentation](https://alembic.sqlalchemy.org/) - Database migration tool
- [PostgreSQL Documentation](https://www.postgresql.org/docs/) - Robust database system

## 📞 Support

If you have any questions or need help, please:
- Open an issue on GitHub
- Check existing issues for solutions
- Review the FastAPI documentation
- Contact the maintainer

---

<div align="center">

**⭐ If you find this project helpful, please consider giving it a star! ⭐**

Made with ❤️ using FastAPI and SQLModel

</div>