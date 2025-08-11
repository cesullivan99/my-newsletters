"""
Logging configuration for My Newsletters Voice Assistant
Provides structured logging with multiple handlers and formatters
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Optional
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "created", "filename", "funcName",
                          "levelname", "levelno", "lineno", "module", "exc_info",
                          "exc_text", "stack_info", "pathname", "processName",
                          "process", "threadName", "thread", "getMessage"]:
                log_obj[key] = value
        
        return json.dumps(log_obj)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    app_name: str = "my-newsletters",
    log_level: str = None,
    log_file: str = None,
    enable_console: bool = True,
    enable_file: bool = True,
    enable_json: bool = False
) -> logging.Logger:
    """
    Setup application logging with multiple handlers
    
    Args:
        app_name: Name of the application/logger
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        enable_console: Enable console logging
        enable_file: Enable file logging
        enable_json: Use JSON format for logs
    
    Returns:
        Configured logger instance
    """
    
    # Get configuration from environment
    log_level = log_level or os.getenv("LOG_LEVEL", "INFO")
    log_file = log_file or os.getenv("LOG_FILE", "logs/app.log")
    
    # Create logger
    logger = logging.getLogger(app_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        
        if enable_json:
            console_handler.setFormatter(JSONFormatter())
        else:
            # Use colored formatter for development
            if os.getenv("APP_ENV") == "development":
                console_format = ColoredFormatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            else:
                console_format = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            console_handler.setFormatter(console_format)
        
        logger.addHandler(console_handler)
    
    # File handler
    if enable_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Rotating file handler (10MB max, keep 5 backups)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        
        if enable_json:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_format)
        
        logger.addHandler(file_handler)
    
    # Error file handler (errors only)
    error_file = log_file.replace(".log", "_error.log")
    error_path = Path(error_file)
    error_path.parent.mkdir(parents=True, exist_ok=True)
    
    error_handler = logging.handlers.RotatingFileHandler(
        error_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s\n%(exc_info)s'
    )
    error_handler.setFormatter(error_format)
    logger.addHandler(error_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_performance(logger: logging.Logger):
    """
    Decorator to log function performance
    
    Args:
        logger: Logger instance to use
    """
    import functools
    import time
    
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.info(
                    f"{func.__name__} completed",
                    extra={
                        "function": func.__name__,
                        "duration_seconds": elapsed,
                        "status": "success"
                    }
                )
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    f"{func.__name__} failed",
                    extra={
                        "function": func.__name__,
                        "duration_seconds": elapsed,
                        "status": "error",
                        "error": str(e)
                    },
                    exc_info=True
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.info(
                    f"{func.__name__} completed",
                    extra={
                        "function": func.__name__,
                        "duration_seconds": elapsed,
                        "status": "success"
                    }
                )
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    f"{func.__name__} failed",
                    extra={
                        "function": func.__name__,
                        "duration_seconds": elapsed,
                        "status": "error",
                        "error": str(e)
                    },
                    exc_info=True
                )
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_api_request(logger: logging.Logger):
    """
    Decorator to log API requests and responses
    
    Args:
        logger: Logger instance to use
    """
    import functools
    import time
    from quart import request
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Log request
            logger.info(
                f"API Request: {request.method} {request.path}",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "query_params": dict(request.args),
                    "remote_addr": request.remote_addr,
                    "user_agent": request.headers.get("User-Agent")
                }
            )
            
            try:
                response = await func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                # Log response
                status_code = response[1] if isinstance(response, tuple) else 200
                logger.info(
                    f"API Response: {status_code}",
                    extra={
                        "method": request.method,
                        "path": request.path,
                        "status_code": status_code,
                        "duration_seconds": elapsed
                    }
                )
                
                return response
                
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    f"API Error: {str(e)}",
                    extra={
                        "method": request.method,
                        "path": request.path,
                        "duration_seconds": elapsed,
                        "error": str(e)
                    },
                    exc_info=True
                )
                raise
        
        return wrapper
    
    return decorator


# Initialize default logger
default_logger = setup_logging()


# Utility functions for common logging patterns
def log_error(message: str, error: Exception, **kwargs):
    """Log an error with exception details"""
    default_logger.error(
        message,
        extra={**kwargs, "error_type": type(error).__name__, "error_message": str(error)},
        exc_info=True
    )


def log_warning(message: str, **kwargs):
    """Log a warning message"""
    default_logger.warning(message, extra=kwargs)


def log_info(message: str, **kwargs):
    """Log an info message"""
    default_logger.info(message, extra=kwargs)


def log_debug(message: str, **kwargs):
    """Log a debug message"""
    default_logger.debug(message, extra=kwargs)