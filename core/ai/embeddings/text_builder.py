"""
Embeddable Entity and Text Builder

Deterministic text construction for semantic embeddings.
This is the most critical step - good text = good embeddings.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime


@dataclass
class EmbeddableEntity:
    """
    Canonical entity interface for embeddings
    
    Any entity (test, scenario, failure) must be convertible to this format.
    """
    id: str                          # Unique identifier
    entity_type: str                 # test | scenario | failure
    text: str                        # Semantic text for embedding
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate entity"""
        if not self.id:
            raise ValueError("Entity id is required")
        if not self.entity_type:
            raise ValueError("Entity type is required")
        if self.entity_type not in ['test', 'scenario', 'failure']:
            raise ValueError(f"Invalid entity type: {self.entity_type}")
        if not self.text or not self.text.strip():
            raise ValueError("Entity text cannot be empty")


class EmbeddingTextBuilder:
    """
    Deterministic text builders for embeddings
    
    CRITICAL: Text quality matters more than the embedding model.
    
    Design principles:
    - Include domain-specific context
    - Normalize formatting
    - Keep token count reasonable
    - Be deterministic (same input = same text)
    """
    
    # Text-only strategy (Phase 1)
    # AST augmentation comes in Phase 2
    
    def build_test_text(
        self,
        test_name: str,
        description: Optional[str] = None,
        steps: Optional[list] = None,
        tags: Optional[list] = None,
        framework: Optional[str] = None,
        file_path: Optional[str] = None,
        assertions: Optional[list] = None,
        **kwargs
    ) -> str:
        """
        Build semantic text for a test case
        
        Args:
            test_name: Test function/method name
            description: Test description/docstring
            steps: List of test steps (for BDD/keyword-driven)
            tags: Test tags/markers
            framework: Testing framework (pytest, robot, etc.)
            file_path: Source file path
            assertions: List of assertions
            **kwargs: Additional metadata
        
        Returns:
            Semantic text representation
        
        Example output:
            Test: test_user_login_with_valid_credentials
            Framework: pytest
            Description: Verify that users can successfully log in with valid credentials
            Steps:
            - Navigate to login page
            - Enter valid username and password
            - Click login button
            - Verify user is redirected to dashboard
            Tags: authentication, login, smoke
        """
        parts = []
        
        # Test name (normalized)
        normalized_name = test_name.replace('_', ' ').replace('test ', '').strip()
        parts.append(f"Test: {normalized_name}")
        
        # Framework context
        if framework:
            parts.append(f"Framework: {framework}")
        
        # Description
        if description:
            desc_clean = description.strip()
            if desc_clean:
                parts.append(f"Description: {desc_clean}")
        
        # Steps (critical for semantic understanding)
        if steps:
            parts.append("Steps:")
            for step in steps:
                step_text = str(step).strip()
                if step_text:
                    parts.append(f"- {step_text}")
        
        # Assertions (what the test verifies)
        if assertions:
            parts.append("Verifies:")
            for assertion in assertions:
                assertion_text = str(assertion).strip()
                if assertion_text:
                    parts.append(f"- {assertion_text}")
        
        # Tags (for filtering/grouping)
        if tags:
            tags_str = ', '.join(str(t) for t in tags if t)
            if tags_str:
                parts.append(f"Tags: {tags_str}")
        
        # File path (for context)
        if file_path:
            parts.append(f"Location: {file_path}")
        
        return '\n'.join(parts)
    
    def build_scenario_text(
        self,
        scenario_name: str,
        feature: Optional[str] = None,
        given_steps: Optional[list] = None,
        when_steps: Optional[list] = None,
        then_steps: Optional[list] = None,
        tags: Optional[list] = None,
        examples: Optional[Dict] = None,
        **kwargs
    ) -> str:
        """
        Build semantic text for BDD scenario
        
        Args:
            scenario_name: Scenario name
            feature: Feature name
            given_steps: Given steps (preconditions)
            when_steps: When steps (actions)
            then_steps: Then steps (expected outcomes)
            tags: Scenario tags
            examples: Scenario outline examples
            **kwargs: Additional metadata
        
        Returns:
            Semantic text representation
        
        Example output:
            Scenario: User login with valid credentials
            Feature: User Authentication
            Given: User is on the login page
            Given: User has valid credentials
            When: User enters username and password
            When: User clicks the login button
            Then: User should be redirected to the dashboard
            Then: User should see welcome message
            Tags: @authentication @smoke
        """
        parts = []
        
        # Scenario name
        parts.append(f"Scenario: {scenario_name}")
        
        # Feature context
        if feature:
            parts.append(f"Feature: {feature}")
        
        # Given steps (preconditions)
        if given_steps:
            for step in given_steps:
                parts.append(f"Given: {step}")
        
        # When steps (actions)
        if when_steps:
            for step in when_steps:
                parts.append(f"When: {step}")
        
        # Then steps (expectations)
        if then_steps:
            for step in then_steps:
                parts.append(f"Then: {step}")
        
        # Tags
        if tags:
            tags_str = ' '.join(f"@{t}" for t in tags if t)
            if tags_str:
                parts.append(f"Tags: {tags_str}")
        
        # Examples (for scenario outlines)
        if examples:
            parts.append("Examples:")
            for key, values in examples.items():
                parts.append(f"  {key}: {', '.join(str(v) for v in values)}")
        
        return '\n'.join(parts)
    
    def build_failure_text(
        self,
        error_message: str,
        error_type: Optional[str] = None,
        stack_trace: Optional[str] = None,
        test_name: Optional[str] = None,
        test_step: Optional[str] = None,
        failure_category: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Build semantic text for test failure
        
        Args:
            error_message: Error message
            error_type: Exception type
            stack_trace: Stack trace (truncated)
            test_name: Associated test name
            test_step: Step that failed
            failure_category: Categorization (timeout, assertion, etc.)
            **kwargs: Additional metadata
        
        Returns:
            Semantic text representation
        
        Example output:
            Failure: AssertionError
            Test: test_user_login
            Step: Verify dashboard is displayed
            Error: Expected element '#dashboard' to be visible, but it was not found
            Category: element_not_found
            Stack: at login_page.py:45 in verify_dashboard()
        """
        parts = []
        
        # Failure type
        if error_type:
            parts.append(f"Failure: {error_type}")
        
        # Test context
        if test_name:
            parts.append(f"Test: {test_name}")
        
        # Step context
        if test_step:
            parts.append(f"Step: {test_step}")
        
        # Error message (most important)
        if error_message:
            # Clean and truncate if needed
            error_clean = error_message.strip()
            if len(error_clean) > 500:
                error_clean = error_clean[:500] + "..."
            parts.append(f"Error: {error_clean}")
        
        # Category
        if failure_category:
            parts.append(f"Category: {failure_category}")
        
        # Stack trace (truncated to relevant lines)
        if stack_trace:
            # Take last few lines (most relevant)
            stack_lines = stack_trace.strip().split('\n')
            relevant_lines = stack_lines[-3:] if len(stack_lines) > 3 else stack_lines
            if relevant_lines:
                parts.append(f"Stack: {' | '.join(relevant_lines)}")
        
        return '\n'.join(parts)
    
    def build_entity(
        self,
        entity_id: str,
        entity_type: str,
        **kwargs
    ) -> EmbeddableEntity:
        """
        Build an EmbeddableEntity from raw data
        
        Args:
            entity_id: Unique entity identifier
            entity_type: Entity type (test, scenario, failure)
            **kwargs: Entity-specific data
        
        Returns:
            EmbeddableEntity with constructed text
        
        Raises:
            ValueError: If entity type is invalid or required data is missing
        """
        # Build text based on entity type
        if entity_type == 'test':
            text = self.build_test_text(**kwargs)
        elif entity_type == 'scenario':
            text = self.build_scenario_text(**kwargs)
        elif entity_type == 'failure':
            text = self.build_failure_text(**kwargs)
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")
        
        # Extract metadata (everything except text-building params)
        metadata = {
            'created_at': datetime.utcnow().isoformat(),
            **kwargs
        }
        
        return EmbeddableEntity(
            id=entity_id,
            entity_type=entity_type,
            text=text,
            metadata=metadata
        )
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text
        
        Rough estimate: 1 token ≈ 4 characters
        
        Args:
            text: Text to estimate
        
        Returns:
            Estimated token count
        """
        return len(text) // 4
    
    def truncate_if_needed(self, text: str, max_tokens: int = 8000) -> str:
        """
        Truncate text if it exceeds max tokens
        
        Args:
            text: Text to truncate
            max_tokens: Maximum tokens allowed
        
        Returns:
            Truncated text (if needed)
        """
        estimated = self.estimate_tokens(text)
        if estimated <= max_tokens:
            return text
        
        # Truncate to max tokens (rough)
        max_chars = max_tokens * 4
        return text[:max_chars] + "\n... (truncated)"
