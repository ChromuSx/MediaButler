"""
Application-wide constants for MediaButler

This module centralizes all magic numbers and configuration constants
to improve code maintainability and readability.
"""

# =============================================================================
# RETRY CONFIGURATION
# =============================================================================

# Default retry attempts for network operations
DEFAULT_RETRY_ATTEMPTS = 3

# Retry delay in seconds
DEFAULT_RETRY_DELAY = 1.0

# Retry delay for downloads (longer for large transfers)
DOWNLOAD_RETRY_DELAY = 2.0

# Exponential backoff multiplier
DEFAULT_BACKOFF_MULTIPLIER = 2.0


# =============================================================================
# TIMEOUT CONFIGURATION
# =============================================================================

# API request timeout in seconds
API_REQUEST_TIMEOUT = 5.0

# File hash calculation timeout
FILE_HASH_TIMEOUT = 30.0

# Download progress update interval in seconds
DOWNLOAD_PROGRESS_UPDATE_INTERVAL = 2.0


# =============================================================================
# RATE LIMITING
# =============================================================================

# TMDB API rate limits (official limits: 40 requests per 10 seconds)
TMDB_RATE_LIMIT_CALLS = 40
TMDB_RATE_LIMIT_PERIOD = 10  # seconds

# WebSocket ping interval (keep-alive)
WEBSOCKET_PING_INTERVAL = 30  # seconds

# API rate limits per minute
API_RATE_LIMIT_LOGIN = "5/minute"  # Strict for brute-force prevention
API_RATE_LIMIT_STATS = "30/minute"
API_RATE_LIMIT_HEALTH = "60/minute"


# =============================================================================
# FILE OPERATIONS
# =============================================================================

# Chunk size for file hashing (4KB)
FILE_HASH_CHUNK_SIZE = 4096

# Maximum filename length
MAX_FILENAME_LENGTH = 200

# File hash algorithms
HASH_ALGORITHM_MD5 = "md5"
HASH_ALGORITHM_SHA1 = "sha1"
HASH_ALGORITHM_SHA256 = "sha256"


# =============================================================================
# DATABASE
# =============================================================================

# TMDB cache expiration in days
TMDB_CACHE_EXPIRATION_DAYS = 90

# Default cache cleanup days (more aggressive)
TMDB_CACHE_CLEANUP_DAYS = 30

# Database connection pool size
DB_POOL_MIN_SIZE = 5
DB_POOL_MAX_SIZE = 20


# =============================================================================
# DOWNLOAD CONFIGURATION
# =============================================================================

# Default concurrent downloads
DEFAULT_CONCURRENT_DOWNLOADS = 3

# Minimum free space in GB
DEFAULT_MIN_FREE_SPACE_GB = 5.0

# Low space warning threshold in GB
DEFAULT_WARNING_THRESHOLD_GB = 10.0

# Space check interval in seconds
DEFAULT_SPACE_CHECK_INTERVAL = 30

# Maximum file size in GB
DEFAULT_MAX_FILE_SIZE_GB = 10.0


# =============================================================================
# TMDB CONFIGURATION
# =============================================================================

# Auto-confirm threshold (confidence percentage)
DEFAULT_AUTO_CONFIRM_THRESHOLD = 70

# High confidence score for series detection
HIGH_CONFIDENCE_SCORE = 90

# Medium confidence score
MEDIUM_CONFIDENCE_SCORE = 70

# Low confidence score
LOW_CONFIDENCE_SCORE = 50


# =============================================================================
# VALIDATION
# =============================================================================

# Minimum file size in bytes (1 KB)
MIN_FILE_SIZE_BYTES = 1024

# Similarity threshold for folder matching
DEFAULT_SIMILARITY_THRESHOLD = 0.7


# =============================================================================
# JWT & AUTHENTICATION
# =============================================================================

# JWT token expiration in minutes (30 days default)
DEFAULT_JWT_EXPIRE_MINUTES = 43200

# JWT secret key minimum length
JWT_SECRET_MIN_LENGTH = 32


# =============================================================================
# TEXT FORMATTING
# =============================================================================

# Default text truncation length
DEFAULT_TRUNCATE_LENGTH = 100

# Default truncation suffix
DEFAULT_TRUNCATE_SUFFIX = "..."


# =============================================================================
# LOGGING
# =============================================================================

# Log level
LOG_LEVEL = "INFO"

# Log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
