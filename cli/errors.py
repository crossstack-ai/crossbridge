"""
Error handling for CrossBridge CLI.

User-friendly error messages with:
- Clear descriptions
- Actionable suggestions
- Error codes for tracking
- Hidden stack traces (in log file only)
"""

from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class CrossBridgeError(Exception):
    """Base exception for CrossBridge errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        suggestion: Optional[str] = None
    ):
        self.message = message
        self.error_code = error_code
        self.suggestion = suggestion
        super().__init__(message)


class CommandError(CrossBridgeError):
    """Command execution error."""
    
    def __init__(self, message: str, suggestion: Optional[str] = None):
        super().__init__(message, "CMD_ERROR", suggestion)


class AuthenticationError(CrossBridgeError):
    """Authentication/authorization failed."""
    
    def __init__(self, message: str, suggestion: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="CS-AUTH-001",
            suggestion=suggestion or "Check your credentials and repository permissions"
        )


class RepositoryError(CrossBridgeError):
    """Repository access or operation failed."""
    
    def __init__(self, message: str, suggestion: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="CS-REPO-001",
            suggestion=suggestion or "Verify repository URL and branch name"
        )


class TransformationError(CrossBridgeError):
    """File transformation failed."""
    
    def __init__(self, message: str, suggestion: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="CS-TRANSFORM-001",
            suggestion=suggestion or "Review source files for compatibility issues"
        )


class AIServiceError(CrossBridgeError):
    """AI service unavailable or failed."""
    
    def __init__(self, message: str, suggestion: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="CS-AI-001",
            suggestion=suggestion or "Check AI service configuration and connectivity"
        )


class ConfigurationError(CrossBridgeError):
    """Configuration invalid or missing."""
    
    def __init__(self, message: str, suggestion: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="CS-CONFIG-001",
            suggestion=suggestion or "Review configuration file or command-line arguments"
        )


# Error code to suggestion mapping
ERROR_SUGGESTIONS: Dict[str, str] = {
    "CS-AUTH-001": "Check your credentials and repository permissions. Ensure your token has read/write access.",
    "CS-REPO-001": "Verify the repository URL is correct and the branch exists. Check network connectivity.",
    "CS-TRANSFORM-001": "Source files may have unsupported syntax or structure. Review compatibility requirements.",
    "CS-AI-001": "AI service is unavailable. Check API key, endpoint configuration, and network connectivity.",
    "CS-CONFIG-001": "Configuration is invalid. Review required fields and value formats.",
    "CS-UNKNOWN-001": "An unexpected error occurred. Check logs for details."
}


def get_user_friendly_error(
    error: Exception,
    error_code: Optional[str] = None
) -> Dict[str, str]:
    """
    Convert exception to user-friendly error message.
    
    Args:
        error: Original exception
        error_code: Optional error code
    
    Returns:
        Dict with message, code, and suggestion
    """
    # CrossBridge errors already have user-friendly messages
    if isinstance(error, CrossBridgeError):
        return {
            "message": error.message,
            "code": error.error_code,
            "suggestion": error.suggestion
        }
    
    # Map common exceptions
    error_type = type(error).__name__
    message = str(error)
    
    # Infer error code from exception type or message
    if not error_code:
        error_code = _infer_error_code(error)
    
    # Get suggestion
    suggestion = ERROR_SUGGESTIONS.get(error_code, ERROR_SUGGESTIONS["CS-UNKNOWN-001"])
    
    # Simplify technical messages
    if "connection" in message.lower() or "timeout" in message.lower():
        message = "Network connection failed"
        suggestion = "Check your internet connection and firewall settings"
    
    elif "authentication" in message.lower() or "unauthorized" in message.lower():
        message = "Authentication failed"
        error_code = "CS-AUTH-001"
    
    elif "not found" in message.lower() or "404" in message:
        message = "Repository or resource not found"
        error_code = "CS-REPO-001"
    
    return {
        "message": message,
        "code": error_code,
        "suggestion": suggestion
    }


def _infer_error_code(error: Exception) -> str:
    """Infer error code from exception."""
    error_msg = str(error).lower()
    error_type = type(error).__name__.lower()
    
    if "auth" in error_msg or "token" in error_msg or "permission" in error_msg:
        return "CS-AUTH-001"
    
    elif "repository" in error_msg or "repo" in error_msg or "branch" in error_msg:
        return "CS-REPO-001"
    
    elif "transform" in error_msg or "parse" in error_msg or "syntax" in error_msg:
        return "CS-TRANSFORM-001"
    
    elif "ai" in error_msg or "openai" in error_msg or "anthropic" in error_msg:
        return "CS-AI-001"
    
    elif "config" in error_msg or "setting" in error_msg:
        return "CS-CONFIG-001"
    
    else:
        return "CS-UNKNOWN-001"


def log_error(error: Exception, context: Optional[str] = None):
    """
    Log error with full details to file.
    
    Args:
        error: Exception to log
        context: Optional context description
    """
    if context:
        logger.error(f"Error in {context}: {error}", exc_info=True)
    else:
        logger.error(f"Error: {error}", exc_info=True)


def handle_cli_error(error: Exception, context: Optional[str] = None):
    """
    Handle CLI error with user-friendly display and logging.
    
    Args:
        error: Exception to handle
        context: Optional context description
    """
    # Log full error details to file
    log_error(error, context)
    
    # Get user-friendly error information
    error_info = get_user_friendly_error(error)
    
    # Display to user
    print(f"\n❌ Error: {error_info['message']}")
    if context:
        print(f"   Context: {context}")
    print(f"   Code: {error_info['code']}")
    if error_info.get('suggestion'):
        print(f"   💡 Suggestion: {error_info['suggestion']}")
    print()
