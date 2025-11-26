"""
Logger utility for CineAI Bot
Configures logging with rotation, formatting, and optional Sentry integration
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from app.config import config


def setup_logging() -> logging.Logger:
    """Setup logging configuration for the bot"""
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Get log level from config
    log_level = getattr(logging, config.bot_settings.LOG_LEVEL.upper(), logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        filename=logs_dir / "bot.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        filename=logs_dir / "errors.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # Bot-specific logger
    bot_logger = logging.getLogger("movie_bazar_bot")
    bot_logger.setLevel(log_level)

    # Set specific logger levels
    logging.getLogger("pyrogram").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # Log startup message
    bot_logger.info("Logging system initialized")
    bot_logger.info(f"Log level: {config.bot_settings.LOG_LEVEL}")
    bot_logger.info(f"Development mode: {config.bot_settings.DEVELOPMENT}")

    return bot_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name"""
    return logging.getLogger(f"cineai_bot.{name}")


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes"""

    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        return get_logger(self.__class__.__name__)


def log_function_call(func):
    """Decorator to log function calls"""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} returned successfully")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            raise
    return wrapper


def log_async_function_call(func):
    """Decorator to log async function calls"""
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"Calling async {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"Async {func.__name__} returned successfully")
            return result
        except Exception as e:
            logger.error(f"Error in async {func.__name__}: {e}", exc_info=True)
            raise
    return wrapper


class ContextLogger:
    """Context manager for logging operations with timing"""

    def __init__(self, logger: logging.Logger, operation: str, level: int = logging.INFO):
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time = None

    def __enter__(self):
        self.start_time = logging.time.time()
        self.logger.log(self.level, f"Starting {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = logging.time.time() - self.start_time
        if exc_type is None:
            self.logger.log(self.level, f"Completed {self.operation} in {duration:.2f}s")
        else:
            self.logger.error(f"Failed {self.operation} after {duration:.2f}s: {exc_val}")


def log_performance(logger: logging.Logger, operation: str):
    """Decorator to log performance of functions"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            with ContextLogger(logger, f"{operation} ({func.__name__})"):
                return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            with ContextLogger(logger, f"{operation} ({func.__name__})"):
                return func(*args, **kwargs)

        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # Check if async
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class StructuredLogger:
    """Structured logger for better log parsing"""

    def __init__(self, name: str):
        self.logger = get_logger(name)

    def log_user_action(self, user_id: int, action: str, details: Optional[dict] = None):
        """Log user action"""
        log_data = {
            "event": "user_action",
            "user_id": user_id,
            "action": action,
            "timestamp": logging.time.time()
        }
        if details:
            log_data.update(details)
        self.logger.info(f"USER_ACTION: {log_data}")

    def log_file_operation(self, file_id: str, operation: str, details: Optional[dict] = None):
        """Log file operation"""
        log_data = {
            "event": "file_operation",
            "file_id": file_id,
            "operation": operation,
            "timestamp": logging.time.time()
        }
        if details:
            log_data.update(details)
        self.logger.info(f"FILE_OPERATION: {log_data}")

    def log_error(self, error: Exception, context: Optional[dict] = None):
        """Log error with context"""
        log_data = {
            "event": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": logging.time.time()
        }
        if context:
            log_data.update(context)
        self.logger.error(f"ERROR: {log_data}", exc_info=True)

    def log_performance(self, operation: str, duration: float, details: Optional[dict] = None):
        """Log performance metrics"""
        log_data = {
            "event": "performance",
            "operation": operation,
            "duration_seconds": duration,
            "timestamp": logging.time.time()
        }
        if details:
            log_data.update(details)
        self.logger.info(f"PERFORMANCE: {log_data}")


def setup_sentry_logging() -> bool:
    """Sentry logging has been disabled"""
    return False


def get_log_stats() -> dict:
    """Get logging statistics"""
    try:
        logs_dir = Path("logs")
        stats = {}

        # Check log files
        for log_file in logs_dir.glob("*.log*"):
            if log_file.is_file():
                stats[log_file.name] = {
                    "size_bytes": log_file.stat().st_size,
                    "modified": log_file.stat().st_mtime
                }

        return stats

    except Exception as e:
        logger = get_logger("logger")
        logger.error(f"Error getting log stats: {e}")
        return {}


def cleanup_old_logs(days_to_keep: int = 30):
    """Clean up old log files"""
    try:
        logs_dir = Path("logs")
        cutoff_time = logging.time.time() - (days_to_keep * 24 * 60 * 60)

        deleted_count = 0
        for log_file in logs_dir.glob("*.log*"):
            if log_file.is_file() and log_file.stat().st_mtime < cutoff_time:
                log_file.unlink()
                deleted_count += 1

        logger = get_logger("logger")
        logger.info(f"Cleaned up {deleted_count} old log files")
        return deleted_count

    except Exception as e:
        logger = get_logger("logger")
        logger.error(f"Error cleaning up old logs: {e}")
        return 0


# Initialize logging on import
bot_logger = setup_logging()

