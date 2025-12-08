"""
Message and output formatting utilities
"""

from typing import List
from models.download import DownloadInfo, DownloadStatus


class MessageFormatter:
    """Message formatter for Telegram"""

    @staticmethod
    def format_progress_bar(progress: float, width: int = 20) -> str:
        """
        Create progress bar

        Args:
            progress: Progress percentage (0-100)
            width: Bar width in characters

        Returns:
            Progress bar string
        """
        filled = int((progress / 100) * width)
        empty = width - filled
        return "█" * filled + "░" * empty

    @staticmethod
    def format_time(seconds: int) -> str:
        """
        Format time in readable format

        Args:
            seconds: Total seconds

        Returns:
            Formatted time string
        """
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """
        Format file size

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted size string
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                if unit in ["B", "KB"]:
                    return f"{size_bytes:.0f} {unit}"
                else:
                    return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    @staticmethod
    def format_speed(bytes_per_second: float) -> str:
        """
        Format download speed

        Args:
            bytes_per_second: Bytes per second

        Returns:
            Formatted speed string
        """
        mbps = bytes_per_second / (1024 * 1024)
        if mbps < 1:
            kbps = bytes_per_second / 1024
            return f"{kbps:.1f} KB/s"
        else:
            return f"{mbps:.1f} MB/s"

    @staticmethod
    def format_download_status(download_info: DownloadInfo) -> str:
        """
        Format complete download status

        Args:
            download_info: Download info

        Returns:
            Formatted status message
        """
        status_emoji = {
            DownloadStatus.PENDING: "⏳",
            DownloadStatus.DOWNLOADING: "📥",
            DownloadStatus.COMPLETED: "✅",
            DownloadStatus.FAILED: "❌",
            DownloadStatus.CANCELLED: "🚫",
            DownloadStatus.WAITING_SPACE: "⏸️",
            DownloadStatus.QUEUED: "📋",
        }

        emoji = status_emoji.get(download_info.status, "❓")

        text = f"{emoji} **{download_info.status.value.capitalize()}**\n\n"
        text += f"📁 **File:** `{download_info.filename}`\n"
        text += f"📏 **Size:** {MessageFormatter.format_size(download_info.size)}\n"

        if download_info.status == DownloadStatus.DOWNLOADING:
            text += f"\n**Progress:** {download_info.progress:.1f}%\n"

            if download_info.speed_mbps > 0:
                text += f"⚡ **Speed:** {download_info.speed_mbps:.1f} MB/s\n"

            if download_info.eta_seconds:
                text += f"⏱ **Time remaining:** {MessageFormatter.format_time(download_info.eta_seconds)}\n"

        elif (
            download_info.status == DownloadStatus.FAILED
            and download_info.error_message
        ):
            text += f"\n❌ **Error:** {download_info.error_message}\n"

        return text

    @staticmethod
    def format_queue_position(position: int, total: int) -> str:
        """
        Format queue position

        Args:
            position: Current position
            total: Total items in queue

        Returns:
            Formatted position string
        """
        return f"📊 Queue position: **{position}/{total}**"

    @staticmethod
    def format_disk_space(
        free_gb: float, total_gb: float, warning_threshold: float, min_free: float
    ) -> str:
        """
        Format disk space info

        Args:
            free_gb: Free GB
            total_gb: Total GB
            warning_threshold: Warning threshold
            min_free: Minimum free space

        Returns:
            Formatted space string
        """
        percent_used = ((total_gb - free_gb) / total_gb) * 100

        # Determine status emoji
        if free_gb > warning_threshold:
            emoji = "🟢"
            status = "OK"
        elif free_gb > min_free:
            emoji = "🟡"
            status = "Warning"
        else:
            emoji = "🔴"
            status = "Critical"

        text = f"{emoji} **Disk Space - {status}**\n"
        text += f"• Total: {total_gb:.1f} GB\n"
        text += f"• Used: {total_gb - free_gb:.1f} GB ({percent_used:.1f}%)\n"
        text += f"• Free: {free_gb:.1f} GB\n"
        text += f"• Available for download: {max(0, free_gb - min_free):.1f} GB"

        return text

    @staticmethod
    def format_download_list(downloads: List[DownloadInfo]) -> str:
        """
        Format download list

        Args:
            downloads: Download list

        Returns:
            Formatted list
        """
        if not downloads:
            return "📭 No active downloads"

        text = f"📥 **Active downloads ({len(downloads)}):**\n\n"

        for idx, dl in enumerate(downloads, 1):
            text += f"{idx}. `{dl.filename[:30]}...`\n"

            if dl.status == DownloadStatus.DOWNLOADING:
                text += f"   {MessageFormatter.format_progress_bar(dl.progress, 10)} {dl.progress:.0f}%\n"

                if dl.speed_mbps > 0:
                    text += f"   ⚡ {dl.speed_mbps:.1f} MB/s"

                if dl.eta_seconds:
                    text += f" - {MessageFormatter.format_time(dl.eta_seconds)}\n"
                else:
                    text += "\n"
            else:
                text += f"   Status: {dl.status.value}\n"

            text += "\n"

        return text

    @staticmethod
    def format_error(error_type: str, error_message: str) -> str:
        """
        Format error message

        Args:
            error_type: Error type
            error_message: Error message

        Returns:
            Formatted error
        """
        emoji_map = {
            "space": "💾",
            "network": "🌐",
            "permission": "🔒",
            "file": "📁",
            "tmdb": "🎬",
            "generic": "⚠️",
        }

        emoji = emoji_map.get(error_type, "❌")

        return f"{emoji} **Error {error_type.capitalize()}**\n\n{error_message}"

    @staticmethod
    def escape_markdown(text: str) -> str:
        """
        Escape markdown characters

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        escape_chars = [
            "_",
            "*",
            "[",
            "]",
            "(",
            ")",
            "~",
            "`",
            ">",
            "#",
            "+",
            "-",
            "=",
            "|",
            "{",
            "}",
            ".",
            "!",
        ]

        for char in escape_chars:
            text = text.replace(char, f"\\{char}")

        return text


class TableFormatter:
    """Table formatter for text output"""

    @staticmethod
    def create_table(
        headers: List[str], rows: List[List[str]], align: str = "left"
    ) -> str:
        """
        Create formatted table

        Args:
            headers: Column headers
            rows: Data rows
            align: Alignment (left, right, center)

        Returns:
            Formatted table
        """
        if not rows:
            return "No data available"

        # Calculate column widths
        col_widths = []
        for i, header in enumerate(headers):
            max_width = len(header)
            for row in rows:
                if i < len(row):
                    max_width = max(max_width, len(str(row[i])))
            col_widths.append(max_width)

        # Create separator
        separator = "+" + "+".join(["-" * (w + 2) for w in col_widths]) + "+"

        # Format header
        header_row = "|"
        for i, header in enumerate(headers):
            if align == "center":
                header_row += f" {header.center(col_widths[i])} |"
            elif align == "right":
                header_row += f" {header.rjust(col_widths[i])} |"
            else:
                header_row += f" {header.ljust(col_widths[i])} |"

        # Build table
        table = f"```\n{separator}\n{header_row}\n{separator}\n"

        # Add rows
        for row in rows:
            row_str = "|"
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    cell_str = str(cell)[: col_widths[i]]
                    if align == "center":
                        row_str += f" {cell_str.center(col_widths[i])} |"
                    elif align == "right":
                        row_str += f" {cell_str.rjust(col_widths[i])} |"
                    else:
                        row_str += f" {cell_str.ljust(col_widths[i])} |"
            table += f"{row_str}\n"

        table += f"{separator}\n```"

        return table
