"""
Command History Module for Rocket CLI

Provides persistent command history with search, recall, and statistics.
Implements a circular buffer for efficient memory usage.

Features:
- Persistent storage in ~/.rocket-cli/history.json
- Search history by pattern
- Statistics (most used commands, recent commands)
- Circular buffer (max 1000 entries)
- Export/import history
- Clear history options

Usage:
    from Rocket.Utils.history import CommandHistory
    
    history = CommandHistory()
    history.add("rocket chat -m 'Hello'")
    recent = history.get_recent(10)
    matches = history.search("chat")
"""

import json
import time
from collections import deque, Counter
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

from Rocket.Utils.Log import get_logger

logger = get_logger(__name__)


@dataclass
class HistoryEntry:
    """Represents a single command history entry."""
    command: str
    timestamp: float
    exit_code: int = 0
    duration_ms: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'HistoryEntry':
        """Create from dictionary."""
        return cls(**data)
    
    def formatted_time(self) -> str:
        """Get human-readable timestamp."""
        dt = datetime.fromtimestamp(self.timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")


class CommandHistory:
    """
    Manages command history with persistent storage.
    
    Implements a circular buffer with configurable max size.
    Automatically saves changes to disk.
    """
    
    def __init__(
        self,
        history_file: Optional[Path] = None,
        max_size: int = 1000,
        auto_save: bool = True
    ):
        """
        Initialize command history.
        
        Args:
            history_file: Path to history file (default: ~/.rocket-cli/history.json)
            max_size: Maximum number of entries to keep
            auto_save: Automatically save after each addition
        """
        self.history_file = history_file or (Path.home() / ".rocket-cli" / "history.json")
        self.max_size = max_size
        self.auto_save = auto_save
        self._history: deque[HistoryEntry] = deque(maxlen=max_size)
        
        # Create directory if needed
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing history
        self.load()
    
    def add(
        self,
        command: str,
        exit_code: int = 0,
        duration_ms: Optional[float] = None
    ) -> None:
        """
        Add a command to history.
        
        Args:
            command: Command string
            exit_code: Exit code (0 = success)
            duration_ms: Execution duration in milliseconds
        """
        if not command or not command.strip():
            return
        
        entry = HistoryEntry(
            command=command.strip(),
            timestamp=time.time(),
            exit_code=exit_code,
            duration_ms=duration_ms
        )
        
        self._history.append(entry)
        
        if self.auto_save:
            self.save()
        
        logger.debug(f"Added to history: {command[:50]}...")
    
    def get_recent(self, count: int = 10) -> List[HistoryEntry]:
        """
        Get most recent commands.
        
        Args:
            count: Number of commands to return
            
        Returns:
            List of recent history entries (most recent first)
        """
        return list(reversed(list(self._history)))[:count]
    
    def search(self, pattern: str, case_sensitive: bool = False) -> List[HistoryEntry]:
        """
        Search history for commands containing pattern.
        
        Args:
            pattern: Search pattern
            case_sensitive: Whether search is case-sensitive
            
        Returns:
            List of matching history entries
        """
        if not pattern:
            return []
        
        if not case_sensitive:
            pattern = pattern.lower()
        
        matches = []
        for entry in reversed(self._history):
            command = entry.command if case_sensitive else entry.command.lower()
            if pattern in command:
                matches.append(entry)
        
        return matches
    
    def get_statistics(self) -> Dict:
        """
        Get history statistics.
        
        Returns:
            Dictionary with statistics:
            - total_commands: Total number of commands
            - unique_commands: Number of unique commands
            - most_used: List of (command, count) tuples
            - success_rate: Percentage of successful commands
            - avg_duration_ms: Average command duration
        """
        if not self._history:
            return {
                "total_commands": 0,
                "unique_commands": 0,
                "most_used": [],
                "success_rate": 0.0,
                "avg_duration_ms": 0.0
            }
        
        commands = [entry.command for entry in self._history]
        counter = Counter(commands)
        
        successes = sum(1 for entry in self._history if entry.exit_code == 0)
        durations = [entry.duration_ms for entry in self._history if entry.duration_ms is not None]
        
        return {
            "total_commands": len(self._history),
            "unique_commands": len(counter),
            "most_used": counter.most_common(10),
            "success_rate": (successes / len(self._history)) * 100,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0.0
        }
    
    def clear(self, keep_last: int = 0) -> None:
        """
        Clear command history.
        
        Args:
            keep_last: Number of recent commands to keep (0 = clear all)
        """
        if keep_last > 0:
            recent = list(self._history)[-keep_last:]
            self._history.clear()
            self._history.extend(recent)
        else:
            self._history.clear()
        
        self.save()
        logger.info(f"History cleared (kept last {keep_last} entries)")
    
    def save(self) -> bool:
        """
        Save history to disk.
        
        Returns:
            True if saved successfully
        """
        try:
            data = {
                "version": "1.0",
                "max_size": self.max_size,
                "entries": [entry.to_dict() for entry in self._history]
            }
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
            return False
    
    def load(self) -> bool:
        """
        Load history from disk.
        
        Returns:
            True if loaded successfully
        """
        if not self.history_file.exists():
            logger.debug("No history file found, starting fresh")
            return True
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            entries = data.get("entries", [])
            self._history.clear()
            
            for entry_data in entries:
                self._history.append(HistoryEntry.from_dict(entry_data))
            
            logger.info(f"Loaded {len(self._history)} commands from history")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            return False
    
    def export_to_file(self, file_path: Path) -> bool:
        """
        Export history to a file.
        
        Args:
            file_path: Path to export file
            
        Returns:
            True if exported successfully
        """
        try:
            data = {
                "exported_at": datetime.now().isoformat(),
                "total_entries": len(self._history),
                "entries": [entry.to_dict() for entry in self._history]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Exported {len(self._history)} commands to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export history: {e}")
            return False
    
    def import_from_file(self, file_path: Path, append: bool = True) -> bool:
        """
        Import history from a file.
        
        Args:
            file_path: Path to import file
            append: If True, append to existing history; if False, replace
            
        Returns:
            True if imported successfully
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            entries = data.get("entries", [])
            
            if not append:
                self._history.clear()
            
            for entry_data in entries:
                self._history.append(HistoryEntry.from_dict(entry_data))
            
            self.save()
            logger.info(f"Imported {len(entries)} commands from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import history: {e}")
            return False
    
    def __len__(self) -> int:
        """Get number of entries in history."""
        return len(self._history)
    
    def __iter__(self):
        """Iterate over history entries (oldest first)."""
        return iter(self._history)


# Global history instance
_history_instance: Optional[CommandHistory] = None


def get_history() -> CommandHistory:
    """
    Get the global command history instance.
    
    Returns:
        CommandHistory instance
    """
    global _history_instance
    
    if _history_instance is None:
        _history_instance = CommandHistory()
    
    return _history_instance
