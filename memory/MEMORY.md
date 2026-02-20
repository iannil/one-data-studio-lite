# Smart Data Platform - Long-Term Memory

Last Updated: 2026-02-19

## Project Overview

**Smart Data Platform** is an enterprise-level intelligent data management platform implementing:
- FastAPI backend + Next.js 14 frontend
- 15+ ETL transformation steps using pandas
- AI-powered analysis (OpenAI integration)
- Data lineage tracking and visualization
- Apache Superset BI integration
- Comprehensive security and audit logging
- Full observability and monitoring
- ML-based data analysis capabilities

## Architecture

### Backend Stack
- **Framework**: FastAPI with SQLAlchemy 2.0
- **Database**: PostgreSQL 15 (main), MySQL 8.0 (test)
- **Cache/Queue**: Redis 7 + Celery
- **Storage**: MinIO (S3-compatible)
- **BI**: Apache Superset
- **AI/ML**: OpenAI API + scikit-learn

### Frontend Stack
- **Framework**: Next.js 14 with App Router
- **UI**: Ant Design 5
- **State**: Zustand
- **Visualization**: AntV G6 (lineage), ChartRenderer

### Key Services
- `MetadataEngine`: Scans data sources, extracts metadata
- `ETLEngine`: Pandas-based data transformation pipeline
- `AIService`: NL2SQL, field analysis, cleaning suggestions, ML-based forecasting
- `BIService`: Superset integration
- `QualityService`: Data quality scoring and issue detection
- `AssetService`: Data asset cataloging and value tracking
- `LineageService`: Upstream/downstream dependency tracking
- `ReportService`: Scheduled report generation with Celery
- `TimeSeriesForecaster`: Statistical time series forecasting
- `AnomalyDetector`: ML-based anomaly detection (Isolation Forest)
- `EnhancedClustering`: KMeans and DBSCAN clustering

### Infrastructure Components
- `LifecycleTracker`: Decorator for full-lifecycle observability
- `TraceContext`: Distributed trace propagation
- `RateLimiter`: Token bucket rate limiting middleware
- `InputValidationMiddleware`: SQL injection, XSS, path traversal detection
- `SecurityHeadersMiddleware`: HSTS, CSP, X-Frame-Options headers

## Coding Standards

1. **Type Safety**: All code uses type hints
2. **Async/Await**: All database operations are async
3. **Observability**: All service methods use `@LifecycleTracker` decorator
4. **Immutability**: Never mutate function arguments, return new objects
5. **Error Handling**: Comprehensive try/except with meaningful error messages
6. **Testing**: Target 80%+ coverage, TDD approach for new features

## Project Structure

```
smart-data-platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API endpoints
│   │   ├── core/            # Config, database, observability
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   ├── connectors/      # Data source connectors
│   │   └── middleware/      # Rate limiting, validation, audit
│   └── tests/               # Pytest tests
├── frontend/
│   └── src/
│       ├── components/      # React components
│       ├── pages/           # Next.js pages
│       ├── services/        # API client
│       └── stores/          # Zustand state
├── docker-compose.ops.yml   # Production/Operations containers
└── memory/                  # AI agent memory system
```

## API Endpoint Patterns

- **GET**: Read operations (list, get)
- **POST**: Create operations, triggers (run, scan, export)
- **PATCH/PUT**: Update operations
- **DELETE**: Delete operations

All endpoints require JWT authentication except `/auth/*`.

## Common Issues & Solutions

### Issue: "asyncpg not found" when running tests locally
**Solution**: Tests must run in Docker environment. Use `docker compose -f docker-compose.ops.yml run backend pytest`

### Issue: Database connection timeout
**Solution**: Check PostgreSQL health status, ensure network is `smart-data-network`

### Issue: Superset sync fails
**Solution**: Verify Superset credentials in config, check database URL format

### Issue: ETL pipeline fails silently
**Solution**: Check `step_metrics` in response, enable observability logging to trace execution

## Current Development Status

### Phase 3 Completed (2026-02-19) ✅
- ✅ Full observability logging system (`app/core/observability.py`)
- ✅ Rate limiting middleware (token bucket algorithm)
- ✅ Input validation and security headers middleware
- ✅ Data quality service with scoring and issue detection
- ✅ Enhanced data export functionality (CSV, Excel, JSON, Parquet)
- ✅ Comprehensive API documentation with OpenAPI
- ✅ Memory tracking system for AI agents
- ✅ ML utilities (TimeSeriesForecaster, AnomalyDetector, EnhancedClustering)
- ✅ Report service with scheduled report generation
- ✅ Production Docker configuration with resource limits

### Phase 4 In Progress 🔄
- 🔄 CI/CD pipeline setup
- 🔄 Additional ETL step types
- 🔄 Frontend UI enhancements for new features
- 🔄 Integration test coverage expansion

### Known Issues
- ⚠️ ML utils classes not exported in services/__init__.py
- ⚠️ Missing tests for ml_utils.py
- ⚠️ Scheduler system needs consolidation (APScheduler vs Celery)
- ⚠️ SQL security validator should be extracted to core/security.py

## Port Configuration

Production Operations Environment:
- Backend API: 5500
- Frontend: 5501
- PostgreSQL: 5502
- Redis: 5503
- MinIO API: 5504
- MinIO Console: 5505
- Superset: 5506
- MySQL: 5510

## Deployment Commands

```bash
# Start all services
docker compose -f docker-compose.ops.yml up -d

# View logs
docker compose -f docker-compose.ops.yml logs -f backend

# Restart specific service
docker compose -f docker-compose.ops.yml restart backend

# Stop all services
docker compose -f docker-compose.ops.yml down
```

## User Preferences (To be discovered)
- [ ] Add user-specific preferences as they are learned
