# ALX Project Nexus - Test Suite

This directory contains comprehensive tests for the ALX Project Nexus online poll system.

## Test Structure

- `test_models.py` - Model unit tests
- `test_views.py` - View and template tests  
- `test_api.py` - REST API endpoint tests
- `test_performance.py` - Performance and load tests
- `__init__.py` - Test configuration

## Running Tests

### All Tests
```bash
cd backend
python manage.py test ../tests/
```

### Specific Test Files
```bash
python manage.py test tests.test_models
python manage.py test tests.test_views
python manage.py test tests.test_api
python manage.py test tests.test_performance
```

### With Coverage
```bash
pip install coverage
coverage run --source='.' manage.py test ../tests/
coverage report
coverage html
```

## Test Categories

### Model Tests (`test_models.py`)
- Poll model creation and validation
- PollOption model relationships
- Vote model constraints and uniqueness
- Model string representations
- Cascade deletion behavior

### View Tests (`test_views.py`)
- Template rendering
- Authentication requirements
- Form submission handling
- Error handling
- Security features (CSRF, XSS)

### API Tests (`test_api.py`)
- REST endpoint functionality
- Authentication and authorization
- Data validation
- Rate limiting
- JWT token handling

### Performance Tests (`test_performance.py`)
- Query optimization
- Concurrent operations
- Memory usage patterns
- Caching effectiveness
- Bulk operations

## Test Data

Tests use isolated test databases and create their own test data. No production data is affected.

## Continuous Integration

These tests are automatically run in our CI/CD pipeline on every commit and pull request.

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Maintain test coverage above 90%
4. Follow naming conventions
