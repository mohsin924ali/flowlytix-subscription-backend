# 🚀 Flowlytix Subscription Server

A comprehensive subscription management and licensing server for Flowlytix, built with FastAPI and following clean architecture principles.

## 📋 Overview

This server provides:

- **Subscription Management**: Create, manage, and validate subscriptions
- **License Key Generation**: Secure license key generation and validation
- **Device Management**: Track and manage activated devices
- **JWT Token Validation**: Secure token-based authentication
- **Analytics Dashboard**: Comprehensive subscription analytics
- **Admin Panel**: Web interface for subscription management

## 🏗️ Architecture

The server follows **Clean Architecture** principles with:

- **Domain Layer**: Business entities and rules
- **Infrastructure Layer**: Database, external services, and persistence
- **API Layer**: REST endpoints and request/response handling
- **Service Layer**: Business logic and use cases

## 🛠️ Technology Stack

- **Python 3.11+** with type hints
- **FastAPI** with async/await
- **SQLAlchemy 2.0+** with async support
- **PostgreSQL** database
- **Redis** for caching
- **JWT** with RS256 for security
- **Alembic** for database migrations
- **Pytest** for testing
- **Docker** for containerization

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL
- Redis (optional, for caching)
- Git

### Installation

1. **Clone the repository**:

```bash
git clone <repository-url>
cd subscription-server
```

2. **Create virtual environment**:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:

```bash
pip install -r requirements/dev.txt
```

4. **Set up environment variables**:

```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Set up database**:

```bash
# Create database
createdb flowlytix_subscriptions

# Run migrations
alembic upgrade head
```

6. **Run the server**:

```bash
python main.py
```

The server will start at `http://localhost:8000`.

## 📝 Environment Configuration

Create a `.env` file in the root directory:

```env
# Application
APP_NAME=Flowlytix Subscription Server
DEBUG=true
ENVIRONMENT=development
VERSION=1.0.0

# Server
HOST=0.0.0.0
PORT=8000
RELOAD=true

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/flowlytix_subscriptions
DATABASE_ECHO=false

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# JWT Keys
PRIVATE_KEY_PATH=keys/private_key.pem
PUBLIC_KEY_PATH=keys/public_key.pem

# CORS
ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:8080"]

# Features
ENABLE_ANALYTICS=true
ENABLE_NOTIFICATIONS=true
ENABLE_DEVICE_TRACKING=true
```

## 🗄️ Database Setup

### Using Docker (Recommended)

```bash
# Start PostgreSQL and Redis
docker-compose up -d db redis

# Wait for services to start
sleep 10

# Run migrations
alembic upgrade head
```

### Manual Setup

1. **Install PostgreSQL**:

```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql
```

2. **Create database and user**:

```sql
CREATE USER flowlytix WITH PASSWORD 'your_password';
CREATE DATABASE flowlytix_subscriptions OWNER flowlytix;
GRANT ALL PRIVILEGES ON DATABASE flowlytix_subscriptions TO flowlytix;
```

3. **Run migrations**:

```bash
alembic upgrade head
```

## 🔑 API Endpoints

### Authentication

- `POST /api/v1/auth/login` - Admin login
- `POST /api/v1/auth/refresh` - Refresh token
- `POST /api/v1/auth/logout` - Logout

### Licensing

- `POST /api/v1/licensing/activate` - Activate license
- `POST /api/v1/licensing/validate` - Validate license
- `POST /api/v1/licensing/refresh` - Refresh license token
- `POST /api/v1/licensing/deactivate` - Deactivate device

### Subscriptions

- `GET /api/v1/subscriptions` - List subscriptions
- `POST /api/v1/subscriptions` - Create subscription
- `GET /api/v1/subscriptions/{id}` - Get subscription details
- `PUT /api/v1/subscriptions/{id}` - Update subscription
- `DELETE /api/v1/subscriptions/{id}` - Delete subscription

### Devices

- `GET /api/v1/devices` - List devices
- `GET /api/v1/devices/{id}` - Get device details
- `PUT /api/v1/devices/{id}` - Update device
- `DELETE /api/v1/devices/{id}` - Remove device

### Analytics

- `GET /api/v1/analytics/dashboard` - Dashboard metrics
- `GET /api/v1/analytics/subscriptions` - Subscription analytics
- `GET /api/v1/analytics/devices` - Device analytics

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest app/tests/test_subscriptions.py

# Run integration tests
pytest app/tests/integration/
```

### Test Categories

- **Unit Tests**: Test individual components
- **Integration Tests**: Test API endpoints
- **E2E Tests**: Test complete workflows

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

### Metrics

```bash
curl http://localhost:8000/metrics
```

### Logs

Structured logging with JSON format:

```bash
# View logs
tail -f logs/app.log

# Search logs
grep "ERROR" logs/app.log
```

## 🔧 Development

### Code Quality

```bash
# Format code
black app/
ruff app/

# Type checking
mypy app/

# Pre-commit hooks
pre-commit run --all-files
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## 📦 Docker Deployment

### Build Image

```bash
docker build -t flowlytix-subscription-server .
```

### Run with Docker Compose

```bash
docker-compose up -d
```

### Environment Variables

Set these in your production environment:

```env
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/flowlytix_subscriptions
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-production-secret-key
SENTRY_DSN=your-sentry-dsn
```

## 🔒 Security

### Key Management

RSA keys are automatically generated on first run:

- Private key: `keys/private_key.pem` (600 permissions)
- Public key: `keys/public_key.pem` (644 permissions)

### Security Headers

Automatic security headers:

- Content Security Policy
- X-Frame-Options
- X-Content-Type-Options
- HSTS (HTTPS only)

### Rate Limiting

- 100 requests per minute per IP
- Configurable limits
- Retry-After headers

## 📋 API Documentation

### Interactive Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### Authentication

All protected endpoints require JWT token in header:

```
Authorization: Bearer <token>
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run quality checks
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 📞 Support

For support, please contact:

- Email: team@flowlytix.com
- Documentation: [Link to docs]
- Issues: [Link to issues]

## 🚀 Production Checklist

Before deploying to production:

- [ ] Set `ENVIRONMENT=production`
- [ ] Configure secure `SECRET_KEY`
- [ ] Set up SSL/TLS certificates
- [ ] Configure database backups
- [ ] Set up monitoring and alerting
- [ ] Configure log aggregation
- [ ] Set up reverse proxy (Nginx)
- [ ] Configure firewall rules
- [ ] Set up health checks
- [ ] Configure auto-scaling
- [ ] Set up CI/CD pipeline
- [ ] Security audit and penetration testing
