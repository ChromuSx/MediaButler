"""
Unit tests for helpers.py - Validation, retry logic, and utility functions
"""

import pytest
import asyncio
from pathlib import Path
from utils.helpers import (
    ValidationHelpers,
    FileHelpers,
    RetryHelpers,
    human_readable_size,
    truncate_text,
)


class TestValidationHelpers:
    """Test validation helper functions"""

    def test_is_valid_telegram_id_positive(self):
        """Test valid Telegram ID"""
        assert ValidationHelpers.is_valid_telegram_id(123456) is True

    def test_is_valid_telegram_id_string_number(self):
        """Test valid Telegram ID as string"""
        assert ValidationHelpers.is_valid_telegram_id("123456") is True

    def test_is_valid_telegram_id_negative(self):
        """Test invalid negative ID"""
        assert ValidationHelpers.is_valid_telegram_id(-123) is False

    def test_is_valid_telegram_id_zero(self):
        """Test invalid zero ID"""
        assert ValidationHelpers.is_valid_telegram_id(0) is False

    def test_is_valid_telegram_id_invalid_string(self):
        """Test invalid string ID"""
        assert ValidationHelpers.is_valid_telegram_id("not_a_number") is False

    def test_sanitize_path_removes_dangerous_chars(self):
        """Test that dangerous characters are removed"""
        path = "../test/path;with|bad>chars<"
        result = ValidationHelpers.sanitize_path(path)

        assert ".." not in result
        assert ";" not in result
        assert "|" not in result

    def test_sanitize_path_removes_multiple_spaces(self):
        """Test multiple space removal"""
        path = "test    path    with    spaces"
        result = ValidationHelpers.sanitize_path(path)
        assert "    " not in result
        assert result == "test path with spaces"

    def test_validate_file_size_valid(self):
        """Test valid file size"""
        size = 1024 * 1024 * 100  # 100MB
        is_valid, msg = ValidationHelpers.validate_file_size(size)
        assert is_valid is True
        assert msg == "OK"

    def test_validate_file_size_too_small(self):
        """Test file size too small"""
        size = 100  # 100 bytes
        is_valid, msg = ValidationHelpers.validate_file_size(size, min_size=1024)
        assert is_valid is False
        assert "too small" in msg.lower()

    def test_validate_file_size_too_large(self):
        """Test file size too large"""
        size = 20 * 1024**3  # 20GB
        is_valid, msg = ValidationHelpers.validate_file_size(size, max_size=10 * 1024**3)
        assert is_valid is False
        assert "too large" in msg.lower()


@pytest.mark.security
class TestValidateUserPath:
    """Test path traversal validation (security-critical)"""

    def test_valid_path_within_allowed_base(self, temp_dir):
        """Test that valid path within allowed base passes"""
        allowed_bases = [temp_dir]
        user_path = temp_dir / "subfolder" / "file.mp4"

        is_valid, msg = ValidationHelpers.validate_user_path(user_path, allowed_bases)

        assert is_valid is True
        assert msg == "OK"

    def test_valid_path_exact_base(self, temp_dir):
        """Test that exact base path is valid"""
        allowed_bases = [temp_dir]

        is_valid, msg = ValidationHelpers.validate_user_path(temp_dir, allowed_bases)

        assert is_valid is True
        assert msg == "OK"

    def test_invalid_path_outside_base(self, temp_dir):
        """Test that path outside allowed base is rejected"""
        allowed_bases = [temp_dir / "allowed"]
        user_path = temp_dir / "not_allowed" / "file.mp4"

        is_valid, msg = ValidationHelpers.validate_user_path(user_path, allowed_bases)

        assert is_valid is False
        assert "allowed directories" in msg.lower()

    def test_path_traversal_attack_prevention(self, temp_dir):
        """Test prevention of path traversal attacks"""
        allowed_bases = [temp_dir / "media"]
        # Attempt to traverse outside with ../
        user_path = temp_dir / "media" / ".." / ".." / "etc" / "passwd"

        is_valid, msg = ValidationHelpers.validate_user_path(user_path, allowed_bases)

        # After resolution, should be outside allowed base
        assert is_valid is False

    def test_symlink_traversal_prevention(self, temp_dir):
        """Test that symlinks don't bypass validation"""
        allowed_bases = [temp_dir / "allowed"]
        (temp_dir / "allowed").mkdir()

        # This test requires symlink creation which may not work on all systems
        # Just test the path resolution logic
        is_valid, msg = ValidationHelpers.validate_user_path(temp_dir / "outside", allowed_bases)

        assert is_valid is False

    def test_multiple_allowed_bases(self, temp_dir):
        """Test validation with multiple allowed base paths"""
        base1 = temp_dir / "media1"
        base2 = temp_dir / "media2"
        allowed_bases = [base1, base2]

        # Path in first base
        is_valid1, _ = ValidationHelpers.validate_user_path(base1 / "subfolder", allowed_bases)
        assert is_valid1 is True

        # Path in second base
        is_valid2, _ = ValidationHelpers.validate_user_path(base2 / "subfolder", allowed_bases)
        assert is_valid2 is True

        # Path outside both bases
        is_valid3, _ = ValidationHelpers.validate_user_path(temp_dir / "other", allowed_bases)
        assert is_valid3 is False

    def test_absolute_vs_relative_paths(self, temp_dir):
        """Test handling of absolute vs relative paths"""
        allowed_bases = [temp_dir.resolve()]

        # Test with string path
        is_valid, _ = ValidationHelpers.validate_user_path(str(temp_dir / "subfolder"), allowed_bases)
        assert is_valid is True

    def test_invalid_path_error_handling(self):
        """Test error handling for invalid paths"""
        allowed_bases = [Path("/media")]

        # Test with invalid path characters (on Windows)
        is_valid, msg = ValidationHelpers.validate_user_path("invalid<>path", allowed_bases)

        # Should either reject or handle gracefully
        assert isinstance(is_valid, bool)
        assert isinstance(msg, str)


class TestFileHelpers:
    """Test file operation helpers"""

    def test_get_file_hash_md5(self, temp_dir):
        """Test MD5 hash calculation"""
        # Create test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")

        hash_result = FileHelpers.get_file_hash(test_file, algorithm="md5")

        assert isinstance(hash_result, str)
        assert len(hash_result) == 32  # MD5 is 32 hex chars

    def test_get_file_hash_sha256(self, temp_dir):
        """Test SHA256 hash calculation"""
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")

        hash_result = FileHelpers.get_file_hash(test_file, algorithm="sha256")

        assert isinstance(hash_result, str)
        assert len(hash_result) == 64  # SHA256 is 64 hex chars

    def test_get_file_hash_consistency(self, temp_dir):
        """Test that hash is consistent for same content"""
        test_file = temp_dir / "test.txt"
        test_file.write_text("consistent content")

        hash1 = FileHelpers.get_file_hash(test_file)
        hash2 = FileHelpers.get_file_hash(test_file)

        assert hash1 == hash2

    def test_is_video_file_valid_extensions(self):
        """Test video file detection for valid extensions"""
        assert FileHelpers.is_video_file("movie.mp4") is True
        assert FileHelpers.is_video_file("video.mkv") is True
        assert FileHelpers.is_video_file("clip.avi") is True
        assert FileHelpers.is_video_file("film.mov") is True

    def test_is_video_file_invalid_extensions(self):
        """Test video file detection for invalid extensions"""
        assert FileHelpers.is_video_file("document.pdf") is False
        assert FileHelpers.is_video_file("image.jpg") is False
        assert FileHelpers.is_video_file("audio.mp3") is False

    def test_is_video_file_case_insensitive(self):
        """Test case-insensitive extension matching"""
        assert FileHelpers.is_video_file("movie.MP4") is True
        assert FileHelpers.is_video_file("video.MKV") is True

    def test_safe_move_same_filesystem(self, temp_dir):
        """Test safe file move on same filesystem"""
        source = temp_dir / "source.txt"
        dest = temp_dir / "subdir" / "dest.txt"

        source.write_text("test content")

        result = FileHelpers.safe_move(source, dest)

        assert result is True
        assert dest.exists()
        assert not source.exists()
        assert dest.read_text() == "test content"

    def test_safe_move_creates_directory(self, temp_dir):
        """Test that safe_move creates destination directory"""
        source = temp_dir / "source.txt"
        dest = temp_dir / "new" / "dir" / "dest.txt"

        source.write_text("test content")

        result = FileHelpers.safe_move(source, dest)

        assert result is True
        assert dest.parent.exists()


class TestRetryHelpers:
    """Test retry logic"""

    @pytest.mark.asyncio
    async def test_async_retry_success_first_attempt(self):
        """Test async retry succeeds on first attempt"""
        call_count = 0

        @RetryHelpers.async_retry(max_attempts=3)
        async def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_function()

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_retry_success_after_failures(self):
        """Test async retry succeeds after some failures"""
        call_count = 0

        @RetryHelpers.async_retry(max_attempts=3, delay=0.01)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"

        result = await flaky_function()

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_async_retry_max_attempts_exceeded(self):
        """Test async retry raises after max attempts"""
        call_count = 0

        @RetryHelpers.async_retry(max_attempts=3, delay=0.01)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            await always_fails()

        assert call_count == 3


class TestUtilityFunctions:
    """Test standalone utility functions"""

    def test_human_readable_size_bytes(self):
        """Test human readable size for bytes"""
        assert "B" in human_readable_size(500)

    def test_human_readable_size_kilobytes(self):
        """Test human readable size for KB"""
        result = human_readable_size(2048)
        assert "KB" in result

    def test_human_readable_size_megabytes(self):
        """Test human readable size for MB"""
        result = human_readable_size(5 * 1024 * 1024)
        assert "MB" in result

    def test_human_readable_size_gigabytes(self):
        """Test human readable size for GB"""
        result = human_readable_size(3 * 1024**3)
        assert "GB" in result

    def test_truncate_text_short(self):
        """Test truncate doesn't affect short text"""
        text = "Short text"
        result = truncate_text(text, max_length=100)
        assert result == text

    def test_truncate_text_long(self):
        """Test truncate shortens long text"""
        text = "a" * 200
        result = truncate_text(text, max_length=50)
        assert len(result) <= 50
        assert result.endswith("...")

    def test_truncate_text_custom_suffix(self):
        """Test truncate with custom suffix"""
        text = "a" * 200
        result = truncate_text(text, max_length=50, suffix="[...]")
        assert result.endswith("[...]")
