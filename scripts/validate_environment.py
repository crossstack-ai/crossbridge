#!/usr/bin/env python3
"""
Environment Variable Validation Script

Validates that required environment variables are set and properly configured.
"""

import os
import sys
from typing import List, Dict, Tuple


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.ENDC}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓{Colors.ENDC} {text}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.ENDC} {text}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗{Colors.ENDC} {text}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ{Colors.ENDC} {text}")


def check_variable(var_name: str, required: bool = True, description: str = "") -> bool:
    """
    Check if an environment variable is set.
    
    Args:
        var_name: Name of the environment variable
        required: Whether the variable is required
        description: Description of what the variable is for
        
    Returns:
        bool: True if validation passed
    """
    value = os.getenv(var_name)
    
    if value:
        # Mask sensitive values
        if 'KEY' in var_name or 'PASSWORD' in var_name or 'TOKEN' in var_name:
            display_value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
        else:
            display_value = value
            
        print_success(f"{var_name} is set: {display_value}")
        return True
    else:
        if required:
            print_error(f"{var_name} is NOT set (Required)")
            if description:
                print(f"  {description}")
            return False
        else:
            print_warning(f"{var_name} is not set (Optional)")
            if description:
                print(f"  {description}")
            return True


def validate_database_config() -> Tuple[bool, List[str]]:
    """Validate database configuration."""
    print_header("Database Configuration")
    
    errors = []
    required_vars = {
        'DB_HOST': 'PostgreSQL server hostname',
        'DB_NAME': 'Database name',
        'DB_USER': 'Database username',
        'DB_PASSWORD': 'Database password'
    }
    
    optional_vars = {
        'DB_PORT': 'PostgreSQL port (default: 5432)',
        'DB_SSL_MODE': 'SSL mode (default: prefer)',
        'DB_POOL_SIZE': 'Connection pool size (default: 10)',
    }
    
    # Check required variables
    all_required_set = True
    for var, desc in required_vars.items():
        if not check_variable(var, required=True, description=desc):
            errors.append(f"Missing required variable: {var}")
            all_required_set = False
    
    # Check optional variables
    print()
    for var, desc in optional_vars.items():
        check_variable(var, required=False, description=desc)
    
    # Test database connection if all required vars are set
    if all_required_set:
        print()
        print_info("Testing database connection...")
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST'),
                port=os.getenv('DB_PORT', '5432'),
                dbname=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                connect_timeout=5
            )
            conn.close()
            print_success("Database connection successful!")
        except ImportError:
            print_warning("psycopg2 not installed - skipping connection test")
            print_info("Install with: pip install psycopg2-binary")
        except Exception as e:
            print_error(f"Database connection failed: {e}")
            errors.append(f"Database connection error: {str(e)}")
    else:
        print_warning("Skipping database connection test (missing required variables)")
    
    return len(errors) == 0, errors


def validate_ai_providers() -> Tuple[bool, List[str]]:
    """Validate AI provider configuration."""
    print_header("AI Provider Configuration")
    
    errors = []
    warnings = []
    
    # Check for at least one AI provider
    providers = {
        'OpenAI': 'OPENAI_API_KEY',
        'Anthropic': 'ANTHROPIC_API_KEY',
        'Azure OpenAI': 'AZURE_OPENAI_KEY',
    }
    
    configured_providers = []
    for provider_name, var_name in providers.items():
        if check_variable(var_name, required=False, description=f"{provider_name} API key"):
            configured_providers.append(provider_name)
            
            # Check related variables
            if provider_name == 'Azure OpenAI':
                check_variable('AZURE_OPENAI_ENDPOINT', required=False, description="Azure endpoint URL")
                check_variable('AZURE_OPENAI_DEPLOYMENT', required=False, description="Azure deployment name")
    
    print()
    if not configured_providers:
        print_error("No AI providers configured!")
        print_info("Configure at least one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, or AZURE_OPENAI_KEY")
        errors.append("No AI providers configured")
    else:
        print_success(f"Configured AI providers: {', '.join(configured_providers)}")
    
    # Check optional AI configuration
    print()
    optional_ai_vars = {
        'OPENAI_DEFAULT_MODEL': 'Default OpenAI model (default: gpt-4)',
        'ANTHROPIC_DEFAULT_MODEL': 'Default Anthropic model (default: claude-3-5-sonnet)',
        'AI_DAILY_COST_LIMIT': 'Daily cost limit in USD',
        'AI_MONTHLY_COST_LIMIT': 'Monthly cost limit in USD',
    }
    
    for var, desc in optional_ai_vars.items():
        check_variable(var, required=False, description=desc)
    
    return len(errors) == 0, errors


def validate_optional_features() -> Tuple[bool, List[str]]:
    """Validate optional feature configuration."""
    print_header("Optional Features")
    
    warnings = []
    
    optional_features = {
        'Repository Integration': {
            'BITBUCKET_USERNAME': 'Bitbucket username',
            'BITBUCKET_PASSWORD': 'Bitbucket app password',
            'GITHUB_TOKEN': 'GitHub personal access token',
        },
        'Grafana Integration': {
            'GRAFANA_URL': 'Grafana server URL',
            'GRAFANA_API_KEY': 'Grafana API key',
        },
        'Application Settings': {
            'LOG_LEVEL': 'Logging level (default: INFO)',
            'LOG_FILE': 'Log file path',
            'CACHE_DIR': 'Cache directory path',
        },
        'Feature Flags': {
            'ENABLE_AI_FEATURES': 'Enable AI features (default: true)',
            'ENABLE_FLAKY_DETECTION': 'Enable flaky test detection (default: true)',
            'ENABLE_PROFILING': 'Enable performance profiling (default: true)',
        }
    }
    
    for feature_name, variables in optional_features.items():
        print(f"\n{Colors.BOLD}{feature_name}:{Colors.ENDC}")
        for var, desc in variables.items():
            check_variable(var, required=False, description=desc)
    
    return True, warnings


def validate_security() -> Tuple[bool, List[str]]:
    """Validate security configuration."""
    print_header("Security Checks")
    
    warnings = []
    
    # Check .env file permissions
    env_file = '.env'
    if os.path.exists(env_file):
        import stat
        st = os.stat(env_file)
        mode = st.st_mode
        
        # Check if file is readable by others
        if mode & stat.S_IROTH:
            print_warning(f"{env_file} is readable by others")
            print_info(f"  Fix with: chmod 600 {env_file}")
            warnings.append(".env file has insecure permissions")
        else:
            print_success(f"{env_file} has secure permissions")
    else:
        print_warning(f"{env_file} not found")
        print_info("  Copy from .env.example: cp .env.example .env")
    
    # Check for hardcoded secrets in common locations
    print()
    print_info("Checking for hardcoded secrets...")
    
    check_files = ['crossbridge.yaml', 'crossbridge.yml', 'config.yaml']
    for file in check_files:
        if os.path.exists(file):
            with open(file, 'r') as f:
                content = f.read()
                if 'sk-' in content or 'password:' in content.lower():
                    print_warning(f"Possible hardcoded secrets in {file}")
                    warnings.append(f"Check {file} for hardcoded secrets")
                else:
                    print_success(f"{file} looks clean")
    
    return True, warnings


def main():
    """Main validation function."""
    print()
    print(f"{Colors.BOLD}CrossBridge Environment Validation{Colors.ENDC}")
    print(f"{Colors.BOLD}Version 0.1.1{Colors.ENDC}")
    
    all_errors = []
    all_warnings = []
    
    # Run all validations
    db_ok, db_errors = validate_database_config()
    all_errors.extend(db_errors)
    
    ai_ok, ai_errors = validate_ai_providers()
    all_errors.extend(ai_errors)
    
    features_ok, feature_warnings = validate_optional_features()
    all_warnings.extend(feature_warnings)
    
    security_ok, security_warnings = validate_security()
    all_warnings.extend(security_warnings)
    
    # Print summary
    print_header("Validation Summary")
    
    if all_errors:
        print_error(f"Found {len(all_errors)} error(s):")
        for error in all_errors:
            print(f"  • {error}")
        print()
    
    if all_warnings:
        print_warning(f"Found {len(all_warnings)} warning(s):")
        for warning in all_warnings:
            print(f"  • {warning}")
        print()
    
    if not all_errors:
        if db_ok and ai_ok:
            print_success("All required environment variables are properly configured!")
            print_success("CrossBridge is ready to use!")
        else:
            print_warning("Some issues found, but CrossBridge may still work with limited features")
    else:
        print_error("Environment validation failed!")
        print_info("Fix the errors above and run this script again")
        sys.exit(1)
    
    print()
    print_info("For more information, see: docs/ENVIRONMENT_VARIABLES.md")
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nValidation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
