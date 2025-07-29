#!/usr/bin/env python3

import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional

def setup_logger(name: str, log_file: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with both file and console handlers.
    
    Args:
        name: Logger name
        log_file: Path to log file (defaults to logs/{name}.log)
        level: Logging level
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if logger already exists
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    
    # Default log file path
    if log_file is None:
        log_file = os.path.join(logs_dir, f"{name}.log")
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        fmt='%(levelname)s - %(message)s'
    )
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(detailed_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Only show warnings and errors on console
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_session_logger(session_id: Optional[str] = None) -> logging.Logger:
    """
    Get a session-specific logger.
    
    Args:
        session_id: Optional session identifier
    
    Returns:
        Session logger instance
    """
    if session_id is None:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    session_log_file = os.path.join("logs", "sessions", f"session_{session_id}.log")
    os.makedirs(os.path.dirname(session_log_file), exist_ok=True)
    
    return setup_logger(f"session_{session_id}", session_log_file)

# Default loggers
agent_logger = setup_logger("agent")
planner_logger = setup_logger("planner")
executor_logger = setup_logger("executor")
web_logger = setup_logger("web_server")