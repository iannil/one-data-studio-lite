# Development Guide

Guide for setting up development environment and contributing to Smart Data Platform.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git
- Make (optional)

## Setup Development Environment

### 1. Clone Repository

```bash
git clone https://github.com/one-data-studio/smart-data-platform.git
cd smart-data-platform
```

### 2. Backend Setup

```bash
cd apps/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup pre-commit hooks
pre-commit install

# Run database migrations
alembic upgrade head

# Create development database
python scripts/init_dev_db.py

# Run development server
uvicorn app.main:app --reload --port 8000
```

Backend will be available at http://localhost:8000
API docs at http://localhost:8000/docs

### 3. Frontend Setup

```bash
cd apps/frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local

# Run development server
npm run dev
```

Frontend will be available at http://localhost:3000

### 4. Start Supporting Services

```bash
# Start all services
docker-compose up -d postgres redis minio rabbitmq

# Or start everything including MLflow, Jupyter, etc.
docker-compose up -d
```

## Development Workflow

### Backend Development

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes and test**
   ```bash
   # Run tests
   pytest tests/

   # Run with coverage
   pytest --cov=app tests/

   # Format code
   black app/
   isort app/

   # Lint code
   flake8 app/
   mypy app/
   ```

3. **Database migrations**
   ```bash
   # Create migration
   alembic revision --autogenerate -m "description"

   # Apply migration
   alembic upgrade head

   # Rollback migration
   alembic downgrade -1
   ```

### Frontend Development

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes and test**
   ```bash
   # Run tests
   npm test

   # Run E2E tests
   npm run test:e2e

   # Lint code
   npm run lint

   # Format code
   npm run format
   ```

3. **Build for production**
   ```bash
   npm run build
   npm run start
   ```

## Code Structure

### Backend Structure

```
apps/backend/
├── app/
│   ├── api/              # API endpoints
│   │   └── v1/           # API version 1
│   │       ├── auth.py
│   │       ├── sources.py
│   │       ├── etl.py
│   │       ├── experiments.py
│   │       ├── models.py
│   │       └── ...
│   ├── core/             # Core functionality
│   │   ├── config.py     # Configuration
│   │   ├── security.py   # Auth/security
│   │   ├── database.py   # Database setup
│   │   └── cache.py      # Cache layer
│   ├── models/           # SQLAlchemy models
│   │   ├── user.py
│   │   ├── source.py
│   │   └── ...
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   │   ├── auth/         # Auth services
│   │   ├── etl/          # ETL services
│   │   ├── llm/          # LLM services
│   │   ├── billing/      # Billing services
│   │   └── ...
│   └── main.py           # FastAPI app
├── tests/                # Tests
│   ├── api/              # API tests
│   ├── services/         # Service tests
│   └── conftest.py       # Test fixtures
└── requirements.txt      # Dependencies
```

### Frontend Structure

```
apps/frontend/
├── src/
│   ├── app/              # Next.js app directory
│   │   ├── layout.tsx    # Root layout
│   │   ├── page.tsx      # Home page
│   │   └── (pages)/      # Route groups
│   ├── components/       # Reusable components
│   │   ├── MainLayout.tsx
│   │   ├── ...
│   │   └── ui/           # UI components
│   ├── pages/            # Page components
│   │   ├── login.tsx
│   │   ├── sources/
│   │   ├── experiments/
│   │   └── ...
│   ├── stores/           # Zustand state
│   │   ├── auth.ts
│   │   ├── llm.ts
│   │   └── ...
│   ├── lib/              # Utilities
│   │   ├── api.ts        # API client
│   │   └── ...
│   └── styles/           # Global styles
├── public/               # Static files
└── package.json          # Dependencies
```

## Testing

### Backend Testing

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# With coverage
pytest --cov=app --cov-report=html

# Specific test
pytest tests/test_auth.py::test_login

# Run with markers
pytest -m "not slow"
```

### Frontend Testing

```bash
# Unit tests
npm test

# Watch mode
npm test -- --watch

# Coverage
npm test -- --coverage

# E2E tests
npm run test:e2e
```

## Debugging

### Backend Debugging

```bash
# Using Python debugger
python -m pdb app/main.py

# Using IPython debugger
pip install ipdb
export PYTHONBREAKPOINT=ipdb.set_trace

# VS Code debugging
# Create .vscode/launch.json:
{
  "name": "Python: FastAPI",
  "type": "python",
  "request": "launch",
  "module": "uvicorn",
  "args": ["app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
  "console": "integratedTerminal"
}
```

### Frontend Debugging

```bash
# Next.js includes debugging out of the box
# Use Chrome DevTools or VS Code debugger

# VS Code debugging:
# Create .vscode/launch.json:
{
  "name": "Next.js: debug server-side",
  "type": "node-terminal",
  "request": "launch",
  "command": "npm run dev"
}

{
  "name": "Next.js: debug client-side",
  "type": "chrome",
  "request": "launch",
  "url": "http://localhost:3000"
}
```

## Common Tasks

### Adding a New API Endpoint

1. Create Pydantic schemas in `app/schemas/`
2. Create route handler in `app/api/v1/`
3. Add to router in `app/api/v1/router.py`
4. Add tests in `tests/api/`

### Adding a New Frontend Page

1. Create page in `src/pages/`
2. Add route to menu in `src/components/MainLayout.tsx`
3. Create Zustand store if needed in `src/stores/`
4. Add tests in `__tests__/`

### Adding a New Service

1. Create service in `app/services/`
2. Define models in `app/models/` if needed
3. Wire up in API layer
4. Add tests

## Database Operations

### Seeding Data

```bash
# Seed development data
python scripts/seed_dev_data.py

# Seed specific data
python scripts/seed_examples.py --models --experiments
```

### Resetting Database

```bash
# Drop and recreate
dropdb smart_data && createdb smart_data
alembic upgrade head

# Or using Docker
docker-compose exec postgres psql -U postgres -c "DROP DATABASE smart_data;"
docker-compose exec postgres psql -U postgres -c "CREATE DATABASE smart_data;"
alembic upgrade head
```

## Performance Profiling

### Backend Profiling

```bash
# Profile with cProfile
python -m cProfile -o profile.stats app/main.py

# Visualize with snakeviz
pip install snakeviz
snakeviz profile.stats
```

### Frontend Performance

```bash
# Analyze bundle size
npm run build -- --analyze

# Lighthouse CI
npm run lighthouse
```

## Contributing Guidelines

### Commit Messages

Follow conventional commits:

```
feat: add user authentication
fix: resolve database connection timeout
docs: update API documentation
test: add tests for ETL service
refactor: simplify payment processing
```

### Pull Request Process

1. Update documentation
2. Add tests for new features
3. Ensure all tests pass
4. Update CHANGELOG.md
5. Submit PR with description

### Code Review Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Follows style guide
- [ ] No security issues
- [ ] Performance considered

## Troubleshooting

### Common Issues

**Backend won't start**
```bash
# Check port availability
lsof -i :8000

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
```

**Frontend build fails**
```bash
# Clear cache and reinstall
rm -rf .next node_modules
npm install
```

**Database connection issues**
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# View logs
docker-compose logs postgres
```

## Resources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Next.js Docs](https://nextjs.org/docs)
- [Ant Design](https://ant.design/)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [Zustand](https://github.com/pmndrs/zustand)
