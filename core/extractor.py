"""
Archive extraction manager for MediaButler
"""

import asyncio
import zipfile
import re
from pathlib import Path
from typing import List, Optional, Tuple
from core.config import get_config


class ArchiveExtractor:
    """Manager for extracting compressed archives"""

    # Supported archive extensions
    SUPPORTED_FORMATS = {".zip", ".rar", ".7z"}

    # Video file extensions to look for
    VIDEO_EXTENSIONS = {
        ".mp4",
        ".mkv",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".webm",
        ".m4v",
        ".mpg",
        ".mpeg",
        ".m2ts",
        ".ts",
    }

    # Multi-part archive patterns
    MULTIPART_PATTERNS = [
        r"\.part(\d+)\.rar$",  # file.part1.rar, file.part2.rar
        r"\.r(\d{2,3})$",  # file.r00, file.r01 (old format)
        r"\.(\d{3})$",  # file.001, file.002 (7z format)
    ]

    def __init__(self):
        self.config = get_config()
        self.logger = self.config.logger

        # Check for optional extraction libraries
        self._check_extractors()

    def _check_extractors(self):
        """Check availability of extraction libraries"""
        self.has_rarfile = False
        self.has_py7zr = False

        try:
            import rarfile  # noqa: F401

            self.has_rarfile = True
            self.logger.info("RAR extraction support available")
        except ImportError:
            self.logger.warning("RAR extraction not available (install rarfile library)")

        try:
            import py7zr  # noqa: F401

            self.has_py7zr = True
            self.logger.info("7z extraction support available")
        except ImportError:
            self.logger.warning("7z extraction not available (install py7zr library)")

    def is_multipart_archive(self, file_path: Path) -> bool:
        """
        Check if file is a multi-part archive

        Args:
            file_path: Path to file

        Returns:
            True if file is a multi-part archive
        """
        filename = file_path.name.lower()

        for pattern in self.MULTIPART_PATTERNS:
            if re.search(pattern, filename):
                return True

        return False

    def get_multipart_number(self, file_path: Path) -> Optional[int]:
        """
        Get part number from multi-part archive

        Args:
            file_path: Path to file

        Returns:
            Part number (1, 2, 3...) or None if not a multi-part archive
        """
        filename = file_path.name.lower()

        for pattern in self.MULTIPART_PATTERNS:
            match = re.search(pattern, filename)
            if match:
                return int(match.group(1))

        return None

    def is_first_part(self, file_path: Path) -> bool:
        """
        Check if file is the first part of a multi-part archive

        Args:
            file_path: Path to file

        Returns:
            True if first part or not a multi-part archive
        """
        if not self.is_multipart_archive(file_path):
            return True  # Single file, treat as "first"

        part_num = self.get_multipart_number(file_path)
        return part_num == 1 or part_num == 0  # .r00 or .part1

    def is_archive(self, file_path: Path) -> bool:
        """
        Check if file is a supported archive

        Args:
            file_path: Path to file

        Returns:
            True if file is a supported archive
        """
        suffix = file_path.suffix.lower()
        filename = file_path.name.lower()

        # Check for multi-part archives
        if self.is_multipart_archive(file_path):
            # For .rar multi-part, check if rarfile is available
            if ".rar" in filename and not self.has_rarfile:
                self.logger.warning(
                    f"Multi-part RAR file detected but rarfile library " f"not available: {file_path.name}"
                )
                return False
            # For .7z multi-part, check if py7zr is available
            if re.search(r"\.\d{3}$", filename) and not self.has_py7zr:
                self.logger.warning(
                    f"Multi-part 7z file detected but py7zr library " f"not available: {file_path.name}"
                )
                return False
            return True

        # Check basic support
        if suffix not in self.SUPPORTED_FORMATS:
            return False

        # Check library availability for specific formats
        if suffix == ".rar" and not self.has_rarfile:
            self.logger.warning(f"RAR file detected but rarfile library not available: {file_path.name}")
            return False

        if suffix == ".7z" and not self.has_py7zr:
            self.logger.warning(f"7z file detected but py7zr library not available: {file_path.name}")
            return False

        return True

    async def extract_archive(
        self,
        archive_path: Path,
        extract_to: Optional[Path] = None,
        delete_archive: bool = True,
    ) -> Tuple[bool, List[Path]]:
        """
        Extract archive and return list of extracted video files

        Args:
            archive_path: Path to archive file
            extract_to: Destination directory (default: same as archive)
            delete_archive: Delete archive after successful extraction

        Returns:
            Tuple of (success, list of extracted video files)
        """
        if not archive_path.exists():
            self.logger.error(f"Archive not found: {archive_path}")
            return False, []

        if not self.is_archive(archive_path):
            self.logger.debug(f"Not a supported archive: {archive_path.name}")
            return False, []

        # Default extraction directory is parent folder
        if extract_to is None:
            extract_to = archive_path.parent

        extract_to.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Extracting archive: {archive_path.name}")

        try:
            # Extract based on format
            suffix = archive_path.suffix.lower()

            if suffix == ".zip":
                extracted_files = await self._extract_zip(archive_path, extract_to)
            elif suffix == ".rar":
                extracted_files = await self._extract_rar(archive_path, extract_to)
            elif suffix == ".7z":
                extracted_files = await self._extract_7z(archive_path, extract_to)
            else:
                self.logger.error(f"Unsupported format: {suffix}")
                return False, []

            # Filter video files
            video_files = [f for f in extracted_files if f.suffix.lower() in self.VIDEO_EXTENSIONS]

            if not video_files:
                self.logger.warning(f"No video files found in archive: {archive_path.name}")
                # Clean up extracted non-video files
                for file in extracted_files:
                    try:
                        if file.exists():
                            file.unlink()
                    except Exception as e:
                        self.logger.warning(f"Could not delete non-video file {file}: {e}")
                return False, []

            self.logger.info(f"Extracted {len(video_files)} video file(s) from {archive_path.name}")

            # Delete archive if requested and extraction successful
            if delete_archive and self.config.extraction.delete_after_extract:
                try:
                    archive_path.unlink()
                    self.logger.info(f"Deleted archive: {archive_path.name}")
                except Exception as e:
                    self.logger.warning(f"Could not delete archive {archive_path.name}: {e}")

            return True, video_files

        except Exception as e:
            self.logger.error(f"Error extracting archive {archive_path.name}: {e}", exc_info=True)
            return False, []

    async def _extract_zip(self, archive_path: Path, extract_to: Path) -> List[Path]:
        """Extract ZIP archive"""
        extracted_files = []

        def extract_sync():
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                files = []
                for member in zip_ref.namelist():
                    # Skip directories and hidden files
                    if member.endswith("/") or member.startswith("."):
                        continue

                    # Extract file
                    zip_ref.extract(member, extract_to)
                    file_path = extract_to / member
                    files.append(file_path)

                return files

        # Run extraction in executor to avoid blocking
        extracted_files = await asyncio.get_event_loop().run_in_executor(None, extract_sync)

        return extracted_files

    async def _extract_rar(self, archive_path: Path, extract_to: Path) -> List[Path]:
        """Extract RAR archive"""
        if not self.has_rarfile:
            raise Exception("rarfile library not available")

        import rarfile

        extracted_files = []

        def extract_sync():
            with rarfile.RarFile(archive_path, "r") as rar_ref:
                files = []
                for member in rar_ref.namelist():
                    # Skip directories and hidden files
                    if member.endswith("/") or member.startswith("."):
                        continue

                    # Extract file
                    rar_ref.extract(member, extract_to)
                    file_path = extract_to / member
                    files.append(file_path)

                return files

        # Run extraction in executor to avoid blocking
        extracted_files = await asyncio.get_event_loop().run_in_executor(None, extract_sync)

        return extracted_files

    async def _extract_7z(self, archive_path: Path, extract_to: Path) -> List[Path]:
        """Extract 7z archive"""
        if not self.has_py7zr:
            raise Exception("py7zr library not available")

        import py7zr

        extracted_files = []

        def extract_sync():
            with py7zr.SevenZipFile(archive_path, "r") as sz_ref:
                sz_ref.extractall(path=extract_to)
                # Get list of extracted files
                return [extract_to / name for name in sz_ref.getnames()]

        # Run extraction in executor to avoid blocking
        extracted_files = await asyncio.get_event_loop().run_in_executor(None, extract_sync)

        return extracted_files

    async def has_video_files(self, archive_path: Path) -> bool:
        """
        Check if archive contains video files without extracting

        Args:
            archive_path: Path to archive

        Returns:
            True if archive contains at least one video file
        """
        if not self.is_archive(archive_path):
            return False

        try:
            suffix = archive_path.suffix.lower()

            def check_sync():
                if suffix == ".zip":
                    with zipfile.ZipFile(archive_path, "r") as zip_ref:
                        return any(Path(name).suffix.lower() in self.VIDEO_EXTENSIONS for name in zip_ref.namelist())
                elif suffix == ".rar" and self.has_rarfile:
                    import rarfile

                    with rarfile.RarFile(archive_path, "r") as rar_ref:
                        return any(Path(name).suffix.lower() in self.VIDEO_EXTENSIONS for name in rar_ref.namelist())
                elif suffix == ".7z" and self.has_py7zr:
                    import py7zr

                    with py7zr.SevenZipFile(archive_path, "r") as sz_ref:
                        return any(Path(name).suffix.lower() in self.VIDEO_EXTENSIONS for name in sz_ref.getnames())
                return False

            # Run check in executor
            has_video = await asyncio.get_event_loop().run_in_executor(None, check_sync)

            return has_video

        except Exception as e:
            self.logger.error(f"Error checking archive contents {archive_path.name}: {e}")
            return False
