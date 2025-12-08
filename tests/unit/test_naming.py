"""
Unit tests for naming.py - File name parsing and pattern matching
"""
import pytest
from pathlib import Path
from utils.naming import FileNameParser


class TestSanitizeFilename:
    """Test filename sanitization"""

    def test_remove_invalid_characters(self):
        """Test removal of invalid characters"""
        filename = 'test<>:"|?*file.mp4'
        result = FileNameParser.sanitize_filename(filename)
        assert result == 'testfile.mp4'

    def test_clean_multiple_dots(self):
        """Test cleaning of multiple dots"""
        filename = 'test...file...mp4'
        result = FileNameParser.sanitize_filename(filename)
        assert result == 'test.file.mp4'

    def test_clean_multiple_spaces(self):
        """Test cleaning of multiple spaces"""
        filename = 'test    file    name.mp4'
        result = FileNameParser.sanitize_filename(filename)
        assert result == 'test file name.mp4'

    def test_limit_length(self):
        """Test filename length limitation"""
        long_name = 'a' * 250 + '.mp4'
        result = FileNameParser.sanitize_filename(long_name)
        assert len(result) <= 200

    def test_preserve_extension_when_limiting_length(self):
        """Test that extension is preserved when limiting length"""
        long_name = 'a' * 250 + '.mkv'
        result = FileNameParser.sanitize_filename(long_name)
        assert result.endswith('.mkv')


class TestExtractSeriesInfo:
    """Test TV series information extraction"""

    def test_standard_format_s01e01(self):
        """Test standard S01E01 format (highest confidence)"""
        filename = "Breaking.Bad.S01E01.Pilot.720p.mp4"
        info = FileNameParser.extract_series_info(filename)

        assert info.season == 1
        assert info.episode == 1
        assert info.confidence >= 90  # High confidence pattern

    def test_format_with_spaces(self):
        """Test S01 E01 format with spaces"""
        filename = "Series Name S01 E05 Episode Title.mkv"
        info = FileNameParser.extract_series_info(filename)

        assert info.season == 1
        assert info.episode == 5
        assert info.confidence >= 90

    def test_x_format(self):
        """Test 1x01 format"""
        filename = "The.Office.1x03.Health.Care.avi"
        info = FileNameParser.extract_series_info(filename)

        assert info.season == 1
        assert info.episode == 3
        assert info.confidence > 0

    def test_x_format_leading(self):
        """Test 12x06 at start (higher confidence)"""
        filename = "12x06.Series.Name.Episode.Title.mp4"
        info = FileNameParser.extract_series_info(filename)

        assert info.season == 12
        assert info.episode == 6
        assert info.confidence >= 85

    def test_verbose_format(self):
        """Test Season 1 Episode 1 format"""
        filename = "Show Name Season 1 Episode 3 Title.mp4"
        info = FileNameParser.extract_series_info(filename)

        assert info.season == 1
        assert info.episode == 3
        assert info.confidence >= 85

    def test_dot_format(self):
        """Test 1.01 format"""
        filename = "Series.1.05.Episode.Title.mp4"
        info = FileNameParser.extract_series_info(filename)

        assert info.season == 1
        assert info.episode == 5

    def test_anime_bracket_format(self):
        """Test [01] anime format"""
        filename = "Anime Series [12] Episode Title.mkv"
        info = FileNameParser.extract_series_info(filename)

        # May detect as episode without season
        assert info.episode is not None or info.season is not None

    def test_multi_episode_format(self):
        """Test S01E01-E03 multi-episode format"""
        filename = "Series.S01E01-E03.Triple.Episode.mp4"
        info = FileNameParser.extract_series_info(filename)

        assert info.season == 1
        # Should detect first episode
        assert info.episode in [1, 3]

    def test_movie_not_detected_as_series(self):
        """Test that movies with years are not detected as TV series"""
        filename = "Fight.Club.1999.1080p.BluRay.mp4"
        info = FileNameParser.extract_series_info(filename)

        # Should not have high confidence for season/episode
        # or should not detect series info at all
        assert info.confidence < 50 or (info.season is None and info.episode is None)

    def test_year_in_brackets_not_confused_with_episode(self):
        """Test that (2023) is not confused with episode number"""
        filename = "Show Name (2023) Something Else.mp4"
        info = FileNameParser.extract_series_info(filename)

        # Should not detect 2023 as episode
        if info.episode is not None:
            assert info.episode != 2023

    def test_no_series_info(self):
        """Test filename without series information"""
        filename = "random_file_without_episode_info.mp4"
        info = FileNameParser.extract_series_info(filename)

        assert info.season is None or info.episode is None or info.confidence < 50


class TestNormalizeForComparison:
    """Test text normalization for comparison"""

    def test_lowercase_conversion(self):
        """Test conversion to lowercase"""
        text = "Breaking Bad"
        result = FileNameParser._normalize_for_comparison(text)
        assert result == "breaking bad"

    def test_remove_year(self):
        """Test year removal"""
        text = "Breaking Bad (2008)"
        result = FileNameParser._normalize_for_comparison(text)
        assert "2008" not in result
        assert "breaking bad" in result

    def test_remove_year_in_brackets(self):
        """Test year in square brackets removal"""
        text = "Movie Name [2023]"
        result = FileNameParser._normalize_for_comparison(text)
        assert "2023" not in result

    def test_remove_language_tags(self):
        """Test language tag removal"""
        text = "Movie Name [ITA]"
        result = FileNameParser._normalize_for_comparison(text)
        assert "ita" not in result

    def test_replace_separators_with_spaces(self):
        """Test separator replacement"""
        text = "Movie.Name_With-Separators"
        result = FileNameParser._normalize_for_comparison(text)
        assert "movie name with separators" == result

    def test_remove_extra_spaces(self):
        """Test extra space removal"""
        text = "Movie    Name    With    Spaces"
        result = FileNameParser._normalize_for_comparison(text)
        assert "movie name with spaces" == result


class TestCalculateSimilarity:
    """Test similarity calculation"""

    def test_identical_strings(self):
        """Test identical strings have similarity 1.0"""
        str1 = "breaking bad"
        str2 = "breaking bad"
        score = FileNameParser._calculate_similarity(str1, str2)
        assert score == 1.0

    def test_completely_different_strings(self):
        """Test completely different strings have low similarity"""
        str1 = "breaking bad"
        str2 = "game of thrones"
        score = FileNameParser._calculate_similarity(str1, str2)
        assert score < 0.3

    def test_partial_match(self):
        """Test partial match has medium similarity"""
        str1 = "breaking bad season one"
        str2 = "breaking bad season two"
        score = FileNameParser._calculate_similarity(str1, str2)
        assert 0.5 < score < 1.0

    def test_substring_bonus(self):
        """Test substring matching gives bonus"""
        str1 = "breaking bad"
        str2 = "breaking bad season 1"
        score = FileNameParser._calculate_similarity(str1, str2)
        # Should have high score due to substring bonus
        assert score > 0.7

    def test_empty_strings(self):
        """Test empty strings return 0"""
        score = FileNameParser._calculate_similarity("", "")
        assert score == 0.0

    def test_one_empty_string(self):
        """Test one empty string returns 0"""
        score = FileNameParser._calculate_similarity("test", "")
        assert score == 0.0


class TestFindSimilarFolder:
    """Test fuzzy folder matching"""

    def test_find_exact_match(self, temp_dir):
        """Test finding exact folder match"""
        # Create test folders
        (temp_dir / "Breaking Bad").mkdir()
        (temp_dir / "Game of Thrones").mkdir()

        result = FileNameParser.find_similar_folder(
            "Breaking Bad",
            temp_dir,
            threshold=0.7
        )

        assert result == "Breaking Bad"

    def test_find_similar_match(self, temp_dir):
        """Test finding similar folder with different formatting"""
        # Create test folder with different formatting
        (temp_dir / "Breaking Bad [ITA]").mkdir()

        result = FileNameParser.find_similar_folder(
            "Breaking Bad",
            temp_dir,
            threshold=0.7
        )

        assert result == "Breaking Bad [ITA]"

    def test_find_similar_with_year(self, temp_dir):
        """Test finding similar folder when one has year"""
        # Create test folder with year
        (temp_dir / "Breaking Bad (2008)").mkdir()

        result = FileNameParser.find_similar_folder(
            "Breaking Bad",
            temp_dir,
            threshold=0.7
        )

        assert result == "Breaking Bad (2008)"

    def test_no_match_below_threshold(self, temp_dir):
        """Test that no match is returned if below threshold"""
        (temp_dir / "Completely Different Show").mkdir()

        result = FileNameParser.find_similar_folder(
            "Breaking Bad",
            temp_dir,
            threshold=0.9  # High threshold
        )

        assert result is None

    def test_nonexistent_directory(self):
        """Test handling of nonexistent directory"""
        result = FileNameParser.find_similar_folder(
            "Test",
            Path("/nonexistent/path"),
            threshold=0.7
        )

        assert result is None

    def test_best_match_selection(self, temp_dir):
        """Test that best match is selected from multiple candidates"""
        # Create multiple folders with varying similarity
        (temp_dir / "Breaking Bad").mkdir()
        (temp_dir / "Breaking Bad (2008)").mkdir()
        (temp_dir / "Breaking").mkdir()

        result = FileNameParser.find_similar_folder(
            "Breaking Bad",
            temp_dir,
            threshold=0.7
        )

        # Should match exact name or very close variant
        assert "Breaking Bad" in result


@pytest.mark.parametrize("filename,expected_season,expected_episode", [
    ("Show.S01E01.mp4", 1, 1),
    ("Show.S05E12.mp4", 5, 12),
    ("Show.1x01.mp4", 1, 1),
    ("Show.3x15.mp4", 3, 15),
    ("Show.Season.2.Episode.5.mp4", 2, 5),
])
def test_various_series_formats(filename, expected_season, expected_episode):
    """Parametrized test for various series formats"""
    info = FileNameParser.extract_series_info(filename)
    assert info.season == expected_season
    assert info.episode == expected_episode


@pytest.mark.security
class TestSecuritySanitization:
    """Security-focused tests for filename sanitization"""

    def test_path_traversal_prevention(self):
        """Test that path traversal attempts are sanitized"""
        filename = "../../../etc/passwd"
        result = FileNameParser.sanitize_filename(filename)
        assert ".." not in result or result.count(".") <= 1  # Only extension dot allowed

    def test_null_byte_handling(self):
        """Test null byte handling"""
        filename = "test\x00file.mp4"
        result = FileNameParser.sanitize_filename(filename)
        assert "\x00" not in result

    def test_unicode_normalization(self):
        """Test that unicode characters are handled safely"""
        filename = "Test\u200bFile\u200d.mp4"  # Zero-width characters
        result = FileNameParser.sanitize_filename(filename)
        # Should handle gracefully without crashing
        assert isinstance(result, str)

    def test_extremely_long_filename(self):
        """Test handling of extremely long filenames"""
        filename = "a" * 10000 + ".mp4"
        result = FileNameParser.sanitize_filename(filename)
        # Should be truncated to reasonable length
        assert len(result) <= 200
