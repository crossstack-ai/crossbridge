"""
Enhanced logging configuration with Phase 3 support.

Adds logging for new modules: Behave, SpecFlow, Cypress, RestAssured.
"""

import logging
import logging.config
from pathlib import Path
from typing import Dict


def get_enhanced_logging_config() -> Dict:
    """
    Get enhanced logging configuration with Phase 3 module support.
    
    Returns:
        Dictionary logging configuration
    """
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
            },
            'json': {
                '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'default',
                'stream': 'ext://sys.stdout',
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': 'logs/crossbridge.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
            },
            'error_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'detailed',
                'filename': 'logs/crossbridge_errors.log',
                'maxBytes': 10485760,
                'backupCount': 5,
            },
            'ai_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filename': 'logs/ai.log',
                'maxBytes': 10485760,
                'backupCount': 3,
            },
        },
        'loggers': {
            # Root logger
            '': {
                'level': 'INFO',
                'handlers': ['console', 'file', 'error_file'],
            },
            # Core modules
            'core': {
                'level': 'DEBUG',
                'handlers': ['file'],
                'propagate': False,
            },
            'core.ai': {
                'level': 'DEBUG',
                'handlers': ['ai_file'],
                'propagate': False,
            },
            # Adapter loggers
            'adapters': {
                'level': 'DEBUG',
                'handlers': ['file'],
                'propagate': False,
            },
            'adapters.java': {
                'level': 'DEBUG',
                'handlers': ['file'],
                'propagate': False,
            },
            'adapters.selenium_pytest': {
                'level': 'DEBUG',
                'handlers': ['file'],
                'propagate': False,
            },
            'adapters.selenium_behave': {
                'level': 'DEBUG',
                'handlers': ['file'],
                'propagate': False,
            },
            'adapters.selenium_specflow_dotnet': {
                'level': 'DEBUG',
                'handlers': ['file'],
                'propagate': False,
            },
            'adapters.cypress': {
                'level': 'DEBUG',
                'handlers': ['file'],
                'propagate': False,
            },
            'adapters.restassured_java': {
                'level': 'DEBUG',
                'handlers': ['file'],
                'propagate': False,
            },
            'adapters.robot': {
                'level': 'DEBUG',
                'handlers': ['file'],
                'propagate': False,
            },
            'adapters.playwright': {
                'level': 'DEBUG',
                'handlers': ['file'],
                'propagate': False,
            },
            # Migration and orchestration
            'core.orchestration': {
                'level': 'DEBUG',
                'handlers': ['file'],
                'propagate': False,
            },
            'core.translation': {
                'level': 'DEBUG',
                'handlers': ['file'],
                'propagate': False,
            },
        },
    }
    
    return config


def setup_enhanced_logging(log_dir: str = 'logs', log_level: str = 'INFO'):
    """
    Set up enhanced logging with Phase 3 support.
    
    Args:
        log_dir: Directory for log files
        log_level: Minimum log level
    """
    # Create log directory if it doesn't exist
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Get config
    config = get_enhanced_logging_config()
    
    # Update log level if specified
    if log_level:
        level = getattr(logging, log_level.upper(), logging.INFO)
        config['loggers']['']['level'] = level
    
    # Apply configuration
    logging.config.dictConfig(config)
    
    # Get logger and log setup
    logger = logging.getLogger(__name__)
    logger.info(f"Enhanced logging configured - Level: {log_level}, Directory: {log_dir}")
    logger.debug("Phase 3 module loggers enabled: Behave, SpecFlow, Cypress, RestAssured, Robot, Playwright")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Module-specific logger getters
def get_behave_logger() -> logging.Logger:
    """Get logger for Behave adapter."""
    return logging.getLogger('adapters.selenium_behave')


def get_specflow_logger() -> logging.Logger:
    """Get logger for SpecFlow adapter."""
    return logging.getLogger('adapters.selenium_specflow_dotnet')


def get_cypress_logger() -> logging.Logger:
    """Get logger for Cypress adapter."""
    return logging.getLogger('adapters.cypress')


def get_restassured_logger() -> logging.Logger:
    """Get logger for RestAssured adapter."""
    return logging.getLogger('adapters.restassured_java')


def get_robot_logger() -> logging.Logger:
    """Get logger for Robot Framework adapter."""
    return logging.getLogger('adapters.robot')


def get_playwright_logger() -> logging.Logger:
    """Get logger for Playwright adapter."""
    return logging.getLogger('adapters.playwright')


def get_ai_logger() -> logging.Logger:
    """Get logger for AI modules."""
    return logging.getLogger('core.ai')
