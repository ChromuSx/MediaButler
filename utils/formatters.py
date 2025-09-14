"""
Utility per formattazione messaggi e output
"""
from typing import Optional, List
from models.download import DownloadInfo, DownloadStatus


class MessageFormatter:
    """Formattatore messaggi per Telegram"""
    
    @staticmethod
    def format_progress_bar(progress: float, width: int = 20) -> str:
        """
        Crea barra progresso
        
        Args:
            progress: Percentuale progresso (0-100)
            width: Larghezza barra in caratteri
            
        Returns:
            Stringa barra progresso
        """
        filled = int((progress / 100) * width)
        empty = width - filled
        return "█" * filled + "░" * empty
    
    @staticmethod
    def format_time(seconds: int) -> str:
        """
        Formatta tempo in formato leggibile
        
        Args:
            seconds: Secondi totali
            
        Returns:
            Stringa tempo formattata
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
        Formatta dimensione file
        
        Args:
            size_bytes: Dimensione in bytes
            
        Returns:
            Stringa dimensione formattata
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                if unit in ['B', 'KB']:
                    return f"{size_bytes:.0f} {unit}"
                else:
                    return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    @staticmethod
    def format_speed(bytes_per_second: float) -> str:
        """
        Formatta velocità download
        
        Args:
            bytes_per_second: Bytes al secondo
            
        Returns:
            Stringa velocità formattata
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
        Formatta stato download completo
        
        Args:
            download_info: Info download
            
        Returns:
            Messaggio stato formattato
        """
        status_emoji = {
            DownloadStatus.PENDING: "⏳",
            DownloadStatus.DOWNLOADING: "📥",
            DownloadStatus.COMPLETED: "✅",
            DownloadStatus.FAILED: "❌",
            DownloadStatus.CANCELLED: "🚫",
            DownloadStatus.WAITING_SPACE: "⏸️",
            DownloadStatus.QUEUED: "📋"
        }
        
        emoji = status_emoji.get(download_info.status, "❓")
        
        text = f"{emoji} **{download_info.status.value.capitalize()}**\n\n"
        text += f"📁 **File:** `{download_info.filename}`\n"
        text += f"📏 **Dimensione:** {MessageFormatter.format_size(download_info.size)}\n"
        
        if download_info.status == DownloadStatus.DOWNLOADING:
            text += f"\n**Progresso:** {download_info.progress:.1f}%\n"
            
            if download_info.speed_mbps > 0:
                text += f"⚡ **Velocità:** {download_info.speed_mbps:.1f} MB/s\n"
            
            if download_info.eta_seconds:
                text += f"⏱ **Tempo rimanente:** {MessageFormatter.format_time(download_info.eta_seconds)}\n"
        
        elif download_info.status == DownloadStatus.FAILED and download_info.error_message:
            text += f"\n❌ **Errore:** {download_info.error_message}\n"
        
        return text
    
    @staticmethod
    def format_queue_position(position: int, total: int) -> str:
        """
        Formatta posizione in coda
        
        Args:
            position: Posizione corrente
            total: Totale elementi in coda
            
        Returns:
            Stringa posizione formattata
        """
        return f"📊 Posizione in coda: **{position}/{total}**"
    
    @staticmethod
    def format_disk_space(
        free_gb: float,
        total_gb: float,
        warning_threshold: float,
        min_free: float
    ) -> str:
        """
        Formatta info spazio disco
        
        Args:
            free_gb: GB liberi
            total_gb: GB totali
            warning_threshold: Soglia avviso
            min_free: Minimo spazio libero
            
        Returns:
            Stringa spazio formattata
        """
        percent_used = ((total_gb - free_gb) / total_gb) * 100
        
        # Determina emoji stato
        if free_gb > warning_threshold:
            emoji = "🟢"
            status = "OK"
        elif free_gb > min_free:
            emoji = "🟡"
            status = "Attenzione"
        else:
            emoji = "🔴"
            status = "Critico"
        
        text = f"{emoji} **Spazio Disco - {status}**\n"
        text += f"• Totale: {total_gb:.1f} GB\n"
        text += f"• Usato: {total_gb - free_gb:.1f} GB ({percent_used:.1f}%)\n"
        text += f"• Libero: {free_gb:.1f} GB\n"
        text += f"• Disponibile per download: {max(0, free_gb - min_free):.1f} GB"
        
        return text
    
    @staticmethod
    def format_download_list(downloads: List[DownloadInfo]) -> str:
        """
        Formatta lista download
        
        Args:
            downloads: Lista download
            
        Returns:
            Lista formattata
        """
        if not downloads:
            return "📭 Nessun download in corso"
        
        text = f"📥 **Download attivi ({len(downloads)}):**\n\n"
        
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
                text += f"   Stato: {dl.status.value}\n"
            
            text += "\n"
        
        return text
    
    @staticmethod
    def format_error(error_type: str, error_message: str) -> str:
        """
        Formatta messaggio errore
        
        Args:
            error_type: Tipo errore
            error_message: Messaggio errore
            
        Returns:
            Errore formattato
        """
        emoji_map = {
            'space': '💾',
            'network': '🌐',
            'permission': '🔒',
            'file': '📁',
            'tmdb': '🎬',
            'generic': '⚠️'
        }
        
        emoji = emoji_map.get(error_type, '❌')
        
        return f"{emoji} **Errore {error_type.capitalize()}**\n\n{error_message}"
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """
        Escape caratteri markdown
        
        Args:
            text: Testo da escapare
            
        Returns:
            Testo con escape
        """
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        
        return text


class TableFormatter:
    """Formattatore tabelle per output testuale"""
    
    @staticmethod
    def create_table(
        headers: List[str],
        rows: List[List[str]],
        align: str = 'left'
    ) -> str:
        """
        Crea tabella formattata
        
        Args:
            headers: Intestazioni colonne
            rows: Righe dati
            align: Allineamento (left, right, center)
            
        Returns:
            Tabella formattata
        """
        if not rows:
            return "Nessun dato disponibile"
        
        # Calcola larghezze colonne
        col_widths = []
        for i, header in enumerate(headers):
            max_width = len(header)
            for row in rows:
                if i < len(row):
                    max_width = max(max_width, len(str(row[i])))
            col_widths.append(max_width)
        
        # Crea separatore
        separator = "+" + "+".join(["-" * (w + 2) for w in col_widths]) + "+"
        
        # Formatta header
        header_row = "|"
        for i, header in enumerate(headers):
            if align == 'center':
                header_row += f" {header.center(col_widths[i])} |"
            elif align == 'right':
                header_row += f" {header.rjust(col_widths[i])} |"
            else:
                header_row += f" {header.ljust(col_widths[i])} |"
        
        # Costruisci tabella
        table = f"```\n{separator}\n{header_row}\n{separator}\n"
        
        # Aggiungi righe
        for row in rows:
            row_str = "|"
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    cell_str = str(cell)[:col_widths[i]]
                    if align == 'center':
                        row_str += f" {cell_str.center(col_widths[i])} |"
                    elif align == 'right':
                        row_str += f" {cell_str.rjust(col_widths[i])} |"
                    else:
                        row_str += f" {cell_str.ljust(col_widths[i])} |"
            table += f"{row_str}\n"
        
        table += f"{separator}\n```"
        
        return table