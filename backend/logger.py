import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 10

current_log_date = None
logger = logging.getLogger("MonitorSystem")

def setup_logging():
    global current_log_date
    
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
        
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Determine filename based on current date
    current_date_str = datetime.now().strftime('%Y-%m-%d')
    current_log_date = current_date_str
    
    log_filename = f"monitor_{current_date_str}.log"
    log_file_path = os.path.join(LOG_DIR, log_filename)
    
    # File Handler: Rotating by size (10MB)
    file_handler = RotatingFileHandler(
        log_file_path, 
        maxBytes=MAX_LOG_SIZE, 
        backupCount=LOG_BACKUP_COUNT, 
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    logger.info(f"Logging initialized. Log file: {log_file_path}")
    return logger

def check_log_rotation():
    """Check if date has changed and rotate log file if necessary."""
    global current_log_date
    new_date_str = datetime.now().strftime('%Y-%m-%d')
    if new_date_str != current_log_date:
        logger.info(f"Date changed from {current_log_date} to {new_date_str}. Rotating log file.")
        setup_logging()

# Initialize logger on import, but setup_logging should be called explicitly or handled carefully
# To avoid side effects on import, we can do a basic init here or wait.
# For simplicity, let's allow it to be imported and used, but setup_logging does the heavy lifting.
# If setup_logging isn't called, it defaults to basicConfig or no logging depending on env.
# But we'll call setup_logging() in main.py startup.
