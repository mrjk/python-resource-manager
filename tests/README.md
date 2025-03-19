# Resource Manager Tests

This directory contains a comprehensive test suite for the Resource Manager library using pytest.

## Test Categories

The tests are organized into several categories:

1. **Unit Tests** - Test individual functions, methods, and classes in isolation
   - `test_resources.py` - Tests for the `Resource` and `ResourceManager` classes
   - `test_links.py` - Tests for resource link functionality
   - `test_resolver.py` - Tests for dependency resolution

2. **Integration Tests** - Test how components work together
   - `test_integration.py` - End-to-end workflow tests

3. **Property-based Tests** - Generate random inputs to find edge cases
   - `test_property_based.py` - Tests using Hypothesis for property-based testing

4. **Performance Tests** - Verify code performs within acceptable limits
   - `test_performance.py` - Benchmarks for critical operations

5. **Exception Tests** - Verify proper error handling
   - `test_exceptions.py` - Tests for error cases and exceptions

## Running the Tests

### Prerequisites

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Running All Tests

From the project root directory:

```bash
python -m pytest resource_manager_tests
```

### Running Specific Test Categories

Unit tests only:
```bash
python -m pytest resource_manager_tests -m unit
```

Integration tests only:
```bash
python -m pytest resource_manager_tests -m integration
```

Performance benchmarks:
```bash
python -m pytest resource_manager_tests -m benchmark
```

### Coverage Reports

The test configuration generates coverage reports in several formats:

- Terminal output with missing lines
- HTML report (in `htmlcov/` directory)
- XML report (in `coverage.xml` file)

View the HTML report by opening `htmlcov/index.html` in a web browser.

## Test Organization

- `conftest.py` - Common test fixtures and utilities
- `pytest.ini` - Pytest configuration
- `fixtures/` - Test data and additional fixtures

## Adding New Tests

When adding new tests:

1. Follow the naming convention: `test_*.py` for files and `test_*` for functions
2. Use appropriate markers for test categorization
3. Leverage existing fixtures from `conftest.py` where possible
4. Maintain high test coverage (aim for 80%+) 