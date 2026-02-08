"""
Notification System for Rocket CLI

Provides event-based notifications for CLI operations and server events.

Features:
- Multiple notification channels (desktop, console, webhook)
- Event subscriptions and filtering
- Priority levels (info, warning, error, critical)
- Notification history and management
- Custom notification templates
- Rate limiting to prevent spam

Usage:
    from Rocket.Utils.notifications import NotificationManager, NotificationLevel
    
    manager = NotificationManager()
    manager.send_notification(
        title="Code Generated",
        message="Successfully generated 150 lines of Python code",
        level=NotificationLevel.SUCCESS
    )
"""

import json
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from collections import deque

from Rocket.Utils.Log import get_logger

logger = get_logger(__name__)


class NotificationLevel(Enum):
    """Notification priority levels."""
    DEBUG = "debug"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    
    def to_color(self) -> str:
        """Get Rich color for this level."""
        colors = {
            NotificationLevel.DEBUG: "dim",
            NotificationLevel.INFO: "cyan",
            NotificationLevel.SUCCESS: "green",
            NotificationLevel.WARNING: "yellow",
            NotificationLevel.ERROR: "red",
            NotificationLevel.CRITICAL: "bold red"
        }
        return colors.get(self, "white")
    
    def to_icon(self) -> str:
        """Get emoji icon for this level."""
        icons = {
            NotificationLevel.DEBUG: "🔍",
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.SUCCESS: "✅",
            NotificationLevel.WARNING: "⚠️",
            NotificationLevel.ERROR: "❌",
            NotificationLevel.CRITICAL: "🚨"
        }
        return icons.get(self, "📢")


@dataclass
class Notification:
    """Represents a single notification."""
    title: str
    message: str
    level: NotificationLevel
    timestamp: float
    category: str = "general"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "message": self.message,
            "level": self.level.value,
            "timestamp": self.timestamp,
            "category": self.category,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Notification':
        """Create from dictionary."""
        data['level'] = NotificationLevel(data['level'])
        return cls(**data)
    
    def formatted_time(self) -> str:
        """Get human-readable timestamp."""
        dt = datetime.fromtimestamp(self.timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    
    def format_console(self) -> str:
        """Format notification for console display."""
        icon = self.level.to_icon()
        return f"{icon} [{self.level.to_color()}]{self.title}[/{self.level.to_color()}]: {self.message}"


class NotificationChannel(Enum):
    """Available notification channels."""
    CONSOLE = "console"          # Print to console
    DESKTOP = "desktop"          # Desktop notifications (OS-specific)
    FILE = "file"                # Log to file
    WEBHOOK = "webhook"          # Send to webhook URL
    EMAIL = "email"              # Send via email (requires SMTP config)


@dataclass
class NotificationConfig:
    """Notification system configuration."""
    enabled: bool = True
    channels: List[NotificationChannel] = None
    min_level: NotificationLevel = NotificationLevel.INFO
    max_history: int = 1000
    rate_limit_seconds: int = 60
    rate_limit_count: int = 10
    
    def __post_init__(self):
        if self.channels is None:
            self.channels = [NotificationChannel.CONSOLE]


class NotificationManager:
    """
    Manages notifications across multiple channels.
    
    Handles notification delivery, filtering, history, and rate limiting.
    """
    
    def __init__(
        self,
        config: Optional[NotificationConfig] = None,
        history_file: Optional[Path] = None
    ):
        """
        Initialize notification manager.
        
        Args:
            config: Notification configuration
            history_file: Path to notification history file
        """
        self.config = config or NotificationConfig()
        self.history_file = history_file or (Path.home() / ".rocket-cli" / "notifications.json")
        
        self._history: deque[Notification] = deque(maxlen=self.config.max_history)
        self._subscribers: Dict[str, List[Callable]] = {}
        self._rate_limiter: deque[float] = deque(maxlen=self.config.rate_limit_count)
        
        # Create directory if needed
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load history
        self.load_history()
    
    def send_notification(
        self,
        title: str,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a notification.
        
        Args:
            title: Notification title
            message: Notification message
            level: Notification level
            category: Notification category
            metadata: Additional metadata
            
        Returns:
            True if notification was sent successfully
        """
        if not self.config.enabled:
            return False
        
        # Check minimum level
        level_priority = {
            NotificationLevel.DEBUG: 0,
            NotificationLevel.INFO: 1,
            NotificationLevel.SUCCESS: 2,
            NotificationLevel.WARNING: 3,
            NotificationLevel.ERROR: 4,
            NotificationLevel.CRITICAL: 5
        }
        
        if level_priority[level] < level_priority[self.config.min_level]:
            return False
        
        # Check rate limiting
        if not self._check_rate_limit():
            logger.debug("Notification rate limit exceeded")
            return False
        
        # Create notification
        notification = Notification(
            title=title,
            message=message,
            level=level,
            timestamp=time.time(),
            category=category,
            metadata=metadata or {}
        )
        
        # Add to history
        self._history.append(notification)
        
        # Deliver to channels
        self._deliver(notification)
        
        # Notify subscribers
        self._notify_subscribers(notification)
        
        # Save history
        self.save_history()
        
        return True
    
    def _check_rate_limit(self) -> bool:
        """
        Check if rate limit allows sending notification.
        
        Returns:
            True if within rate limit
        """
        current_time = time.time()
        
        # Remove old entries outside the rate limit window
        cutoff_time = current_time - self.config.rate_limit_seconds
        while self._rate_limiter and self._rate_limiter[0] < cutoff_time:
            self._rate_limiter.popleft()
        
        # Check if we're at the limit
        if len(self._rate_limiter) >= self.config.rate_limit_count:
            return False
        
        # Add current timestamp
        self._rate_limiter.append(current_time)
        return True
    
    def _deliver(self, notification: Notification) -> None:
        """
        Deliver notification to all configured channels.
        
        Args:
            notification: Notification to deliver
        """
        for channel in self.config.channels:
            try:
                if channel == NotificationChannel.CONSOLE:
                    self._deliver_console(notification)
                elif channel == NotificationChannel.FILE:
                    self._deliver_file(notification)
                elif channel == NotificationChannel.DESKTOP:
                    self._deliver_desktop(notification)
                elif channel == NotificationChannel.WEBHOOK:
                    self._deliver_webhook(notification)
            except Exception as e:
                logger.error(f"Failed to deliver notification to {channel.value}: {e}")
    
    def _deliver_console(self, notification: Notification) -> None:
        """Deliver notification to console."""
        from rich.console import Console
        console = Console()
        console.print(notification.format_console())
    
    def _deliver_file(self, notification: Notification) -> None:
        """Deliver notification to log file."""
        log_file = self.history_file.parent / "notifications.log"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{notification.formatted_time()}] {notification.level.value.upper()}: {notification.title} - {notification.message}\n")
    
    def _deliver_desktop(self, notification: Notification) -> None:
        """Deliver desktop notification (platform-specific)."""
        try:
            import platform
            system = platform.system()
            
            if system == "Windows":
                self._desktop_windows(notification)
            elif system == "Darwin":  # macOS
                self._desktop_macos(notification)
            elif system == "Linux":
                self._desktop_linux(notification)
        except Exception as e:
            logger.debug(f"Desktop notification not available: {e}")
    
    def _desktop_windows(self, notification: Notification) -> None:
        """Windows desktop notification."""
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(
                notification.title,
                notification.message,
                duration=5,
                threaded=True
            )
        except ImportError:
            logger.debug("win10toast not installed, skipping desktop notification")
    
    def _desktop_macos(self, notification: Notification) -> None:
        """macOS desktop notification."""
        import subprocess
        script = f'display notification "{notification.message}" with title "{notification.title}"'
        subprocess.run(['osascript', '-e', script])
    
    def _desktop_linux(self, notification: Notification) -> None:
        """Linux desktop notification."""
        import subprocess
        subprocess.run(['notify-send', notification.title, notification.message])
    
    def _deliver_webhook(self, notification: Notification) -> None:
        """Deliver notification to webhook."""
        # This would require webhook URL configuration
        logger.debug("Webhook delivery not implemented yet")
    
    def _notify_subscribers(self, notification: Notification) -> None:
        """
        Notify all subscribers for this notification category.
        
        Args:
            notification: Notification to broadcast
        """
        # Notify category-specific subscribers
        if notification.category in self._subscribers:
            for callback in self._subscribers[notification.category]:
                try:
                    callback(notification)
                except Exception as e:
                    logger.error(f"Subscriber callback failed: {e}")
        
        # Notify global subscribers
        if "*" in self._subscribers:
            for callback in self._subscribers["*"]:
                try:
                    callback(notification)
                except Exception as e:
                    logger.error(f"Global subscriber callback failed: {e}")
    
    def subscribe(self, category: str, callback: Callable[[Notification], None]) -> None:
        """
        Subscribe to notifications for a category.
        
        Args:
            category: Notification category ("*" for all)
            callback: Function to call when notification is sent
        """
        if category not in self._subscribers:
            self._subscribers[category] = []
        self._subscribers[category].append(callback)
        logger.debug(f"Added subscriber for category: {category}")
    
    def unsubscribe(self, category: str, callback: Callable) -> bool:
        """
        Unsubscribe from notifications.
        
        Args:
            category: Notification category
            callback: Callback function to remove
            
        Returns:
            True if unsubscribed successfully
        """
        if category in self._subscribers:
            try:
                self._subscribers[category].remove(callback)
                return True
            except ValueError:
                pass
        return False
    
    def get_history(
        self,
        count: Optional[int] = None,
        level: Optional[NotificationLevel] = None,
        category: Optional[str] = None
    ) -> List[Notification]:
        """
        Get notification history with optional filtering.
        
        Args:
            count: Maximum number of notifications to return
            level: Filter by notification level
            category: Filter by category
            
        Returns:
            List of notifications (most recent first)
        """
        notifications = list(reversed(self._history))
        
        # Apply filters
        if level:
            notifications = [n for n in notifications if n.level == level]
        
        if category:
            notifications = [n for n in notifications if n.category == category]
        
        # Apply count limit
        if count:
            notifications = notifications[:count]
        
        return notifications
    
    def clear_history(self) -> None:
        """Clear notification history."""
        self._history.clear()
        self.save_history()
        logger.info("Notification history cleared")
    
    def save_history(self) -> bool:
        """
        Save notification history to disk.
        
        Returns:
            True if saved successfully
        """
        try:
            data = {
                "version": "1.0",
                "notifications": [n.to_dict() for n in self._history]
            }
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save notification history: {e}")
            return False
    
    def load_history(self) -> bool:
        """
        Load notification history from disk.
        
        Returns:
            True if loaded successfully
        """
        if not self.history_file.exists():
            return True
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            notifications = data.get("notifications", [])
            self._history.clear()
            
            for notif_data in notifications:
                self._history.append(Notification.from_dict(notif_data))
            
            logger.debug(f"Loaded {len(self._history)} notifications from history")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load notification history: {e}")
            return False


# Global notification manager instance
_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """
    Get the global notification manager instance.
    
    Returns:
        NotificationManager instance
    """
    global _notification_manager
    
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    
    return _notification_manager


# Convenience functions
def notify_success(title: str, message: str, **kwargs) -> None:
    """Send a success notification."""
    get_notification_manager().send_notification(title, message, NotificationLevel.SUCCESS, **kwargs)


def notify_error(title: str, message: str, **kwargs) -> None:
    """Send an error notification."""
    get_notification_manager().send_notification(title, message, NotificationLevel.ERROR, **kwargs)


def notify_warning(title: str, message: str, **kwargs) -> None:
    """Send a warning notification."""
    get_notification_manager().send_notification(title, message, NotificationLevel.WARNING, **kwargs)


def notify_info(title: str, message: str, **kwargs) -> None:
    """Send an info notification."""
    get_notification_manager().send_notification(title, message, NotificationLevel.INFO, **kwargs)
