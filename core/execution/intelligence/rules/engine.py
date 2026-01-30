"""
Rule Engine

Applies rules to failure signals and determines classifications.
"""

from typing import List, Optional
from pathlib import Path
import yaml
import logging

from core.execution.intelligence.rules.models import Rule, RulePack

logger = logging.getLogger(__name__)


class RuleEngine:
    """
    Engine for applying classification rules.
    
    Loads framework-specific rule packs and applies them to failure signals.
    """
    
    def __init__(self, framework: Optional[str] = None):
        """
        Initialize rule engine.
        
        Args:
            framework: Framework name for loading framework-specific rules
        """
        self.framework = framework
        self.rule_pack = self._load_rules(framework)
    
    def _load_rules(self, framework: Optional[str]) -> RulePack:
        """
        Load rules for specified framework.
        
        Args:
            framework: Framework name (e.g., "selenium", "pytest")
            
        Returns:
            RulePack with loaded rules
        """
        if framework:
            try:
                return load_rule_pack(framework)
            except Exception as e:
                logger.warning(f"Failed to load rules for {framework}: {e}, using generic rules")
        
        # Fall back to generic rules
        return load_rule_pack("generic")
    
    def apply_rules(self, signals: List) -> List[Rule]:
        """
        Apply rules to failure signals.
        
        Args:
            signals: List of FailureSignal objects
            
        Returns:
            List of matched rules, sorted by priority
        """
        matched_rules = []
        
        for signal in signals:
            message = signal.message if hasattr(signal, 'message') else str(signal)
            matching = self.rule_pack.find_matching_rules(message)
            matched_rules.extend(matching)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_rules = []
        for rule in matched_rules:
            if rule.id not in seen:
                seen.add(rule.id)
                unique_rules.append(rule)
        
        return unique_rules
    
    def classify(self, signals: List) -> tuple[str, float, List[Rule]]:
        """
        Classify failure based on signals.
        
        Args:
            signals: List of failure signals
            
        Returns:
            Tuple of (failure_type, confidence, matched_rules)
        """
        matched_rules = self.apply_rules(signals)
        
        if not matched_rules:
            return "UNKNOWN", 0.2, []
        
        # Use highest confidence rule
        best_rule = max(matched_rules, key=lambda r: r.confidence)
        
        return best_rule.failure_type, best_rule.confidence, matched_rules


def load_rule_pack(framework: str, config_file: str = None) -> RulePack:
    """
    Load rule pack from crossbridge.yml or fallback to framework-specific YAML file.
    
    Priority:
    1. crossbridge.yml (execution.intelligence.rules.<framework>)
    2. Framework-specific YAML file (rules/<framework>.yaml)
    3. Generic fallback
    
    Args:
        framework: Framework name (e.g., "selenium", "pytest", "generic")
        config_file: Path to crossbridge.yml (optional, auto-detected if None)
        
    Returns:
        RulePack with loaded rules
    """
    # Try loading from crossbridge.yml first
    try:
        rules_from_config = _load_rules_from_crossbridge_config(framework, config_file)
        if rules_from_config:
            logger.info(f"Loaded {len(rules_from_config.rules)} {framework} rules from crossbridge.yml")
            return rules_from_config
    except Exception as e:
        logger.debug(f"Could not load rules from crossbridge.yml: {e}")
    
    # Fallback to framework-specific YAML file
    rules_dir = Path(__file__).parent
    rule_file = rules_dir / f"{framework}.yaml"
    
    if not rule_file.exists():
        logger.warning(f"Rule file not found: {rule_file}, using generic")
        rule_file = rules_dir / "generic.yaml"
    
    if not rule_file.exists():
        # Return minimal rule pack
        return RulePack(name=framework, rules=[], description="No rules available")
    
    try:
        with open(rule_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data:
            return RulePack(name=framework, rules=[])
        
        # Handle both dict format (with metadata) and list format (direct rules)
        if isinstance(data, list):
            rule_count = len(data)
        else:
            rule_count = len(data.get('rules', []))
        
        logger.info(f"Loaded {rule_count} {framework} rules from {rule_file.name}")
        return _parse_rule_data(data, framework)
    
    except Exception as e:
        logger.error(f"Failed to load rule pack from {rule_file}: {e}")
        return RulePack(name=framework, rules=[])


def _load_rules_from_crossbridge_config(framework: str, config_file: str = None) -> Optional[RulePack]:
    """
    Load rules from crossbridge.yml configuration file.
    
    Looks for rules in: execution.intelligence.rules.<framework>
    
    Args:
        framework: Framework name
        config_file: Path to crossbridge.yml (auto-detected if None)
        
    Returns:
        RulePack if found, None otherwise
    """
    # Auto-detect crossbridge.yml location
    if config_file is None:
        # Try common locations
        possible_paths = [
            Path.cwd() / "crossbridge.yml",
            Path.cwd() / "crossbridge.yaml",
            Path(__file__).parent.parent.parent.parent.parent / "crossbridge.yml",
            Path.home() / ".crossbridge" / "crossbridge.yml"
        ]
        
        for path in possible_paths:
            if path.exists():
                config_file = str(path)
                logger.debug(f"Found crossbridge config at: {config_file}")
                break
        
        if config_file is None:
            logger.debug("No crossbridge config file found")
            return None
    
    # Load crossbridge.yml
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.debug(f"Failed to load crossbridge config: {e}")
        return None
    
    if not config:
        return None
    
    # Navigate to intelligence.rules.<framework>
    # Try multiple possible paths in crossbridge.yml:
    # 1. crossbridge.intelligence.rules.<framework> (standard)
    # 2. crossbridge.execution.intelligence.rules.<framework> (alternative)
    # 3. execution.intelligence.rules.<framework> (flat structure)
    # 4. intelligence.rules.<framework> (simple structure)
    rules_data = None
    
    # Try path 1: crossbridge.intelligence.rules.<framework>
    if 'crossbridge' in config:
        rules_data = (config.get('crossbridge', {})
                            .get('intelligence', {})
                            .get('rules', {})
                            .get(framework))
    
    # Try path 2: crossbridge.execution.intelligence.rules.<framework>
    if not rules_data and 'crossbridge' in config:
        rules_data = (config.get('crossbridge', {})
                            .get('execution', {})
                            .get('intelligence', {})
                            .get('rules', {})
                            .get(framework))
    
    # Try path 3: execution.intelligence.rules.<framework>
    if not rules_data:
        rules_data = (config.get('execution', {})
                            .get('intelligence', {})
                            .get('rules', {})
                            .get(framework))
    
    # Try path 4: intelligence.rules.<framework>
    if not rules_data:
        rules_data = (config.get('intelligence', {})
                            .get('rules', {})
                            .get(framework))
    
    if not rules_data:
        logger.debug(f"No rules found for {framework} in crossbridge.yml")
        return None
    
    logger.debug(f"Found {len(rules_data) if isinstance(rules_data, list) else '?'} rules for {framework} in crossbridge.yml")
    
    # Parse rules
    return _parse_rule_data(rules_data, framework)


def _parse_rule_data(data: any, framework: str) -> RulePack:
    """
    Parse rule data into RulePack object.
    
    Supports both list format (direct rules) and dict format (with metadata).
    
    Args:
        data: Rule data (list or dict)
        framework: Framework name
        
    Returns:
        RulePack with parsed rules
    """
    if not data:
        return RulePack(name=framework, rules=[])
    
    # Handle both list format and dict format
    rules = []
    rule_list = data if isinstance(data, list) else data.get('rules', [])
    
    for rule_data in rule_list:
        # Ensure match_any, requires_all, and excludes are lists of strings
        match_any = rule_data.get('match_any', [])
        if not isinstance(match_any, list):
            match_any = [match_any] if match_any else []
        
        requires_all = rule_data.get('requires_all', [])
        if not isinstance(requires_all, list):
            requires_all = [requires_all] if requires_all else []
        
        excludes = rule_data.get('excludes', [])
        if not isinstance(excludes, list):
            excludes = [excludes] if excludes else []
        
        rule = Rule(
            id=rule_data['id'],
            match_any=match_any,
            failure_type=rule_data['failure_type'],
            confidence=rule_data['confidence'],
            priority=rule_data.get('priority', 100),
            description=rule_data.get('description', ''),
            framework=rule_data.get('framework'),
            requires_all=requires_all,
            excludes=excludes
        )
        rules.append(rule)
    
    # Get metadata
    pack_name = data.get('name', framework) if isinstance(data, dict) else framework
    pack_version = data.get('version', '1.0.0') if isinstance(data, dict) else '1.0.0'
    pack_desc = data.get('description', '') if isinstance(data, dict) else ''
    
    return RulePack(
        name=pack_name,
        rules=rules,
        version=pack_version,
        description=pack_desc
    )


def apply_rules(signals: List, rules: List[Rule]) -> List[Rule]:
    """
    Apply rules to signals (functional interface).
    
    Args:
        signals: List of FailureSignal objects
        rules: List of Rule objects
        
    Returns:
        List of matched rules
    """
    matched = []
    
    for signal in signals:
        message = signal.message if hasattr(signal, 'message') else str(signal)
        
        for rule in rules:
            if rule.matches(message):
                matched.append(rule)
    
    # Remove duplicates
    seen = set()
    unique = []
    for rule in matched:
        if rule.id not in seen:
            seen.add(rule.id)
            unique.append(rule)
    
    return unique
