# File: src/utils/logging.py
import os
import sys
import logging

def setup_logger():
    """
    Configures and returns a logger based on LOG_FILE and LOG_LEVEL
    environment variables, as required by the project specification.
    """
    log_file = os.environ.get("LOG_FILE")
    try:
        # LOG_LEVEL=0 is silent, 1 is INFO, 2 is DEBUG
        log_level_env = int(os.environ.get("LOG_LEVEL", "0"))
    except ValueError:
        log_level_env = 0

    # Create a logger instance
    logger = logging.getLogger("phase1_cli")

    # Prevent logs from being propagated to the root logger
    logger.propagate = False

    # Set the level based on the environment variable
    if log_level_env == 1:
        logger.setLevel(logging.INFO)
    elif log_level_env >= 2:
        logger.setLevel(logging.DEBUG)
    else:
        # For LOG_LEVEL=0, set a level that will not log anything
        logger.setLevel(logging.CRITICAL + 1)

    # Remove any existing handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create and configure the handler (file or console)
    handler = None
    if log_file and log_level_env > 0:
        try:
            # This will not crash if the path is invalid
            handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
        except Exception:
            # If the file path is invalid, fall back to console
            handler = logging.StreamHandler(sys.stderr)
    elif log_level_env > 0:
        # Default to stderr if no log file is specified
        handler = logging.StreamHandler(sys.stderr)

    if handler:
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

# Create a single logger instance that can be imported by other files
logger = setup_logger()