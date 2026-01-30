"""
Configuration for Deterministic + AI Behavior System.

This module defines configuration for:
- Deterministic classifier thresholds
- AI enrichment behavior
- Fallback policies
- Observability settings
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import yaml
import os


@dataclass
class DeterministicConfig:
    """Configuration for deterministic classifier."""
    
    # Classification thresholds
    flaky_threshold: float = 0.1  # 10% failure rate
    unstable_threshold: float = 0.4  # 40% failure rate
    min_runs_for_confidence: int = 5
    
    # Confidence adjustments
    high_confidence_min_runs: int = 10
    low_confidence_max_runs: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class AIBehaviorConfig:
    """Configuration for AI enrichment behavior."""
    
    # Feature flags
    enabled: bool = True
    enrichment: bool = True
    
    # Timeouts and limits
    timeout_ms: int = 2000
    min_confidence: float = 0.5
    
    # Failure handling
    fail_open: bool = True  # Return deterministic result on AI failure
    
    # Model configuration
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 500
    
    # Retry behavior
    max_retries: int = 1
    retry_delay_ms: int = 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ObservabilityConfig:
    """Configuration for metrics and logging."""
    
    # Metrics collection
    metrics_enabled: bool = True
    metrics_prefix: str = "crossbridge.intelligence"
    
    # Logging
    log_level: str = "INFO"
    log_ai_prompts: bool = False  # Set to True for debugging
    log_ai_responses: bool = False
    
    # Performance tracking
    track_latency: bool = True
    latency_percentiles: list = None
    
    def __post_init__(self):
        if self.latency_percentiles is None:
            self.latency_percentiles = [50, 90, 95, 99]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class IntelligenceConfig:
    """
    Master configuration for Deterministic + AI system.
    
    This class loads and manages all configuration for:
    - Deterministic classification
    - AI enrichment
    - Observability
    
    Configuration precedence:
    1. Environment variables
    2. Config file (YAML)
    3. Defaults
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Optional path to YAML config file
        """
        self.deterministic = DeterministicConfig()
        self.ai = AIBehaviorConfig()
        self.observability = ObservabilityConfig()
        
        # Load from file if provided
        if config_path and os.path.exists(config_path):
            self._load_from_file(config_path)
        
        # Override with environment variables
        self._load_from_env()
    
    def _load_from_file(self, config_path: str):
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Load deterministic config
            if 'deterministic' in config_data:
                det_config = config_data['deterministic']
                for key, value in det_config.items():
                    if hasattr(self.deterministic, key):
                        setattr(self.deterministic, key, value)
            
            # Load AI config
            if 'ai' in config_data:
                ai_config = config_data['ai']
                for key, value in ai_config.items():
                    if hasattr(self.ai, key):
                        setattr(self.ai, key, value)
            
            # Load observability config
            if 'observability' in config_data:
                obs_config = config_data['observability']
                for key, value in obs_config.items():
                    if hasattr(self.observability, key):
                        setattr(self.observability, key, value)
        
        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        # AI configuration
        if os.getenv('CROSSBRIDGE_AI_ENABLED'):
            self.ai.enabled = os.getenv('CROSSBRIDGE_AI_ENABLED').lower() == 'true'
        
        if os.getenv('CROSSBRIDGE_AI_ENRICHMENT'):
            self.ai.enrichment = os.getenv('CROSSBRIDGE_AI_ENRICHMENT').lower() == 'true'
        
        if os.getenv('CROSSBRIDGE_AI_TIMEOUT_MS'):
            self.ai.timeout_ms = int(os.getenv('CROSSBRIDGE_AI_TIMEOUT_MS'))
        
        if os.getenv('CROSSBRIDGE_AI_MIN_CONFIDENCE'):
            self.ai.min_confidence = float(os.getenv('CROSSBRIDGE_AI_MIN_CONFIDENCE'))
        
        if os.getenv('CROSSBRIDGE_AI_MODEL'):
            self.ai.model = os.getenv('CROSSBRIDGE_AI_MODEL')
        
        # Deterministic configuration
        if os.getenv('CROSSBRIDGE_FLAKY_THRESHOLD'):
            self.deterministic.flaky_threshold = float(os.getenv('CROSSBRIDGE_FLAKY_THRESHOLD'))
        
        if os.getenv('CROSSBRIDGE_UNSTABLE_THRESHOLD'):
            self.deterministic.unstable_threshold = float(os.getenv('CROSSBRIDGE_UNSTABLE_THRESHOLD'))
    
    def to_dict(self) -> Dict[str, Any]:
        """Export full configuration as dictionary."""
        return {
            'deterministic': self.deterministic.to_dict(),
            'ai': self.ai.to_dict(),
            'observability': self.observability.to_dict()
        }
    
    def to_yaml(self, output_path: str):
        """Export configuration to YAML file."""
        with open(output_path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)
    
    @classmethod
    def create_example_config(cls, output_path: str):
        """Create example configuration file with documentation."""
        config = cls()
        
        example_yaml = """# Crossbridge Intelligence Configuration
# Deterministic + AI Behavior System

# Deterministic Classifier Configuration
deterministic:
  # Failure rate thresholds
  flaky_threshold: 0.1        # 10% failure rate = flaky
  unstable_threshold: 0.4     # 40% failure rate = unstable
  min_runs_for_confidence: 5  # Minimum runs for high confidence
  
  # Confidence adjustments
  high_confidence_min_runs: 10
  low_confidence_max_runs: 3

# AI Enrichment Configuration
ai:
  # Feature flags
  enabled: true               # Enable/disable AI entirely
  enrichment: true            # Enable AI enrichment layer
  
  # Timeouts and limits
  timeout_ms: 2000            # Max time for AI call (ms)
  min_confidence: 0.5         # Minimum AI confidence to use results
  
  # Failure handling
  fail_open: true             # Return deterministic result on AI failure
  
  # Model configuration
  model: "gpt-4o-mini"        # AI model to use
  temperature: 0.3            # Lower = more deterministic
  max_tokens: 500             # Max response length
  
  # Retry behavior
  max_retries: 1
  retry_delay_ms: 100

# Observability Configuration
observability:
  # Metrics
  metrics_enabled: true
  metrics_prefix: "crossbridge.intelligence"
  
  # Logging
  log_level: "INFO"
  log_ai_prompts: false       # Set true for debugging
  log_ai_responses: false
  
  # Performance tracking
  track_latency: true
  latency_percentiles: [50, 90, 95, 99]
"""
        
        with open(output_path, 'w') as f:
            f.write(example_yaml)


# Global config instance (lazy-loaded)
_config_instance: Optional[IntelligenceConfig] = None


def get_config(config_path: Optional[str] = None) -> IntelligenceConfig:
    """
    Get global configuration instance.
    
    Args:
        config_path: Optional path to config file (only used on first call)
        
    Returns:
        IntelligenceConfig instance
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = IntelligenceConfig(config_path)
    
    return _config_instance


def reset_config():
    """Reset global configuration (useful for testing)."""
    global _config_instance
    _config_instance = None
