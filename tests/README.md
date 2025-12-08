# MediaButler Test Suite

Comprehensive test suite for MediaButler with unit and integration tests.

## Quick Start

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
# Run all tests with coverage
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=core --cov=utils --cov=handlers --cov-report=html
```

### Run Specific Test Categories

```bash
# Run only unit tests (fast)
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only security tests
pytest -m security

# Run only API tests
pytest -m api
```

### Run Specific Test Files

```bash
# Test naming utilities
pytest tests/unit/test_naming.py

# Test helpers and validation
pytest tests/unit/test_helpers.py

# Run with specific test function
pytest tests/unit/test_naming.py::TestSanitizeFilename::test_remove_invalid_characters
```

## Test Structure

```
tests/
├── README.md                    # This file
├── conftest.py                  # Shared fixtures and configuration
├── unit/                        # Unit tests (fast, isolated)
│   ├── test_naming.py          # File name parsing and pattern matching
│   ├── test_helpers.py         # Validation, retry logic, utilities
│   ├── test_space_manager.py   # Disk space management
│   └── test_database.py        # Database operations
└── integration/                 # Integration tests (slower)
    └── test_download_flow.py   # Complete download workflow
```

## Test Coverage

Current test coverage focuses on:

### Unit Tests

#### `test_naming.py` - File Name Parsing
- ✅ Filename sanitization and validation
- ✅ TV series pattern matching (13+ patterns)
- ✅ Fuzzy folder matching
- ✅ Similarity calculations
- ✅ Security: Path traversal prevention
- ✅ Edge cases: Long filenames, unicode, special characters

**Key Test Classes:**
- `TestSanitizeFilename` - Filename cleaning and validation
- `TestExtractSeriesInfo` - TV show detection with confidence scoring
- `TestNormalizeForComparison` - Text normalization for fuzzy matching
- `TestCalculateSimilarity` - String similarity algorithms
- `TestFindSimilarFolder` - Existing folder detection
- `TestSecuritySanitization` - Security-focused validation

#### `test_helpers.py` - Utilities and Validation
- ✅ Telegram ID validation
- ✅ Path sanitization
- ✅ File size validation
- ✅ **Security: User path validation (path traversal prevention)**
- ✅ File hashing (MD5, SHA256)
- ✅ Video file detection
- ✅ Safe file operations
- ✅ Async retry logic
- ✅ Human-readable size formatting

**Key Test Classes:**
- `TestValidationHelpers` - Input validation functions
- `TestValidateUserPath` - Path traversal security validation
- `TestFileHelpers` - File operation utilities
- `TestRetryHelpers` - Retry logic with exponential backoff
- `TestUtilityFunctions` - Formatting and text utilities

### Integration Tests (Planned)

#### `test_download_flow.py`
- Download queue management
- Space-aware download system
- TMDB integration
- Subtitle download
- Database persistence

## Test Markers

Tests are organized with pytest markers:

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Integration tests with external dependencies
- `@pytest.mark.security` - Security-focused tests (path traversal, injection, etc.)
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.slow` - Slow-running tests

## Fixtures

Common fixtures available in `conftest.py`:

### Path Fixtures
- `temp_dir` - Temporary directory (auto-cleaned)
- `test_paths` - PathsConfig with temp directories

### Config Fixtures
- `test_limits` - LimitsConfig for testing
- `test_tmdb_config` - TMDB configuration
- `test_auth_config` - Auth configuration

### Service Fixtures
- `test_database` - SQLite database (temp)
- `space_manager` - SpaceManager instance
- `mock_telegram_client` - Mocked Telethon client
- `mock_tmdb_client` - Mocked TMDB API client

### Sample Data Fixtures
- `sample_video_file` - Fake video file
- `sample_movie_name` - Movie filename
- `sample_tv_name` - TV show filename
- `sample_download_data` - Download metadata
- `sample_user_data` - User information

## Configuration

Test configuration is in `pytest.ini`:

```ini
[pytest]
# Coverage minimum threshold
--cov-fail-under=50

# Test discovery patterns
python_files = test_*.py *_test.py

# Async support
asyncio_mode = auto
```

## Coverage Reports

After running tests with coverage:

```bash
# Generate HTML coverage report
pytest --cov=core --cov=utils --cov-report=html

# Open in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

Coverage reports show:
- Line-by-line coverage
- Missing lines
- Branch coverage
- Overall percentage

## Writing New Tests

### Test Naming Convention

```python
# Test file: test_<module_name>.py
# Test class: Test<FeatureName>
# Test function: test_<what_it_tests>

class TestMyFeature:
    def test_valid_input_returns_success(self):
        # Arrange
        input_data = "test"

        # Act
        result = my_function(input_data)

        # Assert
        assert result == "expected"
```

### Use Descriptive Names

```python
# ❌ Bad
def test_fn():
    assert parse("test") == True

# ✅ Good
def test_parse_tv_series_detects_s01e01_format(self):
    filename = "Show.S01E01.Episode.mp4"
    info = parse_series(filename)
    assert info.season == 1
    assert info.episode == 1
```

### Test One Thing

```python
# ❌ Bad - tests multiple things
def test_parser():
    assert parse_movie("film.mp4") == "film"
    assert parse_tv("show.s01e01.mp4") == ("show", 1, 1)
    assert sanitize("bad<>name") == "badname"

# ✅ Good - separate tests
def test_parse_movie_extracts_title():
    assert parse_movie("film.mp4") == "film"

def test_parse_tv_extracts_season_and_episode():
    assert parse_tv("show.s01e01.mp4") == ("show", 1, 1)

def test_sanitize_removes_invalid_characters():
    assert sanitize("bad<>name") == "badname"
```

### Use Fixtures for Setup

```python
# ❌ Bad - repetitive setup
def test_function_a():
    db = DatabaseManager("test.db")
    db.connect()
    # test...
    db.close()

def test_function_b():
    db = DatabaseManager("test.db")
    db.connect()
    # test...
    db.close()

# ✅ Good - use fixture
@pytest.fixture
async def test_db():
    db = DatabaseManager("test.db")
    await db.connect()
    yield db
    await db.close()

async def test_function_a(test_db):
    # test with test_db...

async def test_function_b(test_db):
    # test with test_db...
```

## Security Testing

Security-critical tests are marked with `@pytest.mark.security`:

```python
@pytest.mark.security
class TestPathValidation:
    def test_prevent_path_traversal(self):
        """Ensure ../ attacks are blocked"""
        result = validate_path("../../etc/passwd")
        assert result is False
```

Run security tests:

```bash
pytest -m security -v
```

## Continuous Integration

Tests run automatically on:
- Every push to main branch
- Every pull request
- Scheduled daily runs

See `.github/workflows/ci.yml` for CI configuration.

## Troubleshooting

### Import Errors

If you see import errors:

```bash
# Ensure you're in project root
cd /path/to/MediaButler

# Install in development mode
pip install -e .
```

### Async Tests Fail

Ensure `pytest-asyncio` is installed:

```bash
pip install pytest-asyncio
```

### Coverage Too Low

Check which files are missing coverage:

```bash
pytest --cov=core --cov=utils --cov-report=term-missing
```

Add tests for uncovered lines.

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure tests pass: `pytest tests/`
3. Check coverage: `pytest --cov`
4. Run security tests: `pytest -m security`
5. Update this README if adding new test categories

## Target Coverage Goals

- **Unit Tests**: 70%+ coverage
- **Critical Modules** (auth, security): 90%+ coverage
- **Integration Tests**: Key workflows covered

---

**Last Updated**: 2025-12-07
**Test Framework**: pytest 7.4.3
**Coverage Tool**: pytest-cov 4.1.0
